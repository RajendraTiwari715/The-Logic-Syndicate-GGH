import sys
import os
import hashlib
import uuid
from datetime import datetime, timedelta
import cv2
import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.core_models import Camera, WatchlistRecord, VehicleRecord, EventItem, Evidence, Plate, Alert
from app.core import security
from app.services.anpr_pipeline import ANPR_DIR, format_plate, normalize_plate

def generate_sample_plate_image(plate_text: str, is_yellow: bool = False) -> tuple[str, str, str]:
    """Generates a realistic synthetic license plate image and saves it to data/anpr."""
    today_str = datetime.utcnow().strftime("%Y%m%d")
    target_dir = ANPR_DIR / today_str
    target_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"{datetime.utcnow().strftime('%H%M%S_%f')}_{normalize_plate(plate_text)}.jpg"
    filepath = target_dir / filename
    
    # Generate vehicle front crop with plate
    img = np.ones((240, 420, 3), dtype=np.uint8) * 35 # dark vehicle grill
    cv2.rectangle(img, (20, 20), (400, 220), (50, 50, 50), -1)
    
    # Plate background
    plate_bg = (30, 200, 230) if is_yellow else (240, 240, 240)
    cv2.rectangle(img, (70, 110), (350, 185), plate_bg, -1)
    cv2.rectangle(img, (70, 110), (350, 185), (0, 0, 0), 3)
    
    # IND badge
    cv2.rectangle(img, (70, 110), (105, 185), (200, 100, 20), -1)
    cv2.putText(img, "IND", (74, 155), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Plate number
    cv2.putText(img, plate_text, (115, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 0, 0), 2, cv2.LINE_AA)
    
    cv2.imwrite(str(filepath), img)
    digest = hashlib.sha256(filepath.read_bytes()).hexdigest()
    rel_url = f"/media/anpr/{today_str}/{filename}"
    return str(filepath), rel_url, digest

def init_db():
    print("--- INITIALIZING IBVAP DATABASE & SEED DATA ---")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 1. Admin User
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        hashed_password = security.get_password_hash("admin123")
        admin = User(
            username="admin",
            hashed_password=hashed_password,
            role_name=UserRole.ADMIN,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("[+] Created default admin user: admin / admin123")
    else:
        print("[.] Admin user already exists")

    # 2. Cameras
    default_cameras = [
        {"id": "CAM-01", "name": "Main Gate", "bop": "Command", "location": "North Entrance", "status": "ONLINE", "scenario": "normal"},
        {"id": "CAM-02", "name": "Perimeter West", "bop": "Command", "location": "West Wall", "status": "ONLINE", "scenario": "normal"},
        {"id": "CAM-03", "name": "Sector Alpha", "bop": "Alpha", "location": "Watchtower 1", "status": "ONLINE", "scenario": "normal"},
        {"id": "CAM-04", "name": "Sector Bravo", "bop": "Bravo", "location": "Checkpoint 2", "status": "ONLINE", "scenario": "anpr"},
        {"id": "ANPR-01", "name": "Checkpoint Alpha ANPR", "bop": "Sector B", "location": "Sector B Main Road", "status": "ONLINE", "scenario": "anpr"},
    ]
    for c_data in default_cameras:
        cam = db.query(Camera).filter(Camera.id == c_data["id"]).first()
        if not cam:
            db.add(Camera(
                id=c_data["id"],
                name=c_data["name"],
                bop=c_data["bop"],
                location=c_data["location"],
                status=c_data["status"],
                scenario=c_data["scenario"],
                fps=30,
                latency=35,
                storage=120,
                health=98,
                lastHeartbeat=datetime.utcnow().isoformat() + "Z",
                signalQuality=95,
                recording=True,
                detectionCount=120,
                coords={"x": 50, "y": 50},
                mapCoord={"lat": 26.85, "lng": 80.94},
            ))
            print(f"[+] Added camera {c_data['id']}")
    db.commit()

    # 3. Watchlist Records
    default_watchlist = [
        ("MH 12 XY 9090", "Suspected cross-border narcotics / contraband transport"),
        ("DL 1C AB 1234", "Flagged for stolen vehicle alert by state police"),
    ]
    for plate_str, reason in default_watchlist:
        formatted = format_plate(plate_str)
        existing = db.query(WatchlistRecord).filter(WatchlistRecord.plate_number == formatted).first()
        if not existing:
            db.add(WatchlistRecord(plate_number=formatted, description=reason))
            print(f"[+] Added watchlist plate: {formatted}")
    db.commit()

    # 4. Initial Vehicle Records with Real Snapshots
    sample_vehicles = [
        ("DL 4C AB 1234", "Car", "CAM-01", "AUTHORIZED", "Inbound", 96, 5, False),
        ("HR 26 DQ 5566", "Truck", "CAM-01", "UNKNOWN", "Outbound", 92, 15, True),
        ("MH 12 XY 9090", "Car", "CAM-03", "WATCHLIST", "Inbound", 95, 45, True),
        ("UP 16 BD 4321", "Motorcycle", "CAM-02", "UNKNOWN", "Cross-Border", 88, 60, False),
        ("DL 8C LM 7788", "Van", "CAM-01", "AUTHORIZED", "Outbound", 94, 120, False),
    ]

    existing_count = db.query(VehicleRecord).count()
    if existing_count == 0:
        print("[+] Seeding sample ANPR vehicle captures with generated images...")
        for plate_str, v_type, cam_id, status, direction, conf, min_ago, is_yellow in sample_vehicles:
            dt = datetime.utcnow() - timedelta(minutes=min_ago)
            ts_iso = dt.isoformat() + "Z"
            v_id = f"V-{uuid.uuid4().hex[:10].upper()}"
            evt_id = f"EVT-{uuid.uuid4().hex[:10].upper()}"
            
            fpath, furl, fdigest = generate_sample_plate_image(plate_str, is_yellow=is_yellow)
            
            veh = VehicleRecord(
                id=v_id,
                cameraId=cam_id,
                vehicleType=v_type,
                plateNumber=format_plate(plate_str),
                confidence=conf,
                timestamp=ts_iso,
                status=status,
                direction=direction,
            )
            db.add(veh)
            
            evidence = Evidence(
                id=str(uuid.uuid4()),
                event_id=evt_id,
                camera_id=cam_id,
                file_location=fpath,
                file_url=furl,
                file_type="SNAPSHOT",
                sha256_hash=fdigest,
                integrity_status="VERIFIED",
            )
            db.add(evidence)
            
            plate_rec = Plate(
                id=str(uuid.uuid4()),
                vehicle_id=v_id,
                camera_id=cam_id,
                raw_ocr_text=plate_str,
                normalized_plate=normalize_plate(plate_str),
                confidence=conf / 100.0,
                timestamp=dt,
                evidence_id=evidence.id,
            )
            db.add(plate_rec)
            
            event = EventItem(
                id=evt_id,
                cameraId=cam_id,
                eventType="WATCHLIST_MATCH" if status == "WATCHLIST" else "PLATE_DETECTED",
                severity="CRITICAL" if status == "WATCHLIST" else "LOW",
                trackingId=v_id,
                description=f"Vehicle plate {format_plate(plate_str)} detected at {cam_id}",
                timestamp=ts_iso,
                status="NEW",
                riskScore=95 if status == "WATCHLIST" else 15,
                reasons=[f"Plate OCR confidence {conf}%", f"Vehicle type: {v_type}"],
                confidence=float(conf),
                details={"plate_number": format_plate(plate_str), "image_url": furl},
            )
            db.add(event)
            
            if status == "WATCHLIST":
                alert = Alert(
                    id=f"ALRT-{uuid.uuid4().hex[:8].upper()}",
                    eventId=evt_id,
                    severity="CRITICAL",
                    riskScore=95,
                    reason=f"Vehicle plate {format_plate(plate_str)} matches watchlist.",
                    status="NEW",
                    createdAt=ts_iso,
                    cameraId=cam_id,
                    trackingId=v_id,
                    title="Watchlist Vehicle Detected",
                    what=f"{v_type} with plate {format_plate(plate_str)}",
                    where=cam_id,
                    when_time=dt.strftime("%d %b %Y, %I:%M:%S %p"),
                    object=format_plate(plate_str),
                    confidence=conf,
                )
                db.add(alert)
        
        db.commit()
        print("[+] Seeded 5 initial vehicles with snapshots.")

    db.close()
    print("--- DATABASE INITIALIZATION COMPLETE ---")

if __name__ == "__main__":
    init_db()
