from __future__ import annotations

import base64
import hashlib
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from sqlalchemy.orm import Session

from app.models.core_models import Alert, Camera, EventItem, Evidence, Plate, VehicleRecord, WatchlistRecord
from app.vision.anpr import ANPRCapture, ANPRService, anpr_service


BACKEND_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BACKEND_DIR / "data"
ANPR_DIR = DATA_DIR / "anpr"
ANPR_UPLOAD_DIR = ANPR_DIR / "uploads"
ANPR_DIR.mkdir(parents=True, exist_ok=True)
ANPR_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PUBLIC_API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")

_recent_live_captures: dict[str, datetime] = {}


def utcnow() -> datetime:
    return datetime.utcnow()


def timestamp_label(timestamp: datetime) -> str:
    return timestamp.strftime("%d %b %Y, %I:%M:%S %p")


def normalize_plate(text: str) -> str:
    return ANPRService.normalize_plate(text)


def format_plate(text: str) -> str:
    return ANPRService.format_plate(text)


def media_url(relative_path: str | None) -> str | None:
    if not relative_path:
        return None
    if relative_path.startswith("http://") or relative_path.startswith("https://"):
        return relative_path
    return f"{PUBLIC_API_URL}{relative_path}"


def decode_image_bytes(contents: bytes) -> np.ndarray:
    frame = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError("Invalid image file format")
    return frame


def decode_base64_frame(image_data: str) -> np.ndarray:
    if "," in image_data:
        image_data = image_data.split(",", 1)[1]
    try:
        raw = base64.b64decode(image_data, validate=True)
    except Exception as exc:
        raise ValueError("Invalid base64 image payload") from exc
    return decode_image_bytes(raw)


def save_upload_file(contents: bytes, original_filename: str | None = None) -> Path:
    suffix = Path(original_filename or "").suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}:
        suffix = ".mp4"
    path = ANPR_UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    path.write_bytes(contents)
    return path


def encode_image_base64(frame: np.ndarray, quality: int = 80) -> str:
    """
    Canonical helper: encode a real OpenCV BGR frame to a base64 JPEG string.
    Used for face crops, ANPR crops, evidence previews, and WebSocket payloads.
    Never fabricates images — only encodes real numpy arrays from camera frames.
    Returns empty string on encoding failure.
    """
    if frame is None or frame.size == 0:
        return ""
    try:
        ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if not ret:
            return ""
        return base64.b64encode(buf.tobytes()).decode("utf-8")
    except Exception:
        return ""


def safe_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    return cleaned[:80] or "ANPR"


def _ensure_camera(db: Session, camera_id: str) -> None:
    if db.query(Camera).filter(Camera.id == camera_id).first():
        return

    db.add(
        Camera(
            id=camera_id,
            name=f"ANPR {camera_id}",
            bop="ANPR",
            location="ANPR input source",
            status="ONLINE",
            fps=0,
            latency=0,
            storage=0,
            health=100,
            lastHeartbeat=utcnow().isoformat() + "Z",
            signalQuality=100,
            scenario="anpr",
            recording=True,
            detectionCount=0,
            coords={"x": 50, "y": 50},
            mapCoord={"lat": 0, "lng": 0},
        )
    )
    db.flush()


def _watchlist_match(db: Session, plate_number: str) -> WatchlistRecord | None:
    normalized_plate = normalize_plate(plate_number)
    for record in db.query(WatchlistRecord).all():
        if normalize_plate(record.plate_number) == normalized_plate:
            return record
    return None


def _vehicle_type_label(vehicle_type: str) -> str:
    labels = {
        "car": "Car",
        "motorcycle": "Motorcycle",
        "bus": "Bus",
        "truck": "Truck",
        "vehicle": "Vehicle",
    }
    return labels.get(vehicle_type.lower(), vehicle_type.title() if vehicle_type else "Vehicle")


def _crop_vehicle(frame: np.ndarray, capture: ANPRCapture) -> np.ndarray:
    height, width = frame.shape[:2]
    x1, y1, x2, y2 = capture.vehicle_bbox_xyxy
    pad_x = max(8, int((x2 - x1) * 0.06))
    pad_y = max(8, int((y2 - y1) * 0.08))
    x1 = max(0, x1 - pad_x)
    y1 = max(0, y1 - pad_y)
    x2 = min(width, x2 + pad_x)
    y2 = min(height, y2 + pad_y)
    crop = frame[y1:y2, x1:x2]
    return crop if crop.size else frame


def _save_anpr_artifacts(
    frame: np.ndarray,
    capture: ANPRCapture,
    camera_id: str,
    timestamp: datetime,
    is_watchlist: bool = False,
) -> tuple[str, str, str, str | None, str | None]:
    """Saves vehicle crop, zoomed plate crop, and annotated HUD frame."""
    day_dir = ANPR_DIR / timestamp.strftime("%Y%m%d")
    day_dir.mkdir(parents=True, exist_ok=True)
    time_prefix = timestamp.strftime("%H%M%S_%f")
    safe_plate = normalize_plate(capture.plate_number) or "UNKNOWN"
    cam_part = safe_filename_part(camera_id)

    # 1. Clean vehicle crop
    crop_filename = f"{time_prefix}_{cam_part}_{safe_plate}_crop.jpg"
    crop_path = day_dir / crop_filename
    crop = _crop_vehicle(frame, capture)
    cv2.imwrite(str(crop_path), crop)
    digest = hashlib.sha256(crop_path.read_bytes()).hexdigest()
    crop_url = f"/media/anpr/{timestamp.strftime('%Y%m%d')}/{crop_filename}"

    # 2. Plate tight crop (zoom on plate numbers)
    plate_url = None
    if capture.plate_bbox_xyxy:
        px1, py1, px2, py2 = capture.plate_bbox_xyxy
        plate_tight = frame[max(0, py1):min(frame.shape[0], py2), max(0, px1):min(frame.shape[1], px2)]
        if plate_tight.size > 0:
            plate_filename = f"{time_prefix}_{cam_part}_{safe_plate}_plate.jpg"
            plate_path = day_dir / plate_filename
            cv2.imwrite(str(plate_path), plate_tight)
            plate_url = f"/media/anpr/{timestamp.strftime('%Y%m%d')}/{plate_filename}"

    # 3. Full Annotated HUD Frame
    annotated = anpr_service.draw_annotations(
        frame,
        [capture],
        camera_id=camera_id,
        timestamp_str=timestamp.strftime("%d %b %Y, %H:%M:%S"),
        watchlist_plates={capture.plate_number} if is_watchlist else set(),
    )
    annotated_filename = f"{time_prefix}_{cam_part}_{safe_plate}_annotated.jpg"
    annotated_path = day_dir / annotated_filename
    cv2.imwrite(str(annotated_path), annotated)
    annotated_url = f"/media/anpr/{timestamp.strftime('%Y%m%d')}/{annotated_filename}"

    return str(crop_path), crop_url, digest, plate_url, annotated_url


def vehicle_to_payload(db: Session, vehicle: VehicleRecord) -> dict:
    plate_record = db.query(Plate).filter(Plate.vehicle_id == vehicle.id).order_by(Plate.timestamp.desc()).first()
    event_record = db.query(EventItem).filter(EventItem.trackingId == vehicle.id).first()
    image = None
    annotated_image = None
    plate_image = None
    details = {}

    if event_record and event_record.details and isinstance(event_record.details, dict):
        details = event_record.details
        annotated_image = media_url(details.get("annotated_image_url"))
        plate_image = media_url(details.get("plate_crop_url"))

    if plate_record and plate_record.evidence_id:
        evidence = db.query(Evidence).filter(Evidence.id == plate_record.evidence_id).first()
        if evidence:
            image = media_url(evidence.file_url)

    state_code = anpr_service.get_state_code(vehicle.plateNumber)

    return {
        "id": vehicle.id,
        "cameraId": vehicle.cameraId,
        "vehicleType": vehicle.vehicleType,
        "plateNumber": vehicle.plateNumber,
        "confidence": vehicle.confidence,
        "timestamp": vehicle.timestamp,
        "status": vehicle.status,
        "direction": vehicle.direction or "Unknown",
        "image": image,
        "annotatedImage": annotated_image or image,
        "plateImage": plate_image,
        "stateCode": state_code,
        "sharpness": round(float(details.get("sharpness", 0.0)), 1),
        "rawText": details.get("raw_ocr_text", vehicle.plateNumber),
    }


def _recent_capture_allowed(camera_id: str, plate_number: str, dedupe_seconds: int) -> bool:
    if dedupe_seconds <= 0:
        return True

    now = utcnow()
    key = f"{camera_id}:{normalize_plate(plate_number)}"
    last_seen = _recent_live_captures.get(key)
    if last_seen and (now - last_seen).total_seconds() < dedupe_seconds:
        return False

    _recent_live_captures[key] = now
    stale_keys = [item for item, seen_at in _recent_live_captures.items() if (now - seen_at).total_seconds() > 300]
    for item in stale_keys:
        _recent_live_captures.pop(item, None)
    return True


def _persist_capture(
    db: Session,
    capture: ANPRCapture,
    frame: np.ndarray,
    camera_id: str,
    direction: str,
    source: str,
    timestamp: datetime,
) -> tuple[dict, dict | None]:
    _ensure_camera(db, camera_id)

    from app.services.identity_manager import IdentityManager
    id_manager = IdentityManager(db)
    
    plate_norm = normalize_plate(capture.plate_number)
    if not plate_norm:
        return {}, None
        
    vehicle_id = f"V-ANPR-{plate_norm}"
    vehicle, is_new_entry = id_manager.resolve_vehicle(vehicle_id, capture.plate_number)
    
    if not is_new_entry:
        # 2-minute rule suppressed this entry (bounce or same session)
        return vehicle_to_payload(db, vehicle), None
        
    matched_watchlist = _watchlist_match(db, capture.plate_number)
    status = "WATCHLIST" if matched_watchlist else "UNKNOWN"
    # Overwrite status with fresh watchlist info
    vehicle.status = status
    vehicle.vehicleType = _vehicle_type_label(capture.vehicle_type)
    vehicle.confidence = int(round(capture.plate_confidence * 100))
    vehicle.direction = direction
    db.commit()
    
    display_plate = format_plate(capture.plate_number)
    confidence = int(round(capture.plate_confidence * 100))
    event_id = f"EVT-{uuid.uuid4().hex[:12].upper()}"
    timestamp_iso = timestamp.isoformat() + "Z"

    # Only save new images if it's the very first entry of this vehicle
    if vehicle.entry_count == 1:
        file_path, file_url, sha256_hash, plate_crop_url, annotated_url = _save_anpr_artifacts(
            frame, capture, camera_id, timestamp, is_watchlist=bool(matched_watchlist)
        )
        if hasattr(vehicle, 'representative_image'):
            vehicle.representative_image = file_url
            db.commit()
    else:
        # Re-entry after 2 minutes — reuse existing image pointers
        file_path, file_url, sha256_hash, plate_crop_url, annotated_url = "", "", "", "", ""
        if hasattr(vehicle, 'representative_image') and vehicle.representative_image:
            file_url = vehicle.representative_image
            annotated_url = file_url

    event = EventItem(
        id=event_id,
        cameraId=camera_id,
        eventType="WATCHLIST_MATCH" if matched_watchlist else "PLATE_DETECTED",
        severity="CRITICAL" if matched_watchlist else "LOW",
        trackingId=vehicle_id,
        description=(
            f"Watchlist vehicle {display_plate} detected"
            if matched_watchlist
            else f"Vehicle plate {display_plate} detected"
        ),
        timestamp=timestamp_iso,
        status="NEW",
        riskScore=95 if matched_watchlist else 20,
        reasons=[
            f"Plate OCR confidence {confidence}%",
            f"Vehicle type: {_vehicle_type_label(capture.vehicle_type)}",
            f"Source: {source}",
            f"Sharpness index: {round(capture.sharpness, 1)}",
        ],
        confidence=float(confidence),
        details={
            "plate_number": display_plate,
            "normalized_plate": normalize_plate(capture.plate_number),
            "vehicle_type": _vehicle_type_label(capture.vehicle_type),
            "vehicle_confidence": round(capture.vehicle_confidence * 100, 1),
            "raw_ocr_text": capture.raw_text,
            "image_url": file_url,
            "annotated_image_url": annotated_url,
            "plate_crop_url": plate_crop_url,
            "sharpness": round(capture.sharpness, 1),
            "state_code": capture.state_code,
        },
    )
    db.add(event)
    
    # Store evidence to disk - assign to variable so we can reference evidence.id below
    evidence_id_val = f"EVD-{uuid.uuid4().hex[:12].upper()}"
    evidence = Evidence(
        id=evidence_id_val,
        event_id=event_id,
        camera_id=camera_id,
        file_location=str(file_path),
        file_url=file_url,
        file_type="SNAPSHOT",
        sha256_hash=sha256_hash,
        integrity_status="VERIFIED",
    )
    db.add(evidence)

    db.commit()
    db.refresh(vehicle)
    db.refresh(event)
    
    from app.core.ledger import record_event_ledger
    ledger_hash = record_event_ledger(db, event)
    if ledger_hash:
        event.details = {"blockchain_hash": ledger_hash} # Expose payload hash back to UI

    plate = Plate(
        id=str(uuid.uuid4()),
        vehicle_id=vehicle_id,
        camera_id=camera_id,
        raw_ocr_text=capture.raw_text,
        normalized_plate=normalize_plate(capture.plate_number),
        confidence=capture.plate_confidence,
        timestamp=timestamp,
        evidence_id=evidence_id_val,
    )
    db.add(plate)

    alert_payload = None
    if matched_watchlist:
        alert_id = f"ALRT-{uuid.uuid4().hex[:8].upper()}"
        alert = Alert(
            id=alert_id,
            eventId=event_id,
            severity="CRITICAL",
            riskScore=95,
            reason=f"Vehicle plate {display_plate} matches watchlist.",
            reasons=[
                "ANPR watchlist match",
                f"Registered reason: {matched_watchlist.description or 'No description'}",
            ],
            status="NEW",
            createdAt=timestamp_iso,
            acknowledgedAt=None,
            resolvedAt=None,
            cameraId=camera_id,
            trackingId=vehicle_id,
            title="Watchlist Vehicle Detected",
            what=f"{_vehicle_type_label(capture.vehicle_type)} with plate {display_plate}",
            where=camera_id,
            when_time=timestamp_label(timestamp),
            object=display_plate,
            why=f"Plate matches watchlist entry {matched_watchlist.id}",
            zone=None,
            confidence=confidence,
        )
        db.add(alert)
        alert_payload = {
            "id": alert_id,
            "eventId": event_id,
            "severity": "CRITICAL",
            "riskScore": 95,
            "reason": alert.reason,
            "reasons": alert.reasons,
            "status": "NEW",
            "createdAt": timestamp_iso,
            "acknowledgedAt": None,
            "resolvedAt": None,
            "cameraId": camera_id,
            "trackingId": vehicle_id,
            "title": alert.title,
            "what": alert.what,
            "where": alert.where,
            "when": alert.when_time,
            "object": alert.object,
            "why": alert.why,
            "confidence": confidence,
            "image": media_url(file_url),
            "annotatedImage": media_url(annotated_url),
        }

    db.flush()
    payload = vehicle_to_payload(db, vehicle)
    return payload, alert_payload


def process_anpr_frame(
    db: Session,
    frame: np.ndarray,
    camera_id: str = "ANPR-UPLOAD",
    direction: str = "Unknown",
    source: str = "image",
    dedupe_seconds: int = 0,
    seen_plate_numbers: set[str] | None = None,
) -> tuple[list[dict], list[dict]]:
    timestamp = utcnow()
    payloads: list[dict] = []
    alert_payloads: list[dict] = []

    for capture in anpr_service.analyze_frame(frame):
        normalized_plate = normalize_plate(capture.plate_number)
        if seen_plate_numbers is not None and normalized_plate in seen_plate_numbers:
            continue
        if not _recent_capture_allowed(camera_id, capture.plate_number, dedupe_seconds):
            continue
        payload, alert_payload = _persist_capture(db, capture, frame, camera_id, direction, source, timestamp)
        if seen_plate_numbers is not None:
            seen_plate_numbers.add(normalized_plate)
        payloads.append(payload)
        if alert_payload:
            alert_payloads.append(alert_payload)

    db.commit()

    # Broadcast to connected clients if an asyncio loop is active
    try:
        import asyncio
        from app.ws_manager import manager
        loop = asyncio.get_event_loop()
        if loop.is_running():
            for p in payloads:
                loop.create_task(manager.broadcast({"type": "vehicle", "vehicle": p}))
            for a in alert_payloads:
                loop.create_task(manager.broadcast({"type": "NEW_ALERT", "data": a}))
    except Exception:
        pass

    return payloads, alert_payloads


def process_recorded_video(
    db: Session,
    video_path: Path,
    camera_id: str = "ANPR-RECORDED",
    direction: str = "Unknown",
    sample_every_n_frames: int = 15,
    max_captures: int = 50,
) -> dict:
    """High-precision video processing with multi-frame temporal consensus and quality scoring."""
    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise ValueError("Could not open recorded video")

    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    total_video_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration_sec = round(total_video_frames / fps, 1) if fps > 0 else 0.0

    frame_index = 0
    processed_frames = 0
    
    # Store candidate detections across frames: plate -> list of (score, capture, frame)
    plate_candidates: dict[str, list[tuple[float, ANPRCapture, np.ndarray]]] = {}

    try:
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                break

            frame_index += 1
            if frame_index % max(sample_every_n_frames, 1) != 0:
                continue

            processed_frames += 1
            frame_captures = anpr_service.analyze_frame(frame)
            
            for cap in frame_captures:
                norm_plate = normalize_plate(cap.plate_number)
                # Quality score combines OCR confidence and sharpness
                quality_score = cap.plate_confidence * 0.75 + min(cap.sharpness / 200.0, 0.25)
                plate_candidates.setdefault(norm_plate, []).append((quality_score, cap, frame.copy()))

    finally:
        capture.release()

    # Temporal Consensus: for each unique plate, pick the frame with highest quality score
    payloads: list[dict] = []
    alert_payloads: list[dict] = []
    timestamp = utcnow()

    sorted_plates = sorted(plate_candidates.keys(), key=lambda p: max(c[0] for c in plate_candidates[p]), reverse=True)
    for norm_plate in sorted_plates[:max_captures]:
        best_candidate = max(plate_candidates[norm_plate], key=lambda item: item[0])
        _, best_cap, best_frame = best_candidate
        payload, alert_payload = _persist_capture(
            db, best_cap, best_frame, camera_id=camera_id, direction=direction, source="recorded_video", timestamp=timestamp
        )
        payloads.append(payload)
        if alert_payload:
            alert_payloads.append(alert_payload)

    db.commit()

    return {
        "ok": True,
        "source_path": str(video_path),
        "fps": round(fps, 1),
        "duration_seconds": duration_sec,
        "frames_read": frame_index,
        "frames_processed": processed_frames,
        "count": len(payloads),
        "captures": payloads,
        "alerts": alert_payloads,
    }
