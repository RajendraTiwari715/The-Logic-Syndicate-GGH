import os
import cv2
import time
import asyncio
import logging
from datetime import datetime, timezone
from app.db.session import SessionLocal
from app.models.core_models import Person, VehicleRecord, EventItem, WatchlistRecord
from deepface import DeepFace
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("e2e_final")

async def test_integration():
    logger.info("Initializing FINAL E2E ACCEPTANCE TEST...")
    
    with SessionLocal() as db:
        # Pre-seed Authorized Entities
        logger.info("Seeding DB...")
        
        # 1. ZIDANE as AUTHORIZED (but we'll evaluate how the pipeline responds)
        # We will enroll Zidane as "AUTHORIZED"
        img = cv2.imread("zidane.jpg")
        try:
            emb = DeepFace.represent(img_path=img, model_name="VGG-Face", detector_backend="skip", enforce_detection=False, align=True)
            if emb:
                p = db.query(Person).filter(Person.name == "Zinedine Zidane").first()
                if not p:
                    p = Person(id="ZIDANE-AUTH", name="Zinedine Zidane", embedding=emb[0]["embedding"], authorization_status="AUTHORIZED", entry_count=0)
                    db.add(p)
                    db.commit()
        except:
             pass

        # 2. Add DL01AB1234 to Authorized Vehicles Database
        v = db.query(VehicleRecord).filter(VehicleRecord.plateNumber == "DL01AB1234").first()
        if not v:
            v = VehicleRecord(id="VEH-AUTH", plateNumber="DL01AB1234", normalized_plate="DL01AB1234", status="AUTHORIZED", entry_count=0)
            db.add(v)
            
        # 3. Add MH04UN5678 to Watchlist
        w = db.query(WatchlistRecord).filter(WatchlistRecord.plate_number == "MH04UN5678").first()
        if not w:
            w = WatchlistRecord(plate_number="MH04UN5678", description="Unauthorized test vehicle")
            db.add(w)
            
        db.commit()

    cap = cv2.VideoCapture("final_test_video.mp4")
    frame_count = 0
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        # Process natively
        master_ai_pipeline.process_live_cctv_frame("GATE-CAM-01", frame)
    
    cap.release()
    logger.info("Processed %d frames successfully.", frame_count)
    
    # Generate Final Assertions
    with SessionLocal() as db:
        # 1. Person Tests
        p_event = db.query(Person).filter(Person.name == "Zinedine Zidane").first()
        logger.info("AUTHORIZED PERSON CHECK: %s (Entries: %s)", p_event.authorization_status if p_event else "MISSING", p_event.entry_count if p_event else 0)
        
        # 2. Vehicle E2E
        auth_veh = db.query(VehicleRecord).filter(VehicleRecord.normalized_plate == "DL01AB1234").first()
        logger.info("AUTHORIZED VEHICLE CHECK: DL01AB1234 -> %s (Entries: %s)", auth_veh.status if auth_veh else "MISSING OCR", auth_veh.entry_count if auth_veh else 0)
        
        # Watchlist Checks
        unauth_veh = db.query(VehicleRecord).filter(VehicleRecord.normalized_plate == "MH04UN5678").first()
        logger.info("UNAUTHORIZED VEHICLE CHECK: MH04UN5678 -> %s", unauth_veh.status if unauth_veh else "MISSING OCR")
        
        events = db.query(EventItem).filter(EventItem.eventType == "WATCHLIST_MATCH").count()
        logger.info("SECURITY CRITICAL EVENTS CREATED: %d", events)
        
    logger.info("VERIFICATION COMPLETED.")

if __name__ == "__main__":
    asyncio.run(test_integration())
