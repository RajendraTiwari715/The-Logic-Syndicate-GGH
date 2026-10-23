import time
import cv2
import logging
import asyncio

from app.db.session import engine, Base, SessionLocal
from app.models.core_models import Camera as DB_Camera, Detection, EventItem
from app.services.universal_cctv_connector import cctv_manager
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline
from app.vision.model_manager import model_manager

def main():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("e2e_test")
    
    # 1. Init DB context and YOLO singleton
    logger.info("Initializing YOLO models...")
    model_manager.get_yolo() 
    logger.info("Setting up database...")
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        # Seed test camera
        cam = db.query(DB_Camera).filter(DB_Camera.id == "CAM-LOCAL-VIDEO").first()
        if not cam:
            cam = DB_Camera(
                id="CAM-LOCAL-VIDEO", 
                name="Integration Test E2E Video",
                camera_mode="ALL",
                profile="GENERAL",
                rtsp_url="test_video.mp4",
                protocol="LOCAL_FILE",
                status="ONLINE"
            )
            db.add(cam)
            db.commit()

    logger.info("Starting Video Processing Pipeline...")
    cctv_manager.register_and_start(
        camera_id="CAM-LOCAL-VIDEO",
        source="test_video.mp4",
        name="Local Video Execution",
        ai_callback=master_ai_pipeline.process_live_cctv_frame,
    )
    
    try:
        # Let it run for 45 seconds to allow inference 
        for i in range(45):
            time.sleep(1)
            # Just keeping main thread alive while worker processes frames internally
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Stopping pipeline...")
        cctv_manager.stop_all()

    # Evaluation
    logger.info("=== TEST REPORT EVAL ===")
    with SessionLocal() as db:
        dets = db.query(Detection).all() # Note: master_ai_pipeline does not use Detection model directly, it generates Events instead inside its own loop
        events = db.query(EventItem).filter(EventItem.cameraId == "CAM-LOCAL-VIDEO").all()
        for e in events:
            logger.info(f"Generated Event: {e.eventType} - {e.description} - Tracking ID: {e.trackingId}")
        if events:
            logger.info("SUCCESS: The video source processed through the exact same real CCTV architecture safely.")
        else:
            logger.warning("FAILED: No pipeline events yielded.")

if __name__ == "__main__":
    main()
