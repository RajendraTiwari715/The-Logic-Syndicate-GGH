from __future__ import annotations

import cv2
import time
import uuid
import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from app.vision.anpr import anpr_service
from app.vision.detector import YoloTrackingDetector
from app.vision.risk_engine import RiskEngine, RiskSignals
from app.vision.zones import point_in_polygon
from app.db.session import SessionLocal
from app.models.core_models import Camera, Zone, EventItem, Alert, Evidence, VehicleRecord, WatchlistRecord
from app.services.anpr_pipeline import format_plate, normalize_plate, DATA_DIR
from app.services.incident_engine import incident_engine
from app.services.ledger import ledger_service
from app.ws_manager import manager

logger = logging.getLogger(__name__)

from app.services.identity_manager import IdentityManager

class AutonomousSurveillancePipeline:
    """Master Autonomous AI Engine that accepts raw frames from ANY CCTV source,
    executes detection, runs ANPR on vehicles, checks perimeter zones on pedestrians,
    synthesizes contextual reasoning, and dispatches real-time alerts."""

    def __init__(self):
        self.detector = YoloTrackingDetector()
        self.risk_engine = RiskEngine()
        self._last_alert_time: Dict[str, float] = {} # Deduplication per tracking key
        self._dwell_timers: Dict[str, float] = {}    # Tracking loitering dwell duration

    def _save_evidence_snapshot(self, frame: np.ndarray, event_id: str, camera_id: str) -> tuple[str, str, str]:
        """Saves JPEG evidence snapshot, computes SHA-256 digest, and returns (file_path, file_url, sha256_hash)."""
        date_str = datetime.now().strftime("%Y%m%d")
        dir_path = Path(DATA_DIR) / "events" / date_str
        dir_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{datetime.now().strftime('%H%M%S')}_{camera_id}_{event_id}.jpg"
        file_path = dir_path / filename
        
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if ok:
            buf_bytes = buf.tobytes()
            sha256 = hashlib.sha256(buf_bytes).hexdigest()
            file_path.write_bytes(buf_bytes)
            file_url = f"/media/events/{date_str}/{filename}"
            return str(file_path), file_url, sha256
        return "", "", "0" * 64

    def process_live_cctv_frame(self, camera_id: str, frame: np.ndarray, context: dict = None) -> np.ndarray:
        """Processes a single live CCTV frame from any camera infrastructure and returns
        the tactical HUD annotated frame ready for display."""
        h, w = frame.shape[:2]
        annotated = frame.copy()
        timestamp = datetime.now()
        timestamp_str = timestamp.strftime("%d %b %Y, %H:%M:%S")

        # 1. Primary Object Detection & Tracking
        detections = self.detector.infer(frame)
        if not detections:
            return annotated

        if context is None:
            context = {}
        camera_mode = context.get("camera_mode", "ALL")
        run_face_object = camera_mode in ("ALL", "FACE & OBJECT", "FACE&OBJECT", "FACE_OBJECT")
        run_anpr = camera_mode in ("ALL", "ANPR")

        with SessionLocal() as db:
            # Query active perimeter zones for this camera
            zones = db.query(Zone).filter(Zone.cameraId == camera_id).all()
            
            for det in detections:
                x1, y1, x2, y2 = [int(v) for v in det.bbox_xyxy]
                conf_pct = int(det.confidence * 100)
                track_id = f"TRK-{det.raw_track_id or '00'}"

                # -------------------------------------------------------------
                # SCENARIO A: VEHICLE DETECTED -> RUN AUTO-ANPR & WATCHLIST
                # -------------------------------------------------------------
                if det.object_type == "vehicle" and run_anpr:
                    box_color = (255, 180, 0) # Cyan/Blue default for vehicles
                    tag_text = f"{det.object_class.upper()} [{conf_pct}%]"
                    
                    # Crop vehicle region
                    pad = 6
                    vcrop = frame[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
                    if vcrop.size > 0:
                        plate_result = anpr_service.process_plate_crop(vcrop)
                        if plate_result and anpr_service.validate_plate(plate_result.normalized):
                            norm_plate = anpr_service.normalize_plate(plate_result.normalized)
                            disp_plate = anpr_service.format_plate(norm_plate)
                            state_code = anpr_service.get_state_code(norm_plate)
                            tag_text = f"{disp_plate} [{state_code or 'IN'}] {conf_pct}%"

                            # Extract live image for persistence
                            live_image_b64_veh = None
                            try:
                                import base64
                                _, buffer = cv2.imencode('.jpg', vcrop)
                                live_image_b64_veh = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"
                            except Exception:
                                pass

                            # Identity & Tracking deduplication
                            id_manager = IdentityManager(db)
                            veh_rec, is_new = id_manager.resolve_vehicle(tracking_id=track_id, plate_number=norm_plate, live_image=live_image_b64_veh)

                            # Record Vehicle Log into Database & Broadcast
                            v_dedupe_key = f"VEH:{camera_id}:{track_id}"
                            now_v = time.time()
                            if now_v - self._last_alert_time.get(v_dedupe_key, 0) > 15.0:
                                self._last_alert_time[v_dedupe_key] = now_v
                                try:
                                    import asyncio
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        loop.create_task(manager.broadcast({
                                            "type": "vehicle",
                                            "vehicle": {
                                                "id": veh_rec.id,
                                                "cameraId": camera_id,
                                                "plate": disp_plate,
                                                "plateNumber": disp_plate,
                                                "confidence": conf_pct,
                                                "status": veh_rec.status,
                                                "timestamp": timestamp_str,
                                                "vehicleType": det.object_class.upper(),
                                                "image": veh_rec.representative_image,
                                                "annotatedImage": veh_rec.representative_image,
                                                "entryCount": veh_rec.entry_count
                                            }
                                        }))
                                except Exception:
                                    pass

                            # Resolve watchlist status
                            wl_match = db.query(WatchlistRecord).filter(
                                WatchlistRecord.plate_number == norm_plate
                            ).first()

                            if veh_rec.status == "WATCHLIST":
                                box_color = (0, 0, 240)  # Bright Red
                                wl_desc = wl_match.description if wl_match else "Watchlist match"
                                tag_text = f"! WATCHLIST ! {disp_plate}"

                                # Cooldown-controlled alert dispatch (once per 20 seconds)
                                dedupe_key = f"WL:{camera_id}:{norm_plate}"
                                now = time.time()
                                if now - self._last_alert_time.get(dedupe_key, 0) > 20.0:
                                    self._last_alert_time[dedupe_key] = now
                                    self._create_watchlist_alert(db, camera_id, disp_plate, wl_desc, timestamp, frame)

                    # Draw Vehicle Box & Floating Tag
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
                    cv2.rectangle(annotated, (x1, y1 - 20), (x1 + len(tag_text) * 9, y1), box_color, -1)
                    cv2.putText(annotated, tag_text, (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)

                    # Broadcast detection bbox to WebSocket for frontend overlay
                    try:
                        import asyncio as _asyncio
                        _loop = _asyncio.get_event_loop()
                        if _loop.is_running():
                            _loop.create_task(manager.broadcast({
                                "type": "detection",
                                "data": {
                                    "id": f"det-{det.raw_track_id or uuid.uuid4().hex[:8]}",
                                    "cameraId": camera_id,
                                    "objectType": "vehicle",
                                    "trackingId": track_id,
                                    "confidence": conf_pct,
                                    "timestamp": timestamp_str,
                                    "bbox": {
                                        "x": round((x1 / max(w, 1)) * 100, 2),
                                        "y": round((y1 / max(h, 1)) * 100, 2),
                                        "width": round(((x2 - x1) / max(w, 1)) * 100, 2),
                                        "height": round(((y2 - y1) / max(h, 1)) * 100, 2),
                                    },
                                    "label": det.object_class.upper()
                                }
                            }))
                    except Exception:
                        pass

                # -------------------------------------------------------------
                # SCENARIO B: PERSON DETECTED -> RUN SPATIAL ZONE & LOITERING
                # -------------------------------------------------------------
                elif det.object_type == "person" and run_face_object:
                    box_color = (0, 230, 100) # Green normal
                    person_foot = ((x1 + x2) // 2, y2)
                    tag_text = f"PERSON {track_id} [{conf_pct}%]"

                    # Check dwell / loitering timer
                    first_seen = self._dwell_timers.setdefault(track_id, time.time())
                    dwell_sec = round(time.time() - first_seen, 1)

                    # Face Detection & Biometric Embeddings 
                    face_embedding = None
                    try:
                        from deepface import DeepFace
                        pad = 10
                        hcrop = frame[max(0, y1-pad):min(h, y2+pad), max(0, x1-pad):min(w, x2+pad)]
                        if hcrop.shape[0] > 60 and hcrop.shape[1] > 60:
                            # Extract single mathematically bound robust 128D/4096D array map natively 
                            embedding_objs = DeepFace.represent(img_path=hcrop, model_name="VGG-Face", detector_backend="skip", enforce_detection=False, align=True)
                            if embedding_objs and len(embedding_objs) > 0:
                                face_embedding = embedding_objs[0]["embedding"]
                    except Exception as e:
                        pass

                    # Identity & Re-entry logic (IdentityManager)
                    id_manager = IdentityManager(db)
                    
                    live_image_b64 = None
                    if 'hcrop' in locals() and hcrop is not None and hcrop.size > 0:
                        import base64
                        _, buffer = cv2.imencode('.jpg', hcrop)
                        live_image_b64 = f"data:image/jpeg;base64,{base64.b64encode(buffer).decode('utf-8')}"

                    person_identity, is_new_entry = id_manager.resolve_person(
                        tracking_id=track_id, 
                        face_embedding=face_embedding, 
                        name="UNKNOWN",
                        live_image=live_image_b64
                    )
                    entry_count = person_identity.entry_count
                    auth_status = person_identity.authorization_status

                    if person_identity.entry_count >= 1:
                         tag_text = f"PERSON {track_id} | ENTRIES: {entry_count} [{conf_pct}%]"


                    # Evaluate zones (virtual fences)
                    inside_restricted = False
                    violated_zone_name = None

                    for zone in zones:
                        if zone.coordinates and isinstance(zone.coordinates, list):
                            poly = [(int(p.get("x", 0) * w / 100), int(p.get("y", 0) * h / 100)) for p in zone.coordinates]
                            if len(poly) >= 3 and point_in_polygon(person_foot, poly):
                                inside_restricted = True
                                violated_zone_name = zone.name
                                break

                    is_loitering = dwell_sec > 10.0
                    is_night = self.risk_engine.is_night_time(timestamp)

                    if inside_restricted or is_loitering or (is_night and det.confidence > 0.7):
                        box_color = (0, 0, 240) # Red
                        alert_label = "INTRUSION" if inside_restricted else "LOITERING" if is_loitering else "CURFEW MOVEMENT"
                        tag_text = f"! {alert_label} ! {track_id} ({dwell_sec}s)"

                        dedupe_key = f"PERSON:{camera_id}:{track_id}"
                        now = time.time()
                        if now - self._last_alert_time.get(dedupe_key, 0) > 25.0:
                            self._last_alert_time[dedupe_key] = now
                            self._create_person_alert(
                                db, camera_id, track_id, violated_zone_name, dwell_sec, is_night, timestamp, frame
                            )

                    # Draw Person Box & Floating Tag
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
                    cv2.rectangle(annotated, (x1, y1 - 20), (x1 + len(tag_text) * 9, y1), box_color, -1)
                    cv2.putText(annotated, tag_text, (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)

                    # Broadcast detection bbox to WebSocket for frontend overlay
                    try:
                        import asyncio as _asyncio
                        _loop = _asyncio.get_event_loop()
                        if _loop.is_running():
                            _loop.create_task(manager.broadcast({
                                "type": "detection",
                                "data": {
                                    "id": f"det-{det.raw_track_id or uuid.uuid4().hex[:8]}",
                                    "cameraId": camera_id,
                                    "objectType": "person",
                                    "trackingId": track_id,
                                    "confidence": conf_pct,
                                    "timestamp": timestamp_str,
                                    "bbox": {
                                        "x": round((x1 / max(w, 1)) * 100, 2),
                                        "y": round((y1 / max(h, 1)) * 100, 2),
                                        "width": round(((x2 - x1) / max(w, 1)) * 100, 2),
                                        "height": round(((y2 - y1) / max(h, 1)) * 100, 2),
                                    },
                                    "label": tag_text
                                }
                            }))
                    except Exception:
                        pass
                
                # -------------------------------------------------------------
                # SCENARIO C: ANIMAL DETECTED
                # -------------------------------------------------------------
                elif det.object_type == "animal" and run_face_object:
                    box_color = (0, 140, 255) # Orange (BGR)
                    tag_text = f"{det.object_class.upper()} [{conf_pct}%]"
                    
                    # Draw Animal Box & Floating Tag
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), box_color, 2)
                    cv2.rectangle(annotated, (x1, y1 - 20), (x1 + len(tag_text) * 9, y1), box_color, -1)
                    cv2.putText(annotated, tag_text, (x1 + 4, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)

                    # Broadcast detection bbox to WebSocket for frontend overlay
                    try:
                        import asyncio as _asyncio
                        _loop = _asyncio.get_event_loop()
                        if _loop.is_running():
                            _loop.create_task(manager.broadcast({
                                "type": "detection",
                                "data": {
                                    "id": f"det-{det.raw_track_id or uuid.uuid4().hex[:8]}",
                                    "cameraId": camera_id,
                                    "objectType": "animal",
                                    "trackingId": track_id,
                                    "confidence": conf_pct,
                                    "timestamp": timestamp_str,
                                    "bbox": {
                                        "x": round((x1 / max(w, 1)) * 100, 2),
                                        "y": round((y1 / max(h, 1)) * 100, 2),
                                        "width": round(((x2 - x1) / max(w, 1)) * 100, 2),
                                        "height": round(((y2 - y1) / max(h, 1)) * 100, 2),
                                    },
                                    "label": det.object_class.upper()
                                }
                            }))
                    except Exception:
                        pass

        # 3. Tactical HUD Watermark Bar
        cv2.rectangle(annotated, (0, 0), (w, 24), (20, 20, 20), -1)
        hud_info = f"IBVAP AUTONOMOUS CCTV AI | CAM: {camera_id} | {timestamp_str} | ACTIVE TARGETS: {len(detections)}"
        cv2.putText(annotated, hud_info, (10, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 230, 230), 1, cv2.LINE_AA)

        return annotated

    def _create_watchlist_alert(self, db, camera_id: str, plate: str, description: str, timestamp: datetime, frame: np.ndarray):
        """Dispatches automated Critical Watchlist Alert with SHA-256 evidence chain and incident correlation."""
        alert_id = f"ALRT-WL-{uuid.uuid4().hex[:6].upper()}"
        event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        time_str = timestamp.strftime("%d %b %Y, %I:%M:%S %p")

        # Save Evidence & compute SHA-256
        file_path, file_url, sha256 = self._save_evidence_snapshot(frame, event_id, camera_id)

        # 1. Create EventItem
        event_item = EventItem(
            id=event_id,
            cameraId=camera_id,
            eventType="WATCHLIST_MATCH",
            severity="CRITICAL",
            trackingId=plate,
            description=f"Watchlist vehicle detected: {plate}.",
            timestamp=time_str,
            status="NEW",
            riskScore=95,
            reasons=["Security Watchlist Match", "Immediate Interception Advised"],
            confidence=95.0,
            details={"plate": plate, "file_url": file_url}
        )
        db.add(event_item)

        # 2. Record Evidence
        ev_id = f"EV-{uuid.uuid4().hex[:6].upper()}"
        evidence = Evidence(
            id=ev_id,
            event_id=event_id,
            camera_id=camera_id,
            file_location=file_path,
            file_url=file_url,
            file_type="SNAPSHOT",
            sha256_hash=sha256,
            integrity_status="VERIFIED"
        )
        db.add(evidence)

        # 3. Create Alert
        alert = Alert(
            id=alert_id,
            eventId=event_id,
            severity="CRITICAL",
            riskScore=95,
            reason=f"Watchlist vehicle detected: {plate}. Flagged: {description}",
            reasons=["Security Watchlist Match", "Immediate Interception Advised"],
            status="NEW",
            cameraId=camera_id,
            title="WATCHLIST VEHICLE DETECTED",
            what=f"Vehicle with plate {plate}",
            where=camera_id,
            when_time=time_str,
            object=plate,
            why=f"Flagged by security watchlist: {description}",
            confidence=95
        )
        db.add(alert)
        db.commit()

        # 4. Multi-Camera Incident Correlation
        try:
            incident_engine.correlate_events(db, event_item)
        except Exception as exc:
            logger.warning("Incident correlation warning: %s", exc)

        # 5. Cryptographic Evidence Ledger
        try:
            ledger_service.record_evidence_integrity(event_id, sha256, actor="AUTONOMOUS_AI")
        except Exception as exc:
            logger.warning("Ledger recording warning: %s", exc)

        # 6. WebSocket Real-Time Alert Broadcast
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast({
                    "type": "NEW_ALERT",
                    "data": {
                        "id": alert.id,
                        "eventId": alert.eventId,
                        "title": alert.title,
                        "severity": "CRITICAL",
                        "riskScore": 95,
                        "reason": alert.reason,
                        "where": camera_id,
                        "when": time_str,
                        "evidenceUrl": file_url,
                        "sha256": sha256
                    }
                }))
        except Exception:
            pass

    def _create_person_alert(self, db, camera_id: str, track_id: str, zone_name: Optional[str], dwell: float, is_night: bool, timestamp: datetime, frame: np.ndarray):
        """Dispatches automated Perimeter Intrusion or Loitering Alert with SHA-256 evidence chain and incident correlation."""
        alert_id = f"ALRT-SEC-{uuid.uuid4().hex[:6].upper()}"
        event_id = f"EVT-{uuid.uuid4().hex[:6].upper()}"
        time_str = timestamp.strftime("%d %b %Y, %I:%M:%S %p")

        reasons = []
        if zone_name:
            reasons.append(f"Breached virtual perimeter zone '{zone_name}'")
        if dwell > 20:
            reasons.append(f"Stationary loitering for {int(dwell)}s")
        if is_night:
            reasons.append("Movement in restricted curfew hours")

        reason_summary = " • ".join(reasons) or "Unusual perimeter activity"
        severity = "HIGH" if not zone_name else "CRITICAL"
        risk_score = 88 if zone_name else 70
        event_type = "RESTRICTED_ZONE_INTRUSION" if zone_name else "LOITERING"

        # Save Evidence & compute SHA-256
        file_path, file_url, sha256 = self._save_evidence_snapshot(frame, event_id, camera_id)

        # 1. Create EventItem
        event_item = EventItem(
            id=event_id,
            cameraId=camera_id,
            eventType=event_type,
            severity=severity,
            trackingId=track_id,
            description=reason_summary,
            timestamp=time_str,
            status="NEW",
            riskScore=risk_score,
            reasons=reasons,
            confidence=92.0,
            details={"track_id": track_id, "zone": zone_name, "dwell": dwell, "file_url": file_url}
        )
        db.add(event_item)

        # 2. Record Evidence
        ev_id = f"EV-{uuid.uuid4().hex[:6].upper()}"
        evidence = Evidence(
            id=ev_id,
            event_id=event_id,
            camera_id=camera_id,
            file_location=file_path,
            file_url=file_url,
            file_type="SNAPSHOT",
            sha256_hash=sha256,
            integrity_status="VERIFIED"
        )
        db.add(evidence)

        # 3. Create Alert
        alert = Alert(
            id=alert_id,
            eventId=event_id,
            severity=severity,
            riskScore=risk_score,
            reason=reason_summary,
            reasons=reasons,
            status="NEW",
            cameraId=camera_id,
            trackingId=track_id,
            title="PERIMETER BREACH DETECTED" if zone_name else "SUSPICIOUS LOITERING",
            what=f"Person ({track_id})",
            where=f"{camera_id} / {zone_name or 'Buffer'}",
            when_time=time_str,
            object=track_id,
            why=reason_summary,
            zone=zone_name,
            confidence=92
        )
        db.add(alert)
        db.commit()

        # 4. Multi-Camera Incident Correlation
        try:
            incident_engine.correlate_events(db, event_item)
        except Exception as exc:
            logger.warning("Incident correlation warning: %s", exc)

        # 5. Cryptographic Evidence Ledger
        try:
            ledger_service.record_evidence_integrity(event_id, sha256, actor="AUTONOMOUS_AI")
        except Exception as exc:
            logger.warning("Ledger recording warning: %s", exc)

        # 6. WebSocket Real-Time Alert Broadcast
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(manager.broadcast({
                    "type": "NEW_ALERT",
                    "data": {
                        "id": alert.id,
                        "eventId": alert.eventId,
                        "title": alert.title,
                        "severity": alert.severity,
                        "riskScore": alert.riskScore,
                        "reason": alert.reason,
                        "where": camera_id,
                        "when": time_str,
                        "evidenceUrl": file_url,
                        "sha256": sha256
                    }
                }))
        except Exception:
            pass

master_ai_pipeline = AutonomousSurveillancePipeline()
