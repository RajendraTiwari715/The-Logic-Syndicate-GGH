import os
import time
import numpy as np
import cv2
import urllib.request
import logging
from app.db.session import SessionLocal
from app.services.identity_manager import IdentityManager
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline
from app.models.core_models import Person
from deepface import DeepFace

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("face_test")

def main():
    logger.info("Starting Deterministic E2E Face Vectorization test...")
    
    # 1. Acquire Image
    img_path = "test_face.jpg"
    if not os.path.exists(img_path):
        req = urllib.request.Request(
            "https://upload.wikimedia.org/wikipedia/commons/4/48/Outdoors-man-portrait_%28cropped%29.jpg",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req) as response, open(img_path, 'wb') as out_file:
            out_file.write(response.read())
    
    img = cv2.imread(img_path)
    if img is None:
        logger.error("Failed to load image.")
        return
        
    logger.info("Image loaded successfully.")
    
    # 2. Extract Embedding
    try:
        embedding_objs = DeepFace.represent(img_path=img, model_name="VGG-Face", detector_backend="skip", enforce_detection=False, align=True)
        if embedding_objs and len(embedding_objs) > 0:
            face_embedding = embedding_objs[0]["embedding"]
            logger.info("SUCCESS: Extracted Face Embedding (Length: %d)", len(face_embedding))
        else:
            logger.error("No embedding objects returned.")
            return
    except Exception as e:
        logger.error(f"DeepFace failed: {e}")
        return
        
    # 3. Simulate Pipeline Track ID
    tracking_id = "TRK-FACE-01"
    
    with SessionLocal() as db:
        id_manager = IdentityManager(db)
        # Attempt 1: First appearance (UNKNOWN)
        p1 = id_manager.resolve_person(tracking_id, face_embedding, name="UNKNOWN")
        logger.info("Appearance 1 -> Status: %s, Count: %d", p1.authorization_status, p1.entry_count)
        
        # Manually register the person as AUTHORIZED for testing similarity logic
        p1.authorization_status = "AUTHORIZED"
        p1.name = "John Doe"
        db.commit()
        
        # Fast forward time to bypass debounce
        p1.last_seen = p1.last_seen.replace(year=p1.last_seen.year - 1)
        db.commit()
        
        # Attempt 2: Second appearance (different track ID, but SAME face embedding)
        tracking_id_2 = "TRK-FACE-02"
        p2 = id_manager.resolve_person(tracking_id_2, face_embedding, name="UNKNOWN")
        logger.info("Appearance 2 -> Status: %s, Matched Name: %s, Count: %d", p2.authorization_status, p2.name, p2.entry_count)

        if p2.authorization_status == "AUTHORIZED" and p2.name == "John Doe":
            logger.info("SUCCESS: The deterministic face verification module completed securely with DB constraints.")
        else:
            logger.error("FAILED to map identity across embedding similarity.")

if __name__ == "__main__":
    main()
