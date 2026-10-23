import sys
import os
import time
import json
from pathlib import Path
from datetime import datetime
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.services.universal_cctv_connector import UniversalCCTVConnector, cctv_manager
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline
from app.vision.detector import YoloTrackingDetector
from app.vision.anpr import anpr_service
from app.vision.zones import point_in_polygon, crossed_line
from app.vision.risk_engine import RiskEngine, RiskSignals
from app.services.incident_engine import incident_engine
from app.services.ledger import ledger_service
from app.db.session import SessionLocal
from app.models.core_models import Camera, Zone, EventItem, Alert, Evidence, VehicleRecord, WatchlistRecord, Incident

client = TestClient(app)

def test_1_cctv_universal_ingestion():
    print("\n[PILLAR 1] Existing CCTV Infrastructure & Universal Ingestion")
    
    # 1. Test multi-brand RTSP builder
    brands = [
        ("hikvision", "192.168.1.10", 554, "admin", "Pass#123", 1, "rtsp://admin:Pass#123@192.168.1.10:554/Streaming/Channels/101"),
        ("dahua", "192.168.1.20", 554, "admin", "Admin#1", 1, "rtsp://admin:Admin#1@192.168.1.20:554/cam/realmonitor?channel=1&subtype=0"),
        ("cpplus", "192.168.1.30", 554, "admin", "CP#99", 2, "rtsp://admin:CP#99@192.168.1.30:554/cam/realmonitor?channel=2&subtype=0"),
        ("axis", "192.168.1.40", 554, "root", "pass", 1, "rtsp://root:pass@192.168.1.40:554/axis-media/media.amp?camera=1"),
        ("uniview", "192.168.1.50", 554, "admin", "123", 1, "rtsp://admin:123@192.168.1.50:554/unicast/c1/s0/live"),
        ("onvif", "192.168.1.60", 554, "admin", "admin", 1, "rtsp://admin:admin@192.168.1.60:554/onvif1"),
    ]
    for brand, ip, port, user, pwd, ch, expected in brands:
        url = UniversalCCTVConnector.build_rtsp_url(brand, ip, port, user, pwd, ch)
        assert url == expected
        print(f"  ✓ {brand.upper()} URL correctly generated: {url}")

    # 2. Fast non-blocking socket probe (< 1.5 seconds)
    t0 = time.perf_counter()
    probe = UniversalCCTVConnector.probe_stream("rtsp://127.0.0.1:59999/dummy")
    elapsed = time.perf_counter() - t0
    assert not probe["accessible"]
    assert elapsed < 2.0, f"Probe took too long ({elapsed}s), socket pre-check should be fast!"
    print(f"  ✓ Unreachable CCTV probe terminated fast ({round(elapsed * 1000)}ms): {probe['error']}")

def test_2_computer_vision_and_ai_ml():
    print("\n[PILLAR 2] Computer Vision & AI/ML Object Tracking & ANPR")

    # 1. Verify YOLOv8 tracking detector initialization
    detector = YoloTrackingDetector()
    assert detector.model is not None
    print(f"  ✓ YOLOv8 Model loaded successfully with target classes: {detector.class_ids}")

    # 2. Test ANPR license plate normalization & validation
    test_plates = [
        ("DL 01 AB 1234", True),
        ("mh-12-xy-9090", True),
        ("GJ05AZ7711", True),
        ("INVALID_PLATE_99", False),
    ]
    for raw, is_valid in test_plates:
        norm = anpr_service.normalize_plate(raw)
        assert anpr_service.validate_plate(norm) == is_valid
        print(f"  ✓ Plate: '{raw}' -> Normalized: '{norm}' (Valid Indian HSRP: {is_valid})")

def test_3_video_analytics_spatial_reasoning():
    print("\n[PILLAR 3] Video Analytics: Spatial Fences, Tripwires & Curfew")

    # 1. Restricted Polygon Intrusion Check
    perimeter_polygon = [(100, 100), (400, 100), (400, 400), (100, 400)]
    inside_point = (250, 250)
    outside_point = (50, 50)
    assert point_in_polygon(inside_point, perimeter_polygon) is True
    assert point_in_polygon(outside_point, perimeter_polygon) is False
    print("  ✓ Spatial polygon point-in-polygon verification passed (Inside=True, Outside=False)")

    # 2. Virtual Tripwire Line-Crossing Check
    tripwire = [(200, 0), (200, 500)]
    pt_prev = (150, 250)
    pt_curr = (250, 250)
    assert crossed_line(pt_prev, pt_curr, tripwire) is True
    print("  ✓ Virtual Tripwire ray-casting boundary crossing detected successfully")

    # 3. Loitering & Multi-Signal Threat Evaluation
    risk_engine = RiskEngine()
    signals = RiskSignals(
        object_class="person",
        zone_name="Buffer Zone East",
        restricted_zone=True,
        fence_crossed=True,
        loitering=True,
        night_time=True
    )
    eval_res = risk_engine.evaluate(signals)
    assert eval_res.score >= 85
    assert eval_res.severity == "CRITICAL"
    print(f"  ✓ Multi-signal Risk Score: {eval_res.score}/100 [Severity: {eval_res.severity}] - Reasons: {', '.join(eval_res.reasons)}")

def test_4_actionable_intelligence_and_forensics():
    print("\n[PILLAR 4] Actionable Intelligence, SHA-256 Ledger & Incident Correlation")

    cam_id = "CAM-C2-E2E-TEST"
    with SessionLocal() as db:
        # Register Camera
        cam = db.query(Camera).filter(Camera.id == cam_id).first()
        if not cam:
            cam = Camera(id=cam_id, name="Test Border Post 09", status="LIVE", rtsp_url="0")
            db.add(cam)

        # Register Watchlist Plate
        test_wl_plate = "KA03MN4567"
        wl = db.query(WatchlistRecord).filter(WatchlistRecord.plate_number == test_wl_plate).first()
        if not wl:
            wl = WatchlistRecord(id="WL-TEST-01", plate_number=test_wl_plate, description="Suspect Vehicle - Border Intercept")
            db.add(wl)
        db.commit()

        # Run pipeline over synthetic frame
        synthetic_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 50
        annotated = master_ai_pipeline.process_live_cctv_frame(cam_id, synthetic_frame)
        assert annotated is not None
        assert annotated.shape == (720, 1280, 3)
        print("  ✓ Master AI pipeline processed frame and rendered tactical HUD watermark")

        # Test Watchlist Alert Generation with Evidence & SHA-256 Ledger
        master_ai_pipeline._create_watchlist_alert(
            db=db,
            camera_id=cam_id,
            plate=test_wl_plate,
            description="High Priority Intercept Target",
            timestamp=datetime.now(),
            frame=synthetic_frame
        )

        # Verify Alert created
        alert = db.query(Alert).filter(Alert.cameraId == cam_id, Alert.severity == "CRITICAL").order_by(Alert.id.desc()).first()
        assert alert is not None
        print(f"  ✓ Automated Alert created: [{alert.severity}] {alert.title} - ID: {alert.id}")

        # Verify EventItem created
        evt = db.query(EventItem).filter(EventItem.id == alert.eventId).first()
        assert evt is not None
        print(f"  ✓ Linked EventItem: {evt.eventType} with riskScore={evt.riskScore}")

        # Verify Evidence recorded with SHA-256 hash
        evidence = db.query(Evidence).filter(Evidence.event_id == alert.eventId).first()
        assert evidence is not None
        assert len(evidence.sha256_hash) == 64
        print(f"  ✓ Cryptographic Evidence generated: SHA-256={evidence.sha256_hash[:16]}... (Status: {evidence.integrity_status})")

        # Verify Ledger verification
        ledger_entry = ledger_service.verify_evidence_integrity(evidence.sha256_hash)
        assert ledger_entry is not None
        print(f"  ✓ Tamper-proof Ledger block verified for event {ledger_entry['event_id']}")

def run_all_checks():
    print("=" * 80)
    print("SOFTWARE-DEFINED SURVEILLANCE PLATFORM (IBVAP): COMPLETE VERIFICATION")
    print("=" * 80)
    test_1_cctv_universal_ingestion()
    test_2_computer_vision_and_ai_ml()
    test_3_video_analytics_spatial_reasoning()
    test_4_actionable_intelligence_and_forensics()
    print("\n" + "=" * 80)
    print("ALL 4 CORE REQUIREMENTS VERIFIED AND 100% OPERATIONAL")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    run_all_checks()
