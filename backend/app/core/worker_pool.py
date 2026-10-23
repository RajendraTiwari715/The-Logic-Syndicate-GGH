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
from app.services.anpr_pipeline import process_anpr_frame, encode_image_base64
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
        self._known_faces: list = []  # [{id, hist, last_seen, identity}]
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
                            for idx, det in enumerate(detections):
                                x1, y1, x2, y2 = det["bbox"]
                                stable_id = f"{camera_id}-{det['class']}-{idx}"
                                self._broadcast_sync({
                                    "type": "detection",
                                    "data": {
                                        "id": f"det-{stable_id}",
                                        "cameraId": camera_id,
                                        "objectType": det["class"],
                                        "trackingId": f"TRK-{stable_id}",
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

                                for face_idx, (x, y, w, h) in enumerate(faces):
                                    # Crop face with padding for UI display
                                    px = max(0, x - 20)
                                    py = max(0, y - 20)
                                    pw = min(frame.shape[1] - px, w + 40)
                                    ph = min(frame.shape[0] - py, h + 40)
                                    face_crop = frame[py:py+ph, px:px+pw]

                                    if face_crop.size == 0:
                                        continue

                                    # Crop face + upper body for color histogram Re-ID (includes clothing color entropy)
                                    body_h = min(frame.shape[0] - py, h + int(h * 2.5))
                                    body_crop = frame[py:py+body_h, px:px+pw]

                                    # HSV histogram for basic Re-ID
                                    hsv_crop = cv2.cvtColor(body_crop, cv2.COLOR_BGR2HSV)
                                    hist = cv2.calcHist([hsv_crop], [0, 1], None, [50, 60], [0, 180, 0, 256])
                                    cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)

                                    # Try to match against known faces in this session
                                    matched_face = None
                                    for kf in self._known_faces:
                                        score = cv2.compareHist(hist, kf["hist"], cv2.HISTCMP_CORREL)
                                        if score > 0.85:  # Stricter threshold because body color is more distinct
                                            matched_face = kf
                                            logger.debug(
                                                f"[{camera_id}] Face re-ID match: id={kf['id']} score={score:.3f}"
                                            )
                                            break

                                    TEN_HOURS_SEC = 10 * 3600

                                    # Scoped variables for this face detection result
                                    face_identity = "UNKNOWN"
                                    face_status = "UNKNOWN"
                                    is_new_entry_event = False
                                    face_id_str = None

                                    if matched_face:
                                        if current_time - matched_face["last_seen"] < TEN_HOURS_SEC:
                                            # Seen within 10 hours — update last_seen, no new log entry
                                            matched_face["last_seen"] = current_time
                                            logger.debug(f"[{camera_id}] Face seen recently, skipping DB log")
                                            continue
                                        else:
                                            # Re-entry after 10 hours
                                            matched_face["last_seen"] = current_time
                                            face_identity = matched_face["identity"]
                                            face_status = matched_face["status"]
                                            face_id_str = matched_face["id"]
                                            is_new_entry_event = True
                                    else:
                                        # New face detected
                                        if force_watchlist:
                                            face_identity = "Watchlist Target"
                                            face_status = "FLAGGED"
                                        elif force_reid:
                                            face_identity = "Verified Staff"
                                            face_status = "AUTHORIZED"
                                        else:
                                            face_identity = f"Unknown ID-{uuid.uuid4().hex[:4].upper()}"
                                            face_status = "UNKNOWN"

                                        face_id_str = f"FACE-{uuid.uuid4().hex[:8]}"
                                        self._known_faces.append({
                                            "id": face_id_str,
                                            "hist": hist,
                                            "last_seen": current_time,
                                            "identity": face_identity,
                                            "status": face_status
                                        })
                                        is_new_entry_event = True

                                        logger.info(
                                            f"[{camera_id}] New face detected: id={face_id_str} "
                                            f"status={face_status} identity={face_identity}"
                                        )

                                    # Attempt deep identity resolution via IdentityManager
                                    try:
                                        from app.services.identity_manager import IdentityManager
                                        im = IdentityManager(db)
                                        tracking_id = f"P-{face_id_str}"
                                        person, is_new_entry_event = im.resolve_person(
                                            tracking_id=tracking_id,
                                            face_embedding=hist.flatten().tolist(),
                                            name=face_identity if face_identity not in ("UNKNOWN", f"Unknown ID-{face_id_str[-4:]}") else None
                                        )
                                        face_identity = person.name
                                        face_status = person.authorization_status
                                        logger.info(
                                            f"[{camera_id}] Identity resolved: person_id={person.id} "
                                            f"name={face_identity} status={face_status} "
                                            f"entry_count={person.entry_count} is_new={is_new_entry_event}"
                                        )
                                    except Exception as e_id:
                                        logger.warning(f"[{camera_id}] IdentityManager error (using session state): {e_id}")

                                    # Only write DB record and broadcast on genuine new entry events
                                    if not is_new_entry_event:
                                        continue

                                    b64_img = encode_image_base64(face_crop)
                                    now_iso = datetime.utcnow().isoformat() + "Z"

                                    frame_h, frame_w = frame.shape[:2]
                                    face_area = w * h
                                    frame_area = frame_w * frame_h
                                    confidence_score = 85 + int((face_area / max(frame_area, 1)) * 10)

                                    face_record = FaceRecord(
                                        id=f"FACE-LOG-{uuid.uuid4().hex[:8]}",
                                        cameraId=camera_id,
                                        identity=face_identity,
                                        confidence=confidence_score,
                                        timestamp=now_iso,
                                        database="Local DB",
                                        status=face_status,
                                        image=f"data:image/jpeg;base64,{b64_img}" if b64_img else None,
                                        direction="Inbound" if "01" in camera_id else "Unknown"
                                    )
                                    db.add(face_record)
                                    db.commit()
                                    db.refresh(face_record)

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
