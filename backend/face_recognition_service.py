import os
import time
import cv2
import uuid
import threading
import face_recognition
import numpy as np
import firebase_admin
from firebase_admin import credentials, firestore, storage
from datetime import datetime

# =======================================================
# CONFIGURATION
# =======================================================
RTSP_URL = 0 # Use 0 for webcam, or "rtsp://..." for CCTV
KNOWN_FACES_DIR = "known_faces"
COOLDOWN_SECONDS = 120 # 2 minutes cooldown timer for known faces
CAMERA_ID = "CAM-TRACK-01"

# =======================================================
# FIREBASE SETUP
# =======================================================
SERVICE_ACCOUNT_FILE = "serviceAccountKey.json"

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'your-storage-bucket.appspot.com' 
    })
    db = firestore.client()
    bucket = storage.bucket()
    print("[INFO] Firebase initialized successfully.")
    FIREBASE_ENABLED = True
except Exception as e:
    print(f"[WARNING] Firebase initialization failed. Logs will not be sent to Firestore. Ensure '{SERVICE_ACCOUNT_FILE}' exists.")
    print(f"Error: {e}")
    FIREBASE_ENABLED = False

# =======================================================
# LOAD KNOWN FACES
# =======================================================
known_face_encodings = []
known_face_names = []

if not os.path.exists(KNOWN_FACES_DIR):
    os.makedirs(KNOWN_FACES_DIR)
    print(f"[INFO] Created '{KNOWN_FACES_DIR}' directory. Add images here.")

print("[INFO] Loading known faces...")
for filename in os.listdir(KNOWN_FACES_DIR):
    if filename.endswith((".jpg", ".jpeg", ".png")):
        path = os.path.join(KNOWN_FACES_DIR, filename)
        name = os.path.splitext(filename)[0]
        try:
            image = face_recognition.load_image_file(path)
            encodings = face_recognition.face_encodings(image)
            if encodings:
                known_face_encodings.append(encodings[0])
                known_face_names.append(name)
                print(f"[INFO] Loaded known face: {name}")
            else:
                print(f"[WARNING] No face found in {filename}")
        except Exception as e:
            print(f"[ERROR] Could not process {filename}: {e}")

# Track last seen times for cooldown
last_seen = {}

# Thread lock for known faces to prevent race conditions during updates
known_faces_lock = threading.Lock()

# =======================================================
# BACKGROUND DB TASKS
# =======================================================
def save_to_db_background(name, is_new, image_data):
    """
    Saves image to storage and logs to DB asynchronously.
    image_data is the numpy array of the cropped face.
    """
    if not FIREBASE_ENABLED:
        return

    temp_filename = f"temp_{uuid.uuid4().hex}.jpg"
    cv2.imwrite(temp_filename, image_data)

    try:
        # 1. Upload image to Storage
        storage_path = f"face_logs/{temp_filename}"
        blob = bucket.blob(storage_path)
        blob.upload_from_filename(temp_filename)
        blob.make_public()
        image_url = blob.public_url

        # 2. Log to Firestore
        doc_ref = db.collection('face_logs').document()
        doc_ref.set({
            'name': name,
            'status': 'Unknown' if is_new else 'Known',
            'cameraId': CAMERA_ID,
            'timestamp': firestore.SERVER_TIMESTAMP,
            'imageUrl': image_url,
            'isNewPerson': is_new
        })
        print(f"[INFO] Background Task: Successfully Logged {name} to Firebase.")
    except Exception as e:
        print(f"[ERROR] Background Task: Failed to upload to Firebase: {e}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# =======================================================
# MAIN VIDEO LOOP
# =======================================================
def process_video():
    print(f"[INFO] Starting video stream: {RTSP_URL}")
    video_capture = cv2.VideoCapture(RTSP_URL)

    if not video_capture.isOpened():
        print("[ERROR] Cannot open video stream.")
        return

    process_this_frame = True
    face_locations = []
    face_names = []

    while True:
        ret, frame = video_capture.read()
        if not ret:
            print("[WARNING] Frame capture failed. Retrying...")
            time.sleep(1)
            continue

        # Resize frame for faster processing
        small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        rgb_small_frame = np.ascontiguousarray(small_frame[:, :, ::-1])

        if process_this_frame:
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)

            current_frame_names = []
            
            with known_faces_lock:
                for face_encoding, face_location in zip(face_encodings, face_locations):
                    name = "Unknown"
                    is_new = False
                    
                    if len(known_face_encodings) > 0:
                        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.5)
                        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
                        if len(face_distances) > 0:
                            best_match_index = np.argmin(face_distances)
                            if matches[best_match_index]:
                                name = known_face_names[best_match_index]

                    # If the person is completely new
                    if name == "Unknown":
                        is_new = True
                        name = f"Person_{uuid.uuid4().hex[:6]}"
                        # Instantly add to known faces so next frame recognizes them
                        known_face_encodings.append(face_encoding)
                        known_face_names.append(name)
                        print(f"[DETECT] NEW Person Registered: {name}")

                    current_frame_names.append(name)
                    
                    now = time.time()
                    last_time = last_seen.get(name, 0)
                    
                    # Cooldown logic: Log if new OR if 5 minutes have passed
                    if is_new or (now - last_time > COOLDOWN_SECONDS):
                        last_seen[name] = now
                        if not is_new:
                            print(f"[DETECT] {name} seen again after 5min cooldown.")
                        
                        # Extract face for uploading
                        top, right, bottom, left = face_location
                        top *= 4; right *= 4; bottom *= 4; left *= 4
                        
                        h, w, _ = frame.shape
                        pad = 30
                        crop_top = max(0, top - pad)
                        crop_bottom = min(h, bottom + pad)
                        crop_left = max(0, left - pad)
                        crop_right = min(w, right + pad)
                        
                        face_image = frame[crop_top:crop_bottom, crop_left:crop_right].copy()
                        
                        # Trigger Non-Blocking Background Thread for DB/Storage Operations
                        threading.Thread(target=save_to_db_background, args=(name, is_new, face_image), daemon=True).start()
            
            face_names = current_frame_names

        process_this_frame = not process_this_frame

        # Display the results smoothly without freezing
        for (top, right, bottom, left), name in zip(face_locations, face_names):
            top *= 4; right *= 4; bottom *= 4; left *= 4
            # Red box for newly identified Unknowns, Green for knowns
            color = (0, 0, 255) if "Person_" in name else (0, 255, 0)
            
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.rectangle(frame, (left, bottom - 35), (right, bottom), color, cv2.FILLED)
            font = cv2.FONT_HERSHEY_DUPLEX
            cv2.putText(frame, name, (left + 6, bottom - 6), font, 0.7, (255, 255, 255), 1)

        cv2.imshow('Video', frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    video_capture.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    process_video()
