import sys
import os
import io
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.vision.anpr import anpr_service
from app.services.anpr_pipeline import format_plate, normalize_plate

def make_plate_image_bytes(plate_text: str, is_yellow: bool = False) -> bytes:
    """Generates synthetic license plate image as JPEG bytes."""
    img = np.ones((120, 360, 3), dtype=np.uint8) * 40
    # Plate box
    bg_color = (30, 200, 230) if is_yellow else (245, 245, 245)
    cv2.rectangle(img, (15, 15), (345, 105), bg_color, -1)
    cv2.rectangle(img, (15, 15), (345, 105), (0, 0, 0), 2)
    # Blue IND strip
    cv2.rectangle(img, (15, 15), (55, 105), (200, 100, 20), -1)
    cv2.putText(img, "IND", (18, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)
    # License plate text
    cv2.putText(img, plate_text, (65, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (0, 0, 0), 2, cv2.LINE_AA)
    
    ok, encoded = cv2.imencode(".jpg", img)
    assert ok, "Failed to encode test plate image"
    return encoded.tobytes()

def test_ocr_direct_recognition():
    print("\n[TEST 1] Direct License Plate OCR Recognition...")
    plate_text = "DL 01 AB 1234"
    img_bytes = make_plate_image_bytes(plate_text)
    frame = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_COLOR)
    
    result = anpr_service.process_plate_crop(frame)
    assert result is not None, "ANPR service could not read test license plate"
    print(f"  Recognized raw: '{result.raw_text}' -> Normalized: '{result.normalized}' (Confidence: {result.confidence:.2f})")
    assert "DL01AB1234" in result.normalized or normalize_plate(result.normalized) == "DL01AB1234"

def test_anpr_api_image_upload_and_persistence():
    print("\n[TEST 2] ANPR Image Processing API (POST /api/v1/analytics/anpr/image)...")
    client = TestClient(app)
    
    target_plate = "HR 26 DQ 5566"
    img_bytes = make_plate_image_bytes(target_plate, is_yellow=True)
    
    response = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("test_car_hr.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"camera_id": "CAM-01", "direction": "Inbound"},
    )
    assert response.status_code == 200, f"Image upload failed: {response.text}"
    data = response.json()
    assert data.get("ok") is True
    assert data.get("count", 0) >= 1
    captures = data.get("captures", [])
    print(f"  Captures returned: {len(captures)}")
    first = captures[0]
    print(f"  First capture plate: {first.get('plateNumber')} | Status: {first.get('status')}")
    assert "HR26DQ5566" in normalize_plate(first.get("plateNumber", ""))
    assert first.get("image") is not None, "Capture image URL should not be null"

def test_watchlist_registration_and_critical_alert():
    print("\n[TEST 3] Watchlist Registration and Automatic Alert Triggering...")
    client = TestClient(app)
    
    wl_plate = "UP 32 AZ 9999"
    # Register plate to watchlist
    wl_res = client.post(
        "/api/v1/analytics/watchlist",
        json={"plate_number": wl_plate, "description": "High value target watchlist test"},
    )
    assert wl_res.status_code == 200
    print(f"  Registered {wl_plate} to Watchlist")
    
    # Send image with this plate
    img_bytes = make_plate_image_bytes(wl_plate)
    res = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("test_target.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"camera_id": "CAM-03", "direction": "Inbound"},
    )
    assert res.status_code == 200
    data = res.json()
    captures = data.get("captures", [])
    alerts = data.get("alerts", [])
    assert len(captures) >= 1
    assert captures[0]["status"] == "WATCHLIST", f"Expected WATCHLIST status, got {captures[0]['status']}"
    assert len(alerts) >= 1, "Alert was not triggered for watchlist plate"
    print(f"  Alert triggered successfully: {alerts[0]['title']} - Severity: {alerts[0]['severity']}")
    assert alerts[0]["severity"] == "CRITICAL"

def test_get_vehicles_api():
    print("\n[TEST 4] Querying Vehicles via GET /api/v1/analytics/vehicles...")
    client = TestClient(app)
    response = client.get("/api/v1/analytics/vehicles")
    assert response.status_code == 200
    vehicles = response.json()
    assert len(vehicles) > 0, "No vehicles returned"
    print(f"  Total vehicles in database: {len(vehicles)}")
    sample = vehicles[0]
    print(f"  Sample vehicle: Plate: {sample['plateNumber']}, Type: {sample['vehicleType']}, Cam: {sample['cameraId']}, Image: {sample['image']}")
    assert "plateNumber" in sample
    assert "status" in sample

def test_watchlist_upload_photo():
    print("\n[TEST 5] Auto-OCR Watchlist Upload via POST /api/v1/analytics/watchlist/upload...")
    client = TestClient(app)
    plate_text = "KA 05 NB 4433"
    img_bytes = make_plate_image_bytes(plate_text)
    
    res = client.post(
        "/api/v1/analytics/watchlist/upload",
        files={"file": ("test_wl_ref.jpg", io.BytesIO(img_bytes), "image/jpeg")},
    )
    assert res.status_code == 200, f"Upload failed: {res.text}"
    data = res.json()
    assert data.get("ok") is True
    print(f"  Auto-extracted plate: {data.get('plate_number')}")
    assert "KA" in data.get("plate_number")

if __name__ == "__main__":
    print("==================================================")
    print("RUNNING COMPLETE ANPR BACKEND VERIFICATION SUITE")
    print("==================================================")
    test_ocr_direct_recognition()
    test_anpr_api_image_upload_and_persistence()
    test_watchlist_registration_and_critical_alert()
    test_get_vehicles_api()
    test_watchlist_upload_photo()
    print("\n==================================================")
    print("ALL 5 END-TO-END ANPR TESTS PASSED WITH 100% SUCCESS!")
    print("==================================================")
