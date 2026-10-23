from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import time

from app.db.session import get_db
from app.models.core_models import Camera as DB_Camera
from app.models.user import User, UserRole
from app.schemas.core_schemas import Camera, CameraCreate
from app.api.deps import get_current_user, get_current_active_supervisor

router = APIRouter()

@router.get("/", response_model=List[Camera])
def get_cameras(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cameras = db.query(DB_Camera).all()
    return cameras

@router.get("/{camera_id}", response_model=Camera)
def get_camera(camera_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    return db_camera

from app.services.audit import log_audit_action

@router.post("/", response_model=Camera)
def create_camera(
    camera: CameraCreate, 
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    new_camera = DB_Camera(**camera.model_dump())
    db.add(new_camera)
    db.commit()
    db.refresh(new_camera)
    
    log_audit_action(db, str(supervisor.id), supervisor.username, "CREATE_CAMERA", f"Created camera {new_camera.name}", "Camera", str(new_camera.id))
    return new_camera

@router.put("/{camera_id}", response_model=Camera)
def update_camera(
    camera_id: str,
    camera_in: CameraCreate,
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    update_data = camera_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_camera, field, value)
        
    db.commit()
    db.refresh(db_camera)
    
    log_audit_action(db, str(supervisor.id), supervisor.username, "UPDATE_CAMERA", f"Updated camera rules {db_camera.name}", "Camera", str(db_camera.id))
    return db_camera

@router.put("/{camera_id}/status", response_model=Camera)
def update_camera_status(
    camera_id: str, 
    status: str, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db_camera.status = status
    db.commit()
    db.refresh(db_camera)
    log_audit_action(db, str(current_user.id), current_user.username, "UPDATE_CAMERA_STATUS", f"Switched status to {status}", "Camera", str(db_camera.id))
    return db_camera

@router.delete("/{camera_id}", response_model=Camera)
def delete_camera(
    camera_id: str,
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")
    
    db.delete(db_camera)
    db.commit()
    log_audit_action(db, str(supervisor.id), supervisor.username, "DELETE_CAMERA", f"Deleted camera {camera_id}", "Camera", camera_id)
    return db_camera


# =========================================================================
# UNIVERSAL CCTV INFRASTRUCTURE ADAPTER ENDPOINTS
# =========================================================================
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
import cv2
from app.services.universal_cctv_connector import UniversalCCTVConnector, cctv_manager
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline

class ProbeRequest(BaseModel):
    source: str

class GenerateUrlRequest(BaseModel):
    brand: str
    ip: str
    port: int = 554
    username: str = "admin"
    password: str = ""
    channel: int = 1
    custom_path: str = "live"

@router.post("/probe")
def probe_cctv_stream(req: ProbeRequest):
    """Probes any CCTV stream (RTSP, ONVIF, HTTP, Webcam) to verify connectivity before saving."""
    return UniversalCCTVConnector.probe_stream(req.source)

@router.post("/generate-url")
def generate_cctv_url(req: GenerateUrlRequest):
    """Generates vendor-compliant RTSP URL for Hikvision, Dahua, Axis, CP Plus, ONVIF, etc."""
    url = UniversalCCTVConnector.build_rtsp_url(
        brand=req.brand,
        ip=req.ip,
        port=req.port,
        username=req.username,
        password=req.password,
        channel=req.channel,
        custom_path=req.custom_path,
    )
    return {"brand": req.brand, "rtsp_url": url}

@router.post("/{camera_id}/start-ai")
def start_camera_ai(camera_id: str, db: Session = Depends(get_db)):
    """Starts autonomous AI processing on a specific CCTV stream."""
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if not db_camera:
        raise HTTPException(status_code=404, detail="Camera not found")

    source = db_camera.rtsp_url or "0"
    worker = cctv_manager.register_and_start(
        camera_id=camera_id,
        source=source,
        name=db_camera.name or "CCTV",
        ai_callback=master_ai_pipeline.process_live_cctv_frame,
    )
    db_camera.status = "LIVE"
    db.commit()
    return {"ok": True, "camera_id": camera_id, "status": worker.status, "source": source}

@router.post("/{camera_id}/stop-ai")
def stop_camera_ai(camera_id: str, db: Session = Depends(get_db)):
    """Stops autonomous AI processing for a camera."""
    cctv_manager.stop_camera(camera_id)
    db_camera = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
    if db_camera:
        db_camera.status = "DISCONNECTED"
        db.commit()
    return {"ok": True, "camera_id": camera_id, "status": "DISCONNECTED"}

@router.get("/{camera_id}/live")
def get_live_annotated_feed(camera_id: str):
    """Streams real-time tactical AI annotated video (MJPEG) with bounding boxes and HUD watermark."""
    worker = cctv_manager.get_worker(camera_id)
    if not worker:
        # Auto start worker on demand
        from app.db.session import SessionLocal
        with SessionLocal() as db:
            cam = db.query(DB_Camera).filter(DB_Camera.id == camera_id).first()
            source = cam.rtsp_url if cam and cam.rtsp_url else "0"
            worker = cctv_manager.register_and_start(
                camera_id=camera_id,
                source=source,
                name=cam.name if cam else camera_id,
                ai_callback=master_ai_pipeline.process_live_cctv_frame,
            )

    def frame_generator():
        while True:
            frame = worker.get_annotated_frame()
            if frame is not None:
                ret, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    yield (b"--frame\r\n"
                           b"Content-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
            time.sleep(0.04) # ~25 FPS stream delivery

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")

@router.get("/discover")
def discover_local_cameras():
    """
    Dynamically enumerate available local webcam devices by probing indices 0-9.
    Returns a list of usable cameras with their index and display name.
    Does NOT hardcode any camera model, USB ID, or device path.
    This endpoint is portable across all developers' machines.
    """
    import cv2

    discovered = []
    for index in range(10):
        cap = cv2.VideoCapture(index)
        if cap is not None and cap.isOpened():
            ret, _ = cap.read()
            if ret:
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps = cap.get(cv2.CAP_PROP_FPS)
                discovered.append({
                    "index": index,
                    "source": str(index),
                    "source_type": "LOCAL_WEBCAM",
                    "display_name": f"Camera {index}",
                    "resolution": f"{width}x{height}",
                    "fps": round(fps, 1) if fps > 0 else None,
                    "available": True
                })
            cap.release()

    return {"cameras": discovered, "count": len(discovered)}
