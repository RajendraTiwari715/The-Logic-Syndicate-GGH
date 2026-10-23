import sys
import os
import uuid
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.core_models import (
    Camera, CameraStatus,
    Zone, EventItem, EventType,
    Alert, AlertState, Severity,
    Incident, Evidence, AuditLog,
    Plate, Watchlist
)

def verify_db():
    print("Connecting to DB...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # User
        print("Testing User...")
        user = User(username=f"test_user_{uuid.uuid4().hex[:8]}", hashed_password="pw", role_name=UserRole.OPERATOR)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Camera
        print("Testing Camera...")
        camera = Camera(name="Test Cam", location="Test Loc", rtsp_url="rtsp://test", status=CameraStatus.LIVE)
        db.add(camera)
        db.commit()
        db.refresh(camera)

        # Zone
        print("Testing Zone...")
        zone = Zone(name="Test Zone", zoneType="RESTRICTED", cameraId=camera.id, coordinates=[{"x":0,"y":0}, {"x":1,"y":1}])
        db.add(zone)
        db.commit()
        db.refresh(zone)

        # Event
        print("Testing Event...")
        event = EventItem(eventType=EventType.RESTRICTED_ZONE_INTRUSION, cameraId=camera.id, riskScore=80)
        db.add(event)
        db.commit()
        db.refresh(event)

        # Alert
        print("Testing Alert...")
        alert = Alert(eventId=event.id, severity=Severity.CRITICAL, status=AlertState.NEW, reason="Test Alert")
        db.add(alert)
        db.commit()
        db.refresh(alert)

        # Incident
        print("Testing Incident...")
        incident = Incident(title="Test Incident")
        db.add(incident)
        db.commit()
        db.refresh(incident)

        # Evidence
        print("Testing Evidence...")
        evidence = Evidence(event_id=event.id, file_type="IMAGE", file_location="/test", sha256_hash="hash")
        db.add(evidence)
        db.commit()
        db.refresh(evidence)

        # Audit Log
        print("Testing Audit Log...")
        audit = AuditLog(user=user.id, action="TEST_ACTION", details="Test")
        db.add(audit)
        db.commit()
        db.refresh(audit)

        # Plate
        print("Testing Plate...")
        plate = Plate(raw_ocr_text="TEST999", camera_id=camera.id, confidence=0.99)
        db.add(plate)
        db.commit()
        db.refresh(plate)

        # Watchlist
        print("Testing Watchlist...")
        watchlist = Watchlist(name="BAD999", type="VEHICLE")
        db.add(watchlist)
        db.commit()
        db.refresh(watchlist)
        
        print("ALL DATABASE INSERT TESTS SUCCESSFUL.")
    except Exception as e:
        print(f"FAILED: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    verify_db()
