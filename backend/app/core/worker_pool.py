import logging
import asyncio
import json
import uuid
import numpy as np
import time
from typing import Dict
from datetime import datetime

from app.core.camera_worker import CameraWorker
from app.db.session import SessionLocal
from app.services.anpr_pipeline import process_anpr_frame
from app.ws_manager import manager

logger = logging.getLogger(__name__)


class WorkerPool:
    """
    Manages active CameraWorker threads and bridges synchronous ML pipelines
    with asynchronous WebSocket broadcasting.

    Camera Mode Semantics (controlled via context["camera_mode"]):
        ALL           -> YOLO + Face/Object pipeline + ANPR pipeline
        FACE & OBJECT -> YOLO + Face/Object pipeline only (no ANPR)
        ANPR          -> ANPR pipeline only (no YOLO/Face)
    """
    def __init__(self):
        self._workers: Dict[str, CameraWorker] = {}
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None

        # Face detection state (per camera)
        self._face_cascade = None
        self._face_tracks: Dict[str, list[dict]] = {}
        self._object_tracks: Dict[str, list[dict]] = {}
        self._last_face_time: Dict[str, float] = {}
        self._last_fence_time: float = 0.0

    def _get_face_cascade(self):
        if self._face_cascade is None:
            import cv2
            if not hasattr(cv2, 'CascadeClassifier'):
                logger.warning(
                    "cv2.CascadeClassifier not available in this OpenCV build (likely opencv-python-headless 5.x). "
                    "HAAR face detection is disabled. Install 'opencv-python>=4.8,<5' for full face cascade support."
                )
                self._face_cascade = None
                return None
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
            if self._face_cascade.empty():
                logger.error("Failed to load haarcascade_frontalface_default.xml from %s", cascade_path)
                self._face_cascade = None
        return self._face_cascade


    def _broadcast_sync(self, payload: dict):
        """Thread-safe fire-and-forget broadcast to all WebSocket clients."""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                manager.broadcast(payload),
                self._loop
            )

    @staticmethod
    def _bbox_iou(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
        x1 = max(first[0], second[0])
        y1 = max(first[1], second[1])
        x2 = min(first[2], second[2])
        y2 = min(first[3], second[3])
        intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        if intersection == 0:
            return 0.0
        area_first = max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1])
        area_second = max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1])
        return intersection / max(area_first + area_second - intersection, 1.0)

    @staticmethod
    def _boxes_match(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> tuple[bool, float]:
        first_width = max(first[2] - first[0], 1.0)
        first_height = max(first[3] - first[1], 1.0)
        second_width = max(second[2] - second[0], 1.0)
        second_height = max(second[3] - second[1], 1.0)
        first_cx, first_cy = (first[0] + first[2]) / 2, (first[1] + first[3]) / 2
        second_cx, second_cy = (second[0] + second[2]) / 2, (second[1] + second[3]) / 2
        scale = max((first_width + first_height + second_width + second_height) / 4, 1.0)
        distance = (((first_cx - second_cx) ** 2 + (first_cy - second_cy) ** 2) ** 0.5) / scale
        size_ratio = max(first_width / second_width, second_width / first_width,
                         first_height / second_height, second_height / first_height)
        overlap = WorkerPool._bbox_iou(first, second)
        return size_ratio <= 2.5 and (overlap >= 0.05 or distance <= 1.25), distance - overlap

    def _update_object_tracks(self, camera_id: str, detections: list[dict], now: float) -> None:
        """Assign stable per-camera IDs so every distinct object gets one snapshot."""
        tracks = [
            track for track in self._object_tracks.get(camera_id, [])
            if now - track["last_seen"] <= 5.0
        ]
        assigned: set[str] = set()

        for detection in detections:
            bbox = tuple(float(value) for value in detection["bbox"])
            best_track = None
            best_score = float("inf")
            for track in tracks:
                if track["id"] in assigned or track["class"] != detection["class"]:
                    continue
                matches, score = self._boxes_match(track["bbox"], bbox)
                if matches and score < best_score:
                    best_track = track
                    best_score = score

            if best_track is None:
                best_track = {
                    "id": f"TRK-{uuid.uuid4().hex[:12]}",
                    "class": detection["class"],
                    "snapshot_saved": False,
                }
                tracks.append(best_track)

            best_track["bbox"] = bbox
            best_track["last_seen"] = now
            detection["is_new_track"] = not best_track.get("snapshot_saved", False)
            assigned.add(best_track["id"])
            detection["tracking_id"] = best_track["id"]

        self._object_tracks[camera_id] = tracks

    def _face_track_for_detection(self, camera_id: str, bbox: tuple[float, float, float, float], now: float) -> tuple[str, bool]:
        """Track face boxes within one camera; do not identify people by clothing color."""
        tracks = [
            track for track in self._face_tracks.get(camera_id, [])
            if now - track["last_seen"] <= 10.0
        ]
        best_track = None
        best_score = float("inf")
        for track in tracks:
            if track.get("assigned_at") == now:
                continue
            matches, score = self._boxes_match(track["bbox"], bbox)
            if matches and score < best_score:
                best_track = track
                best_score = score

        is_new = best_track is None
        if is_new:
            best_track = {"id": f"FACE-{uuid.uuid4().hex[:10]}", "logged": False}
            tracks.append(best_track)
        best_track["bbox"] = bbox
        best_track["last_seen"] = now
        best_track["assigned_at"] = now
        self._face_tracks[camera_id] = tracks
        return best_track["id"], is_new or not best_track.get("logged", False)

    def _save_object_snapshot(self, db, camera_id: str, frame: np.ndarray, detection: dict, timestamp: str) -> None:
        """Persist one image per tracked person/object and retry failed writes."""
        if not detection.get("is_new_track"):
            return

        x1, y1, x2, y2 = (int(round(value)) for value in detection["bbox"])
        frame_h, frame_w = frame.shape[:2]
        x1, x2 = max(0, x1), min(frame_w, x2)
        y1, y2 = max(0, y1), min(frame_h, y2)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return

        try:
            from app.models.core_models import FaceRecord
            from app.services.snapshot_store import evidence_storage

            is_person = detection.get("class") == "person"
            label = detection.get("label", "DETECTION")
            stored_image = evidence_storage.upload_evidence(
                crop, camera_id, f"{'PERSON' if is_person else 'OBJECT'}_{label}"
            )
            if not stored_image:
                return

            tracking_id = detection["tracking_id"]
            record_id = f"{'FACE' if is_person else 'OBJECT'}-LOG-{uuid.uuid4().hex[:8]}"
            face_record = FaceRecord(
                id=record_id,
                cameraId=camera_id,
                identity=(
                    f"Unknown ID-{tracking_id[-6:].upper()}"
                    if is_person else label.title()
                ),
                confidence=int(round(detection.get("confidence", 0) * 100)),
                timestamp=timestamp,
                database="Local DB" if is_person else "Object Detection",
                status="UNKNOWN",
                image=stored_image[0],
                direction="Unknown",
            )
            db.add(face_record)
            db.commit()
            for track in self._object_tracks.get(camera_id, []):
                if track["id"] == tracking_id:
                    track["snapshot_saved"] = True
                    if is_person:
                        track["record_id"] = record_id
                        track["identity"] = face_record.identity
                        track["face_enhanced"] = False
                    break
            if is_person:
                self._broadcast_sync({
                    "type": "NEW_FACE",
                    "data": {
                        "id": face_record.id,
                        "cameraId": face_record.cameraId,
                        "identity": face_record.identity,
                        "confidence": face_record.confidence,
                        "timestamp": face_record.timestamp,
                        "database": face_record.database,
                        "status": face_record.status,
                        "image": face_record.image,
                        "direction": face_record.direction,
                    },
                })
        except Exception as exc:
            db.rollback()
            logger.warning("[%s] Could not persist object snapshot: %s", camera_id, exc)

    def _person_track_for_face(
        self,
        camera_id: str,
        face_bbox: tuple[float, float, float, float],
        now: float,
    ) -> dict | None:
        """Match a detected face crop to its person detection in this camera frame."""
        face_center = ((face_bbox[0] + face_bbox[2]) / 2, (face_bbox[1] + face_bbox[3]) / 2)
        candidates = []
        for track in self._object_tracks.get(camera_id, []):
            if track["class"] != "person" or now - track["last_seen"] > 5.0:
                continue
            x1, y1, x2, y2 = track["bbox"]
            if x1 <= face_center[0] <= x2 and y1 <= face_center[1] <= y2:
                area = max((x2 - x1) * (y2 - y1), 1.0)
                candidates.append((area, track))
        return min(candidates, key=lambda item: item[0])[1] if candidates else None

    def _inference_bridge(self, frame: np.ndarray, camera_id: str, context: dict = None):
        """
        Executes the AI pipeline for a single camera frame inside the isolated worker thread.
        Routes to YOLO/Face or ANPR based on camera_mode from context.
        """
        context = context or {}
        zones = context.get("zones", [])
        force_watchlist = context.get("force_watchlist", False)
        force_reid = context.get("force_reid", False)
        with SessionLocal() as db:
            try:
                from app.models.core_models import Camera
                cam_rec = db.query(Camera).filter(Camera.id == camera_id).first()
                if not cam_rec:
                    try:
                        cam_rec = Camera(id=camera_id, name=camera_id, location="Unknown", status="ONLINE", camera_mode="ALL")
                        db.add(cam_rec)
                        db.commit()
                        db.refresh(cam_rec)
                    except Exception:
                        db.rollback()
                        cam_rec = None
                
                db_camera_mode = getattr(cam_rec, "camera_mode", "ALL") if cam_rec else "ALL"
                if not db_camera_mode:
                    db_camera_mode = "ALL"
                # Context overrides DB if provided directly
                camera_mode = (context.get("camera_mode") or db_camera_mode).upper().strip()
                
                # Determine which pipelines to run based on camera mode
                run_face_object = camera_mode in ("ALL", "FACE & OBJECT", "FACE&OBJECT", "FACE_OBJECT")
                run_anpr = camera_mode in ("ALL", "ANPR")

                # ===================================================
                # PIPELINE A: YOLO + FACE & OBJECT DETECTION
                # ===================================================
                detections = []
                if run_face_object:
                    from app.vision.model_manager import model_manager
                    model, _, err = model_manager.get_yolo()
                    if err or model is None:
                        logger.warning(f"[{camera_id}] YOLO load skipped: {err}")
                    else:

                        # COCO class name lookup
                        COCO_NAMES = {
                            0: 'person',
                            2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck',
                            14: 'bird', 15: 'cat', 16: 'dog',
                            17: 'horse', 18: 'sheep', 19: 'cow',
                            20: 'elephant', 21: 'bear'
                        }
                        # person/vehicle classes
                        PERSON_CLASSES = {0}
                        VEHICLE_CLASSES = {2, 3, 5, 7}
                        ANIMAL_CLASSES = {14, 15, 16, 17, 18, 19, 20, 21}

                        results = model(frame, verbose=False)
                        h, w = frame.shape[:2]
                        for r in results:
                            for box in r.boxes:
                                cls_id = int(box.cls[0])
                                conf = float(box.conf[0])
                                if cls_id in PERSON_CLASSES:
                                    obj_type = 'person'
                                    label = 'PERSON'
                                elif cls_id in VEHICLE_CLASSES:
                                    obj_type = 'vehicle'
                                    label = COCO_NAMES.get(cls_id, 'VEHICLE').upper()
                                elif cls_id in ANIMAL_CLASSES:
                                    obj_type = 'animal'
                                    label = COCO_NAMES.get(cls_id, 'ANIMAL').upper()
                                else:
                                    continue
                                bbox = box.xyxy[0].tolist()
                                detections.append({
                                    "bbox": bbox,
                                    "class": obj_type,
                                    "label": label,
                                    "confidence": conf
                                })
                                logger.debug(
                                    f"[{camera_id}] YOLO: cls={cls_id}({label}) conf={conf:.2f} bbox={bbox}"
                                )

                        # Broadcast real detections to frontend (no fake fallback)
                        if detections:
                            h, w = frame.shape[:2]
                            now_iso = datetime.utcnow().isoformat() + "Z"
                            self._update_object_tracks(camera_id, detections, time.time())
                            for det in detections:
                                self._save_object_snapshot(db, camera_id, frame, det, now_iso)
                                x1, y1, x2, y2 = det["bbox"]
                                stable_id = det["tracking_id"]
                                self._broadcast_sync({
                                    "type": "detection",
                                    "data": {
                                        "id": stable_id,
                                        "cameraId": camera_id,
                                        "objectType": det["class"],
                                        "trackingId": stable_id,
                                        "confidence": round(det["confidence"] * 100, 1),
                                        "timestamp": now_iso,
                                        "bbox": {
                                            "x": round((x1 / max(w, 1)) * 100, 2),
                                            "y": round((y1 / max(h, 1)) * 100, 2),
                                            "width": round(((x2 - x1) / max(w, 1)) * 100, 2),
                                            "height": round(((y2 - y1) / max(h, 1)) * 100, 2)
                                        },
                                        "label": det.get("label", det["class"].upper())
                                    }
                                })

                # ===================================================
                # VIRTUAL FENCING CHECK (only if face/object ran)
                # ===================================================
                if run_face_object and zones and detections:
                    from app.vision.zones import point_in_polygon, percent_points_to_pixels
                    h, w = frame.shape[:2]

                    for det in detections:
                        x1, y1, x2, y2 = det["bbox"]
                        bottom_center = ((x1 + x2) / 2.0, y2)

                        for zone in zones:
                            poly_points = percent_points_to_pixels(zone['points'], w, h)
                            is_inside = point_in_polygon(bottom_center, poly_points)

                            logger.debug(
                                f"[{camera_id}] Fencing check: center={bottom_center} zone={zone.get('name')} inside={is_inside}"
                            )
                            if is_inside:
                                # Rate-limit fence alerts to once per 3 seconds
                                if (time.time() - self._last_fence_time) < 3.0:
                                    continue
                                self._last_fence_time = time.time()

                                from app.models.core_models import EventItem
                                event_id = f"EVT-FENCE-{int(time.time()*1000)}"
                                now_iso = datetime.utcnow().isoformat() + "Z"
                                fencing_event = EventItem(
                                    id=event_id,
                                    cameraId=camera_id,
                                    eventType="INTRUSION",
                                    severity="CRITICAL",
                                    trackingId=f"TRACK-{uuid.uuid4().hex[:8]}",
                                    description=f"Subject breached Virtual Fence: {zone['name']}",
                                    timestamp=now_iso,
                                    status="NEW",
                                    riskScore=90,
                                    reasons=["Person/Vehicle crossed polygon boundary", f"Zone: {zone['name']}"]
                                )
                                db.add(fencing_event)
                                db.commit()
                                db.refresh(fencing_event)

                                from app.core.ledger import record_event_ledger
                                ledger_hash = record_event_ledger(db, fencing_event)
                                fencing_event.details = {"blockchain_hash": ledger_hash} if ledger_hash else {}

                                self._broadcast_sync({
                                    "type": "NEW_ALERT",
                                    "data": {
                                        "id": f"ALRT-FENCE-{int(time.time()*1000)}",
                                        "eventId": event_id,
                                        "severity": "CRITICAL",
                                        "riskScore": 90,
                                        "title": "Virtual Fence Breach",
                                        "what": "Person/Vehicle entered restricted polygon",
                                        "where": camera_id,
                                        "zone": zone['name'],
                                        "reason": f"Subject breached {zone['name']}",
                                        "status": "NEW",
                                        "createdAt": now_iso,
                                        "reasons": fencing_event.reasons,
                                        "blockchain_hash": ledger_hash
                                    }
                                })

                # ===================================================
                # PIPELINE B: FACE IDENTITY (within YOLO/Face mode)
                # ===================================================
                if run_face_object:
                    import cv2
                    face_cascade = self._get_face_cascade()
                    if face_cascade is not None:
                        current_time = time.time()
                        # Throttle face detection to once per 2 seconds per camera
                        if current_time - self._last_face_time.get(camera_id, 0) > 2.0:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            faces = face_cascade.detectMultiScale(
                                gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60)
                            )

                            if len(faces) > 0:
                                self._last_face_time[camera_id] = current_time
                                from app.models.core_models import FaceRecord

                                for x, y, w, h in faces:
                                    face_bbox = (float(x), float(y), float(x + w), float(y + h))
                                    face_track_id, is_new_entry_event = self._face_track_for_detection(
                                        camera_id, face_bbox, current_time
                                    )
                                    person_track = self._person_track_for_face(camera_id, face_bbox, current_time)
                                    if person_track and person_track.get("face_enhanced"):
                                        for track in self._face_tracks.get(camera_id, []):
                                            if track["id"] == face_track_id:
                                                track["logged"] = True
                                                break
                                        continue
                                    if not person_track and not is_new_entry_event:
                                        continue

                                    # Crop face with padding for UI display
                                    px = max(0, x - 20)
                                    py = max(0, y - 20)
                                    pw = min(frame.shape[1] - px, w + 40)
                                    ph = min(frame.shape[0] - py, h + 40)
                                    face_crop = frame[py:py+ph, px:px+pw]

                                    if face_crop.size == 0:
                                        continue

                                    # Clothing-color similarity is not a reliable person identity
                                    # signal; bbox tracking keeps nearby people as separate entries.
                                    if force_watchlist:
                                        face_identity, face_status = "Watchlist Target", "FLAGGED"
                                    elif force_reid:
                                        face_identity, face_status = "Verified Staff", "AUTHORIZED"
                                    else:
                                        face_identity = (
                                            person_track.get("identity") if person_track
                                            else f"Unknown ID-{face_track_id[-6:].upper()}"
                                        )
                                        face_status = "UNKNOWN"

                                    # Persist the crop in the Docker-backed evidence store and
                                    # keep only its URL in PostgreSQL.
                                    from app.services.snapshot_store import evidence_storage
                                    face_snapshot = evidence_storage.upload_evidence(
                                        face_crop, camera_id, f"FACE_{face_identity}"
                                    )
                                    face_image_url = face_snapshot[0] if face_snapshot else None
                                    if not face_image_url:
                                        continue

                                    # Persist one person record for this live track. Do not use
                                    # clothing histograms as face embeddings: they merge different
                                    # people wearing similar colors.
                                    try:
                                        from app.services.identity_manager import IdentityManager
                                        im = IdentityManager(db)
                                        person, _ = im.resolve_person(
                                            tracking_id=f"P-{person_track['id'] if person_track else face_track_id}",
                                            face_embedding=None,
                                            name=face_identity,
                                            live_image=face_image_url,
                                        )
                                        face_identity = person.name
                                        if force_watchlist or force_reid:
                                            person.authorization_status = face_status
                                            db.commit()
                                        else:
                                            face_status = person.authorization_status
                                        logger.info(
                                            f"[{camera_id}] Identity resolved: person_id={person.id} "
                                            f"name={face_identity} status={face_status} "
                                            f"entry_count={person.entry_count}"
                                        )
                                    except Exception as e_id:
                                        db.rollback()
                                        logger.warning(f"[{camera_id}] IdentityManager error (using session state): {e_id}")

                                    now_iso = datetime.utcnow().isoformat() + "Z"

                                    frame_h, frame_w = frame.shape[:2]
                                    face_area = w * h
                                    frame_area = frame_w * frame_h
                                    confidence_score = 85 + int((face_area / max(frame_area, 1)) * 10)

                                    face_record = None
                                    if person_track and person_track.get("record_id"):
                                        face_record = db.query(FaceRecord).filter(
                                            FaceRecord.id == person_track["record_id"]
                                        ).first()
                                    if face_record:
                                        face_record.identity = face_identity
                                        face_record.confidence = confidence_score
                                        face_record.timestamp = now_iso
                                        face_record.status = face_status
                                        face_record.image = face_image_url
                                    else:
                                        face_record = FaceRecord(
                                            id=f"FACE-LOG-{uuid.uuid4().hex[:8]}",
                                            cameraId=camera_id,
                                            identity=face_identity,
                                            confidence=confidence_score,
                                            timestamp=now_iso,
                                            database="Local DB",
                                            status=face_status,
                                            image=face_image_url,
                                            direction="Inbound" if "01" in camera_id else "Unknown"
                                        )
                                        db.add(face_record)
                                    db.commit()
                                    db.refresh(face_record)
                                    if person_track:
                                        person_track["record_id"] = face_record.id
                                        person_track["identity"] = face_identity
                                        person_track["face_enhanced"] = True
                                    for track in self._face_tracks.get(camera_id, []):
                                        if track["id"] == face_track_id:
                                            track["logged"] = True
                                            break

                                    face_data = {
                                        "id": face_record.id,
                                        "cameraId": face_record.cameraId,
                                        "identity": face_record.identity,
                                        "confidence": face_record.confidence,
                                        "timestamp": face_record.timestamp,
                                        "database": face_record.database,
                                        "status": face_record.status,
                                        "image": face_record.image,
                                        "direction": face_record.direction
                                    }
                                    self._broadcast_sync({"type": "NEW_FACE", "data": face_data})

                                    # Send CRITICAL alert for watchlist face match
                                    if face_status == "FLAGGED":
                                        logger.warning(
                                            f"[{camera_id}] WATCHLIST face detected: {face_identity}"
                                        )
                                        self._broadcast_sync({
                                            "type": "NEW_ALERT",
                                            "data": {
                                                "id": f"ALRT-FACE-{int(time.time()*1000)}",
                                                "eventId": face_record.id,
                                                "severity": "CRITICAL",
                                                "riskScore": 95,
                                                "title": "Watchlist Face Detected",
                                                "what": f"Known threat: {face_identity}",
                                                "where": camera_id,
                                                "reason": "Facial match with watchlist database",
                                                "status": "NEW",
                                                "createdAt": now_iso,
                                                "reasons": ["High confidence biometric match"],
                                                "image": face_record.image
                                            }
                                        })

                # ===================================================
                # PIPELINE C: ANPR (vehicle / plate detection)
                # ===================================================
                if run_anpr:
                    try:
                        # ANPR result variables are fully scoped here — no leakage from face pipeline
                        vehicles, anpr_alerts = process_anpr_frame(
                            db,
                            frame,
                            camera_id=camera_id,
                            direction="Live",
                            source="live",
                            dedupe_seconds=10,
                        )
                        for vehicle in vehicles:
                            logger.info(
                                f"[{camera_id}] ANPR result: plate={vehicle.get('plateNumber')} "
                                f"status={vehicle.get('status')} conf={vehicle.get('confidence')}"
                            )
                            self._broadcast_sync({"type": "vehicle", "vehicle": vehicle})
                        for anpr_alert in anpr_alerts:
                            logger.warning(
                                f"[{camera_id}] ANPR watchlist alert: {anpr_alert.get('title')}"
                            )
                            self._broadcast_sync({"type": "NEW_ALERT", "data": anpr_alert})
                    except Exception as anpr_exc:
                        db.rollback()
                        logger.error(f"[{camera_id}] ANPR pipeline error: {anpr_exc}")

            except Exception as exc:
                db.rollback()
                logger.exception(f"[{camera_id}] Worker inference failed: {exc}")

    def enqueue(self, camera_id: str, frame: np.ndarray, context: dict = None) -> bool:
        if not self._loop:
            try:
                self._loop = asyncio.get_running_loop()
            except RuntimeError:
                pass

        if camera_id not in self._workers:
            worker = CameraWorker(camera_id, priority="NORMAL", max_queue_size=5)
            worker.set_callback(self._inference_bridge)
            worker.start()
            self._workers[camera_id] = worker
            logger.info(f"Initialized new CameraWorker for {camera_id}")

        return self._workers[camera_id].enqueue_frame(frame, context=context)

    def shutdown_all(self):
        for w in self._workers.values():
            w.stop()
        self._workers.clear()


worker_pool = WorkerPool()
