import logging
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api.routers import auth, users, stream, cameras, alerts, zones, analytics
from app.core.config import settings
from app.ws_manager import manager
from app.db.session import engine, Base, SessionLocal
from app.core.redis_client import redis_client
from app.core.storage import storage_client
from app.services.anpr_pipeline import DATA_DIR, decode_base64_frame, process_anpr_frame
from app.db.session import get_db
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

class CleanLogsFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if "Using CPU" in msg or "faster with a GPU" in msg:
            return False
        return True

from sqlalchemy import text
from fastapi.responses import JSONResponse

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_obj = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "service": "ibvap-backend",
            "message": record.getMessage(),
        }
        if hasattr(record, "camera_id"):
            log_obj["camera_id"] = record.camera_id
        if hasattr(record, "event_id"):
            log_obj["event_id"] = record.event_id
        if hasattr(record, "latency"):
            log_obj["latency"] = record.latency
        return json.dumps(log_obj)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
filter_obj = CleanLogsFilter()
handler.addFilter(filter_obj)
logger.handlers.clear()
logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Suppress EasyOCR root level logs explicitly
easyocr_logger = logging.getLogger("easyocr")
easyocr_logger.addFilter(filter_obj)
for h in easyocr_logger.handlers:
    h.addFilter(filter_obj)

# Start connections
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting IBVAP Backend")
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Database auto-initialization skipped: %s", exc)
    redis_client.connect()
    storage_client.connect()
    # Warmup YOLO singleton model to prevent lazy load stutter
    try:
        from app.vision.model_manager import model_manager
        model_manager.get_yolo()
    except Exception as exc:
        logger.warning("YOLO warmup notice: %s", exc)

    # Automatically connect all registered CCTV infrastructure streams
    try:
        from app.models.core_models import Camera as DB_Camera
        from app.services.universal_cctv_connector import cctv_manager
        from app.services.autonomous_surveillance_pipeline import master_ai_pipeline

        with SessionLocal() as db:
            active_cams = db.query(DB_Camera).all()
            for cam in active_cams:
                source = cam.rtsp_url if cam.rtsp_url else None
                if source and source != "test_video.mp4":
                    logger.info("Auto-starting CCTV AI stream for %s (%s)", cam.id, source)
                    cctv_manager.register_and_start(
                        camera_id=cam.id,
                        source=source,
                        name=cam.name or cam.id,
                        ai_callback=master_ai_pipeline.process_live_cctv_frame,
                    )
    except Exception as exc:
        logger.warning("CCTV Auto-bootstrap notice: %s", exc)

    yield
    # Shutdown
    logger.info("Shutting down IBVAP Backend and CCTV Workers")
    try:
        from app.services.universal_cctv_connector import cctv_manager
        cctv_manager.stop_all()
    except Exception:
        pass
    try:
        from app.core.worker_pool import worker_pool
        worker_pool.shutdown_all()
    except Exception:
        pass

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["auth"])
app.include_router(users.router, prefix=f"{settings.API_V1_STR}/users", tags=["users"])
app.include_router(stream.router, prefix=f"{settings.API_V1_STR}/stream", tags=["stream"])
app.include_router(cameras.router, prefix=f"{settings.API_V1_STR}/cameras", tags=["cameras"])
app.include_router(alerts.router, prefix=f"{settings.API_V1_STR}/alerts", tags=["alerts"])
app.include_router(zones.router, prefix=f"{settings.API_V1_STR}/zones", tags=["zones"])
app.include_router(analytics.router, prefix=f"{settings.API_V1_STR}/analytics", tags=["analytics"])
app.mount("/media", StaticFiles(directory=str(DATA_DIR)), name="media")

@app.get("/")
def read_root():
    return {"message": "Welcome to IBVAP AI Backend"}

@app.get("/health")
def healthcheck(db=Depends(get_db)):
    health_status = {
        "status": "ok",
        "service": "ibvap-backend",
        "components": {
            "database": "unhealthy",
            "redis": "unhealthy",
            "minio": "unhealthy",
            "ai_models": "unhealthy"
        }
    }
    
    # Check DB
    try:
        db.execute(text("SELECT 1"))
        health_status["components"]["database"] = "healthy"
    except Exception:
        health_status["status"] = "degraded"

    # Check Redis
    try:
        if redis_client.redis and redis_client.redis.ping():
            health_status["components"]["redis"] = "healthy"
        else:
            health_status["status"] = "degraded"
    except Exception:
        health_status["status"] = "degraded"
        
    # Check Storage
    try:
        if storage_client.is_healthy():
            health_status["components"]["minio"] = "healthy"
        else:
            health_status["status"] = "degraded"
    except Exception:
        health_status["status"] = "degraded"

    # Check AI Models
    try:
        from app.vision.model_manager import model_manager
        health_status["components"]["ai_models"] = "healthy"
    except Exception:
        health_status["components"]["ai_models"] = "fallback_ready"
        
    return JSONResponse(
        status_code=200 if health_status["status"] == "ok" else 503,
        content=health_status
    )

@app.get("/liveness")
def liveness():
    return {"status": "alive"}

@app.get("/readiness")
def readiness(db=Depends(get_db)):
    health = healthcheck(db).body.decode("utf-8")
    status = json.loads(health).get("status")
    return {"status": "ready" if status == "ok" else "not_ready"}

@app.websocket("/ws/detections")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON payload"})
                continue

            if payload.get("type") != "frame":
                continue

            camera_id = payload.get("camera_id") or payload.get("cameraId") or "ANPR-LIVE"
            direction = payload.get("direction") or "Live"
            image_data = payload.get("image") or payload.get("frame") or ""
            if not image_data:
                await websocket.send_json({"type": "error", "message": "Missing frame image"})
                continue

            try:
                frame = decode_base64_frame(image_data)
            except ValueError as exc:
                await websocket.send_json({"type": "error", "message": str(exc)})
                continue

            # Delegate inline blocking logic directly into the back-pressured multi-threading worker pipeline
            # Delegate inline blocking logic directly into the back-pressured multi-threading worker pipeline
            from app.core.worker_pool import worker_pool
            zones = payload.get("zones", [])
            force_watchlist = payload.get("force_watchlist", False)
            force_reid = payload.get("force_reid", False)
            camera_mode = payload.get("camera_mode", "ALL")
            context = {"zones": zones, "force_watchlist": force_watchlist, "force_reid": force_reid, "camera_mode": camera_mode}
            success = worker_pool.enqueue(camera_id, frame, context)
            if not success:
                # Frame dropped purposefully under severe backpressure -> Protect system stability.
                logger.warning(f"WebSocket input dropped for {camera_id}: CameraWorker Queue full.")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
