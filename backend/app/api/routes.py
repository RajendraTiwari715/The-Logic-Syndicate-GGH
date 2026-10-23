from __future__ import annotations

import asyncio
import json
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database.base import get_db
from app.database.models import AlertModel, CameraModel, DetectionModel, EventModel, TrackingModel, ZoneModel, WatchlistModel
from app.models.schemas import CameraCreateRequest, HealthSummary, VideoUploadResponse, ZoneCreateRequest, WatchlistCreateRequest
from app.services.camera_service import CameraManager, safe_json_loads


router = APIRouter()


def get_camera_manager(request: Request) -> CameraManager:
    return request.app.state.camera_manager


def camera_to_dict(camera: CameraModel) -> dict:
    return {
        "id": camera.id,
        "name": camera.name,
        "bop": camera.bop,
        "location": camera.location,
        "status": camera.status,
        "fps": round(camera.fps or 0.0, 2),
        "latency": round(camera.latency or 0.0, 2),
        "storage": round(camera.storage or 0.0, 2),
        "health": round(camera.health or 0.0, 2),
        "lastHeartbeat": camera.last_heartbeat.isoformat() if camera.last_heartbeat else datetime.utcnow().isoformat(),
        "signalQuality": round(camera.signal_quality or 0.0, 2),
        "scenario": camera.scenario,
        "recording": bool(camera.recording),
        "detectionCount": int(camera.detection_count or 0),
        "coords": {"x": camera.coords_x, "y": camera.coords_y},
        "mapCoord": {"lat": camera.map_lat, "lng": camera.map_lng},
        "streamUrl": f"{settings.api_base_url}/api/stream/{camera.id}",
        "sourceType": camera.source_type,
        "snapshotPath": camera.snapshot_path,
        "reconnectAttempts": int(camera.reconnect_attempts or 0),
    }


def detection_to_dict(record: DetectionModel) -> dict:
    return {
        "id": record.id,
        "cameraId": record.camera_id,
        "objectType": record.object_type,
        "trackingId": record.tracking_id,
        "confidence": round(record.confidence * 100, 1),
        "timestamp": record.timestamp.isoformat(),
        "bbox": {
            "x": record.bbox_x,
            "y": record.bbox_y,
            "w": record.bbox_w,
            "h": record.bbox_h,
        },
        "label": record.object_class.upper(),
        "direction": record.direction,
    }


def event_to_dict(record: EventModel) -> dict:
    reasons = safe_json_loads(record.reasons_json, [])
    return {
        "id": record.id,
        "cameraId": record.camera_id,
        "eventType": record.event_type.replace("_", " ").title(),
        "severity": record.severity,
        "trackingId": record.tracking_id,
        "description": record.description,
        "timestamp": record.timestamp.isoformat(),
        "status": record.status,
        "riskScore": record.risk_score,
        "reasons": reasons,
        "snapshotPath": record.snapshot_path,
    }


def alert_to_dict(record: AlertModel) -> dict:
    reasons = safe_json_loads(record.reasons_json, [])
    return {
        "id": record.id,
        "eventId": record.event_id,
        "severity": record.severity,
        "riskScore": record.risk_score,
        "reason": record.reason,
        "reasons": reasons,
        "status": record.status,
        "createdAt": record.created_at.isoformat(),
        "acknowledgedAt": record.acknowledged_at.isoformat() if record.acknowledged_at else None,
        "resolvedAt": record.resolved_at.isoformat() if record.resolved_at else None,
        "cameraId": record.camera_id,
        "trackingId": record.tracking_id,
        "title": record.title,
        "what": record.what,
        "where": record.where,
        "when": record.when_display,
        "object": record.object_label,
        "why": record.why,
        "zone": record.zone,
        "confidence": round(record.confidence, 1),
        "snapshotPath": record.snapshot_path,
    }


def zone_to_dict(record: ZoneModel) -> dict:
    return {
        "id": record.id,
        "cameraId": record.camera_id,
        "name": record.name,
        "zoneType": record.zone_type,
        "severity": record.severity,
        "coordinates": safe_json_loads(record.coordinates_json, []),
        "rule": record.rule,
    }

def watchlist_to_dict(record: WatchlistModel) -> dict:
    return {
        "id": record.id,
        "plate_number": record.plate_number,
        "description": record.description,
        "added_at": record.added_at.isoformat(),
    }



def tracking_to_dict(record: TrackingModel) -> dict:
    history = safe_json_loads(record.history_json, [])
    duration_seconds = int(record.duration_seconds or 0)
    minutes, seconds = divmod(duration_seconds, 60)
    return {
        "trackingId": record.tracking_id,
        "objectType": record.object_type,
        "cameraId": record.camera_id,
        "direction": record.direction,
        "duration": f"{minutes:02d}:{seconds:02d}",
        "status": record.status,
        "firstSeen": record.first_seen.isoformat(),
        "lastSeen": record.last_seen.isoformat(),
        "history": history,
        "label": record.object_class.upper(),
        "confidence": round(record.confidence * 100, 1),
    }


@router.get("/api/cameras")
def list_cameras(db: Session = Depends(get_db)) -> list[dict]:
    cameras = db.query(CameraModel).order_by(CameraModel.id.asc()).all()
    return [camera_to_dict(camera) for camera in cameras]


@router.get("/api/cameras/{camera_id}")
def get_camera(camera_id: str, db: Session = Depends(get_db)) -> dict:
    camera = db.get(CameraModel, camera_id)
    if camera is None:
        raise HTTPException(status_code=404, detail="Camera not found")
    return camera_to_dict(camera)


@router.post("/api/cameras")
def create_camera(payload: CameraCreateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    camera_id = payload.camera_id or f"BOP-{uuid.uuid4().hex[:4].upper()}"
    camera = db.get(CameraModel, camera_id)
    if camera is None:
        camera = CameraModel(
            id=camera_id,
            name=payload.name or camera_id,
            bop=payload.bop or "BOP Dynamic",
            location=payload.location or "Dynamic camera source",
            source=payload.source,
            source_type=payload.source_type or CameraManager.detect_source_type(payload.source),
            status="OFFLINE",
            fps=0.0,
            latency=0.0,
            storage=0.0,
            health=0.0,
            signal_quality=0.0,
            scenario="normal",
            recording=1,
            detection_count=0,
            coords_x=payload.coords.x if payload.coords else 20.0,
            coords_y=payload.coords.y if payload.coords else 20.0,
            map_lat=payload.map_coord.lat if payload.map_coord else settings.default_map_lat,
            map_lng=payload.map_coord.lng if payload.map_coord else settings.default_map_lng,
        )
        db.add(camera)
    else:
        camera.name = payload.name or camera.name
        camera.bop = payload.bop or camera.bop
        camera.location = payload.location or camera.location
        camera.source = payload.source
        camera.source_type = payload.source_type or CameraManager.detect_source_type(payload.source)
        if payload.coords:
            camera.coords_x = payload.coords.x
            camera.coords_y = payload.coords.y
        if payload.map_coord:
            camera.map_lat = payload.map_coord.lat
            camera.map_lng = payload.map_coord.lng
    db.commit()
    request.app.state.camera_manager.restart_camera(camera_id)
    db.refresh(camera)
    return camera_to_dict(camera)


@router.post("/api/cameras/upload", response_model=VideoUploadResponse)
async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
    suffix = Path(file.filename or "uploaded-video.mp4").suffix or ".mp4"
    filename = f"{uuid.uuid4().hex}{suffix}"
    output_path = Path(settings.upload_dir) / filename
    contents = await file.read()
    output_path.write_bytes(contents)
    return VideoUploadResponse(filename=file.filename or filename, source_path=str(output_path))


@router.get("/api/events")
def list_events(db: Session = Depends(get_db)) -> list[dict]:
    events = db.query(EventModel).order_by(EventModel.timestamp.desc()).limit(200).all()
    return [event_to_dict(event) for event in events]


@router.get("/api/alerts")
def list_alerts(db: Session = Depends(get_db)) -> list[dict]:
    alerts = db.query(AlertModel).order_by(AlertModel.created_at.desc()).limit(200).all()
    return [alert_to_dict(alert) for alert in alerts]


@router.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    alert = db.get(AlertModel, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_at = datetime.utcnow()
    event = db.get(EventModel, alert.event_id)
    if event is not None:
        event.status = "ACKNOWLEDGED"
    db.commit()
    payload = alert_to_dict(alert)
    request.app.state.websocket_manager.broadcast_from_thread({"event": "alert_updated", "alert": payload})
    return payload


@router.post("/api/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    alert = db.get(AlertModel, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.utcnow()
    event = db.get(EventModel, alert.event_id)
    if event is not None:
        event.status = "RESOLVED"
    db.commit()
    payload = alert_to_dict(alert)
    request.app.state.websocket_manager.broadcast_from_thread({"event": "alert_updated", "alert": payload})
    return payload


@router.get("/api/detections")
def list_detections(camera_id: str | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = db.query(DetectionModel)
    if camera_id:
        query = query.filter(DetectionModel.camera_id == camera_id)
    detections = query.order_by(DetectionModel.timestamp.desc()).limit(200).all()
    return [detection_to_dict(detection) for detection in detections]


@router.get("/api/tracking")
def list_tracking(db: Session = Depends(get_db)) -> list[dict]:
    records = db.query(TrackingModel).order_by(TrackingModel.last_seen.desc()).limit(200).all()
    return [tracking_to_dict(record) for record in records]


@router.get("/api/tracking/{tracking_id}")
def get_tracking(tracking_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.get(TrackingModel, tracking_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Tracking record not found")
    return tracking_to_dict(record)


@router.get("/api/zones")
def list_zones(db: Session = Depends(get_db)) -> list[dict]:
    zones = db.query(ZoneModel).order_by(ZoneModel.created_at.desc()).all()
    return [zone_to_dict(zone) for zone in zones]


@router.post("/api/zones")
def create_zone(payload: ZoneCreateRequest, request: Request, db: Session = Depends(get_db)) -> dict:
    zone = ZoneModel(
        id=f"Z-{uuid.uuid4().hex[:10]}",
        camera_id=payload.camera_id,
        name=payload.name,
        zone_type=payload.zone_type,
        severity=payload.severity,
        coordinates_json=json.dumps([point.model_dump() for point in payload.coordinates]),
        rule=payload.rule or f"{payload.zone_type} -> {payload.severity} alert",
    )
    db.add(zone)
    db.commit()
    payload_dict = zone_to_dict(zone)
    request.app.state.websocket_manager.broadcast_from_thread({"event": "zone_created", "zone": payload_dict})
    return payload_dict


@router.delete("/api/zones/{zone_id}")
def delete_zone(zone_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    zone = db.get(ZoneModel, zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    db.delete(zone)
    db.commit()
    request.app.state.websocket_manager.broadcast_from_thread({"event": "zone_deleted", "zone_id": zone_id})
    return {"ok": True, "zoneId": zone_id}

@router.get("/api/watchlist")
def list_watchlist(db: Session = Depends(get_db)) -> list[dict]:
    records = db.query(WatchlistModel).order_by(WatchlistModel.added_at.desc()).all()
    return [watchlist_to_dict(r) for r in records]

@router.post("/api/watchlist")
def add_to_watchlist(payload: WatchlistCreateRequest, db: Session = Depends(get_db)) -> dict:
    record = db.query(WatchlistModel).filter(WatchlistModel.plate_number == payload.plate_number).first()
    if not record:
        record = WatchlistModel(
            id=f"W-{uuid.uuid4().hex[:8]}",
            plate_number=payload.plate_number,
            description=payload.description
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return watchlist_to_dict(record)

@router.delete("/api/watchlist/{watchlist_id}")
def delete_watchlist(watchlist_id: str, db: Session = Depends(get_db)) -> dict:
    record = db.get(WatchlistModel, watchlist_id)
    if record:
        db.delete(record)
        db.commit()
    return {"ok": True}

@router.post("/api/watchlist/upload")
async def upload_plate_image(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    from app.vision.anpr import anpr_service
    from app.services.anpr_pipeline import format_plate, normalize_plate
    import numpy as np
    import cv2
    
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(status_code=400, detail="Invalid image file format")
        
    ocr_result = anpr_service.process_plate_crop(img)
    if not ocr_result:
        raise HTTPException(status_code=400, detail="No readable plate number detected in the image")
        
    plate_number = format_plate(ocr_result.normalized)
    if not plate_number:
        raise HTTPException(status_code=400, detail="Extracted text contains no valid alphanumeric characters")
        
    norm_target = normalize_plate(plate_number)
    record = next((r for r in db.query(WatchlistModel).all() if normalize_plate(r.plate_number) == norm_target), None)

    if not record:
        record = WatchlistModel(
            id=f"W-{uuid.uuid4().hex[:8]}",
            plate_number=plate_number,
            description="Auto-added via Image Upload"
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
    return {"ok": True, "plate_number": plate_number, "record": watchlist_to_dict(record)}


@router.get("/api/system/health")
def get_system_health(db: Session = Depends(get_db)) -> dict:
    cameras = db.query(CameraModel).all()
    online = sum(1 for camera in cameras if camera.status == "ONLINE")
    offline = sum(1 for camera in cameras if camera.status == "OFFLINE")
    degraded = sum(1 for camera in cameras if camera.status == "DEGRADED")
    average_health = round(sum(camera.health for camera in cameras) / max(len(cameras), 1), 2)
    summary = HealthSummary(online=online, offline=offline, degraded=degraded, average_health=average_health)
    return {
        "summary": summary.model_dump(),
        "cameras": [camera_to_dict(camera) for camera in cameras],
    }


@router.get("/api/stream/{camera_id}")
async def stream_camera(camera_id: str, request: Request) -> StreamingResponse:
    camera_manager = get_camera_manager(request)

    async def generate() -> bytes:
        while True:
            frame = camera_manager.latest_frame(camera_id)
            if frame is None:
                await asyncio.sleep(0.1)
                continue
            yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
            await asyncio.sleep(1 / max(settings.max_fps, 1))

    return StreamingResponse(generate(), media_type="multipart/x-mixed-replace; boundary=frame")


@router.websocket("/ws/analytics")
async def analytics_socket(websocket: WebSocket) -> None:
    manager = websocket.app.state.websocket_manager
    await manager.connect(websocket)
    await websocket.send_json({"event": "connected", "timestamp": datetime.utcnow().isoformat()})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
