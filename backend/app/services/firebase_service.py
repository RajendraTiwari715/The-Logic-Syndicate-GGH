import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

# Mock implementation since we don't have the firebase_credentials.json

def upload_frame_to_storage(frame_bytes, camera_id):
    """
    Mock uploading a frame to Firebase Cloud Storage.
    Returns a fake public URL.
    """
    logger.info(f"Mock Uploading frame for camera {camera_id} to Cloud Storage...")
    file_id = str(uuid.uuid4())
    # In a real scenario, this would use firebase_admin.storage.bucket().blob().upload_from_string()
    mock_url = f"https://firebasestorage.googleapis.com/v0/b/mock-ibvap.appspot.com/o/alerts%2F{file_id}.jpg?alt=media"
    return mock_url

def save_alert_to_firestore(camera_id, alert_type, metadata, image_url):
    """
    Mock saving an alert document to Firebase Firestore.
    """
    logger.info(f"Mock Saving alert {alert_type} for camera {camera_id} to Firestore...")
    alert_doc = {
        "id": str(uuid.uuid4()),
        "camera_id": camera_id,
        "type": alert_type,
        "metadata": metadata,
        "image_url": image_url,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
    # In a real scenario, this would use firebase_admin.firestore.client().collection('alerts').add(alert_doc)
    logger.info(f"Firestore document saved: {alert_doc}")
    return alert_doc
