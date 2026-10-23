import sys
import os
import cv2
import time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.services.universal_cctv_connector import UniversalCCTVConnector, cctv_manager
from app.services.autonomous_surveillance_pipeline import master_ai_pipeline
from app.db.session import SessionLocal
from app.models.core_models import Camera

client = TestClient(app)

def test_cctv_brand_url_builder():
    print("\n--- [TEST 1] Universal CCTV Brand RTSP URL Builder ---")
    brands = [
        ("hikvision", "192.168.1.64", 554, "admin", "Pass1234", 1, "rtsp://admin:Pass1234@192.168.1.64:554/Streaming/Channels/101"),
        ("dahua", "192.168.1.108", 554, "admin", "Admin#123", 2, "rtsp://admin:Admin#123@192.168.1.108:554/cam/realmonitor?channel=2&subtype=0"),
        ("cpplus", "10.0.0.50", 554, "admin", "CP@9988", 1, "rtsp://admin:CP@9988@10.0.0.50:554/cam/realmonitor?channel=1&subtype=0"),
        ("axis", "192.168.0.90", 554, "root", "pass", 1, "rtsp://root:pass@192.168.0.90:554/axis-media/media.amp?camera=1"),
        ("uniview", "192.168.1.120", 554, "admin", "123456", 1, "rtsp://admin:123456@192.168.1.120:554/unicast/c1/s0/live"),
        ("onvif", "192.168.1.200", 554, "admin", "admin", 1, "rtsp://admin:admin@192.168.1.200:554/onvif1"),
    ]
    
    for brand, ip, port, user, pwd, ch, expected in brands:
        url = UniversalCCTVConnector.build_rtsp_url(brand, ip, port, user, pwd, ch)
        assert url == expected, f"Failed for {brand}: expected {expected}, got {url}"
        print(f" [PASS] {brand.upper().ljust(10)} -> {url}")

def test_api_endpoints():
    print("\n--- [TEST 2] API Endpoints: URL Generator & Probe ---")
    # 1. API Generate URL
    resp = client.post("/api/v1/cameras/generate-url", json={
        "brand": "hikvision",
        "ip": "172.16.20.15",
        "port": 554,
        "username": "operator",
        "password": "SecurePassword#99",
        "channel": 3
    })
    assert resp.status_code == 200, f"API generate-url failed: {resp.text}"
    gen_url = resp.json().get("rtsp_url")
    assert "Streaming/Channels/301" in gen_url
    print(f" [PASS] POST /api/v1/cameras/generate-url -> {gen_url}")

    # 2. API Probe Stream (with invalid stream to test graceful failure without hang)
    probe_resp = client.post("/api/v1/cameras/probe", json={"source": "rtsp://192.0.2.1:554/nonexistent"})
    assert probe_resp.status_code == 200
    probe_data = probe_resp.json()
    assert probe_data["accessible"] is False
    assert "latency_ms" in probe_data
    print(f" [PASS] POST /api/v1/cameras/probe correctly timed out and returned clean diagnostic: {probe_data['error'][:60]}...")

def test_live_autonomous_cctv_worker():
    print("\n--- [TEST 3] Live CCTV Worker with Master AI Pipeline ---")
    # Register test camera in DB
    cam_id = "CAM-CCTV-TEST-01"
    with SessionLocal() as db:
        cam = db.query(Camera).filter(Camera.id == cam_id).first()
        if not cam:
            cam = Camera(id=cam_id, name="Test Border CCTV", rtsp_url="test_cctv_dummy", status="DISCONNECTED")
            db.add(cam)
            db.commit()

    # Create dummy test synthetic frame
    dummy_frame = np.ones((720, 1280, 3), dtype=np.uint8) * 40
    
    # Process through master AI pipeline
    annotated = master_ai_pipeline.process_live_cctv_frame(cam_id, dummy_frame)
    assert annotated is not None
    assert annotated.shape == (720, 1280, 3)
    print(f" [PASS] master_ai_pipeline successfully processed frame and generated HUD watermark ({annotated.shape[1]}x{annotated.shape[0]})")

def run_all():
    print("="*70)
    print("TESTING UNIVERSAL CCTV INFRASTRUCTURE INTEGRATION")
    print("="*70)
    test_cctv_brand_url_builder()
    test_api_endpoints()
    test_live_autonomous_cctv_worker()
    print("\n" + "="*70)
    print("ALL CCTV INFRASTRUCTURE ADAPTER TESTS PASSED (100% SUCCESS)")
    print("="*70 + "\n")

if __name__ == "__main__":
    run_all()
