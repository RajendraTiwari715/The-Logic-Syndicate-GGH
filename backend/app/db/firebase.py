import firebase_admin
from firebase_admin import credentials, firestore
import os

CREDENTIAL_PATH = os.getenv("FIREBASE_CREDENTIALS", "serviceAccountKey.json")

def init_firebase():
    if not firebase_admin._apps:
        try:
            if os.path.exists(CREDENTIAL_PATH):
                cred = credentials.Certificate(CREDENTIAL_PATH)
                firebase_admin.initialize_app(cred)
                print("Firebase Initialized Successfully.")
            else:
                print(f"Firebase Credentials not found at {CREDENTIAL_PATH}. Skipping initialization.")
        except Exception as e:
            print(f"Firebase Initialization Error: {e}")

def get_db():
    try:
        if firebase_admin._apps:
            return firestore.client()
    except Exception:
        pass
    return None
