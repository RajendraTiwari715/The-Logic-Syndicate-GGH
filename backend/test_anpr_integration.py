import os
import time
import numpy as np
import cv2
import urllib.request
import logging
from app.db.session import SessionLocal
from app.services.identity_manager import IdentityManager
from app.vision.anpr import anpr_service
from app.models.core_models import VehicleRecord

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("anpr_test")

def main():
    logger.info("Starting Deterministic E2E ANPR Optical Character test...")
    
    # 1. Acquire Image Inline synthetically
    img_path = "test_car.png"
    # Create white synthetic rect
    img = np.ones((250, 600, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (10, 10), (590, 240), (0, 0, 0), 4)
    # Put clear thick text imitating plate
    cv2.putText(img, "MH 04 AB 1234", (40, 150), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (0, 0, 0), 8)
    cv2.imwrite(img_path, img)
            
    img = cv2.imread(img_path)
    if img is None:
        logger.error("Failed to load vehicle image.")
        return
        
    logger.info("Image loaded successfully.")
    
    # 2. Extract OCR
    plate_found = None
    try:
        plate_result = anpr_service.process_plate_crop(img)
        if plate_result and anpr_service.validate_plate(plate_result.normalized):
            plate_found = anpr_service.normalize_plate(plate_result.normalized)
            logger.info("SUCCESS: Extracted OCR Plate: %s (Raw: '%s')", plate_found, plate_result.raw_text)
        else:
            logger.error("Failed to map plate correctly.")
            return
    except Exception as e:
        logger.error(f"EasyOCR failed: {e}")
        return
        
    # 3. Simulate Pipeline Track ID
    tracking_id = "TRK-VEH-1234"
    
    with SessionLocal() as db:
        id_manager = IdentityManager(db)
        # Attempt 1: First appearance (UNKNOWN)
        v1 = id_manager.resolve_vehicle(tracking_id, plate_number=plate_found)
        logger.info("Vehicle appearance 1 -> Status: %s, Count: %d", v1.status, v1.entry_count)
        
        # Manually register the plate as AUTHORIZED
        v1.status = "AUTHORIZED"
        db.commit()
        
        # Fast forward time to bypass debounce
        v1.last_seen = v1.last_seen.replace(year=v1.last_seen.year - 1)
        db.commit()
        
        # Attempt 2: Second appearance indicating track isolation
        tracking_id_2 = "TRK-VEH-5678"
        v2 = id_manager.resolve_vehicle(tracking_id_2, plate_number=plate_found)
        logger.info("Vehicle appearance 2 -> Status: %s, Matched Plate: %s, Count: %d", v2.status, v2.plateNumber, v2.entry_count)

        if v2.status == "AUTHORIZED":
            logger.info("SUCCESS: The deterministic ANPR verification module completed securely with DB constraints.")
        else:
            logger.error("FAILED to map Identity Manager status properly.")

if __name__ == "__main__":
    main()
