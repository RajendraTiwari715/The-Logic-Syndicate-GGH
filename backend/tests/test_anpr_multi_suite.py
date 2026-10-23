import sys
import os
import io
import time
import hashlib
import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app
from app.vision.anpr import anpr_service, ANPRService
from app.services.anpr_pipeline import format_plate, normalize_plate

client = TestClient(app)

def create_plate_image(
    plate_text: str,
    is_yellow: bool = False,
    brightness: float = 1.0,
    blur: int = 0,
    tilt_angle: float = 0.0,
    noise_sigma: float = 0.0
) -> np.ndarray:
    """Generates synthetic license plate with configurable visual augmentations."""
    w, h = 340, 110
    img = np.ones((h, w, 3), dtype=np.uint8) * 45
    bg_color = (30, 200, 230) if is_yellow else (245, 245, 245)
    
    # Outer border and plate background
    cv2.rectangle(img, (10, 10), (w - 10, h - 10), bg_color, -1)
    cv2.rectangle(img, (10, 10), (w - 10, h - 10), (10, 10, 10), 2)
    
    # Blue IND badge
    cv2.rectangle(img, (10, 10), (50, h - 10), (190, 90, 20), -1)
    cv2.putText(img, "IND", (14, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Plate Text
    cv2.putText(img, plate_text, (60, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.88, (10, 10, 10), 2, cv2.LINE_AA)
    
    # Apply brightness/contrast
    if brightness != 1.0:
        img = np.clip(img * brightness, 0, 255).astype(np.uint8)
        
    # Apply blur
    if blur > 0:
        k = blur if blur % 2 != 0 else blur + 1
        img = cv2.GaussianBlur(img, (k, k), 0)
        
    # Apply noise
    if noise_sigma > 0:
        noise = np.random.normal(0, noise_sigma, img.shape).astype(np.float32)
        img = np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)
        
    # Apply perspective/tilt
    if tilt_angle != 0.0:
        center = (w // 2, h // 2)
        rot_mat = cv2.getRotationMatrix2D(center, tilt_angle, 1.0)
        img = cv2.warpAffine(img, rot_mat, (w, h), borderValue=(45, 45, 45))
        
    return img

def img_to_bytes(img: np.ndarray, ext: str = ".jpg") -> bytes:
    ok, buf = cv2.imencode(ext, img)
    assert ok, "Image encoding failed"
    return buf.tobytes()

def make_video_file_bytes(plates: list[str], frames_per_plate: int = 15) -> bytes:
    """Creates an in-memory MP4 video containing plates sequentially."""
    import tempfile
    temp_path = os.path.join(tempfile.gettempdir(), f"anpr_test_video_{int(time.time()*1000)}.mp4")
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(temp_path, fourcc, 15, (640, 360))
    
    for plate in plates:
        plate_crop = create_plate_image(plate, is_yellow="HR" in plate)
        # Place plate inside a 640x360 simulated road frame
        road_frame = np.ones((360, 640, 3), dtype=np.uint8) * 80
        # draw road lines
        cv2.line(road_frame, (0, 280), (640, 280), (200, 200, 200), 2)
        # place vehicle crop with plate
        ph, pw = plate_crop.shape[:2]
        road_frame[150:150+ph, 150:150+pw] = plate_crop
        for _ in range(frames_per_plate):
            out.write(road_frame)
            
    out.release()
    with open(temp_path, "rb") as f:
        data = f.read()
    try:
        os.remove(temp_path)
    except:
        pass
    return data

def run_suite():
    passed = 0
    total = 0
    results = []

    def record_test(name: str, success: bool, detail: str = ""):
        nonlocal passed, total
        total += 1
        if success:
            passed += 1
            status_str = "PASS"
        else:
            status_str = "FAIL"
        results.append((name, status_str, detail))
        print(f"[{status_str}] {name}: {detail}")

    print("=================================================================")
    print("STARTING EXTENSIVE MULTI-TEST SUITE FOR ANPR ENGINE")
    print("=================================================================\n")

    # -------------------------------------------------------------
    # Category 1: Diverse Indian State Formats
    # -------------------------------------------------------------
    print("--- [CATEGORY 1] Various Indian License Plate Formats ---")
    plate_cases = [
        ("Delhi Private White", "DL 01 AB 1234", False),
        ("Haryana Commercial Yellow", "HR 26 DQ 5566", True),
        ("Maharashtra HSRP", "MH 12 XY 9090", False),
        ("Karnataka Private", "KA 05 NB 4433", False),
        ("Uttar Pradesh Private", "UP 16 BD 4321", False),
        ("Gujarat Commercial", "GJ 01 CW 8899", True),
    ]

    for label, text, is_yellow in plate_cases:
        img = create_plate_image(text, is_yellow=is_yellow)
        res = anpr_service.process_plate_crop(img)
        expected_norm = normalize_plate(text)
        if res and normalize_plate(res.normalized) == expected_norm:
            record_test(f"Plate Format: {label}", True, f"Parsed: '{res.raw_text}' -> '{res.normalized}' (Conf: {res.confidence:.2f})")
        else:
            actual = res.normalized if res else "None"
            record_test(f"Plate Format: {label}", False, f"Expected {expected_norm}, Got {actual}")

    # -------------------------------------------------------------
    # Category 2: Adverse Environmental / Camera Conditions
    # -------------------------------------------------------------
    print("\n--- [CATEGORY 2] Adverse Optical Conditions ---")
    test_plate = "DL 03 XY 7788"
    
    # 2.1 Low light (night/shadow)
    img_dark = create_plate_image(test_plate, brightness=0.6)
    res_dark = anpr_service.process_plate_crop(img_dark)
    expected = normalize_plate(test_plate)
    record_test("Condition: Low Light / Dim (60% Brightness)", bool(res_dark and normalize_plate(res_dark.normalized) == expected), 
                f"Result: {res_dark.normalized if res_dark else 'Missed'}")

    # 2.2 Moderate camera motion blur
    img_blur = create_plate_image(test_plate, blur=3)
    res_blur = anpr_service.process_plate_crop(img_blur)
    record_test("Condition: Camera Motion Blur (3px)", bool(res_blur and normalize_plate(res_blur.normalized) == expected),
                f"Result: {res_blur.normalized if res_blur else 'Missed'}")

    # 2.3 Sensor noise (grainy CCTV)
    img_noise = create_plate_image(test_plate, noise_sigma=12.0)
    res_noise = anpr_service.process_plate_crop(img_noise)
    record_test("Condition: CCTV Sensor Noise (Sigma 12)", bool(res_noise and normalize_plate(res_noise.normalized) == expected),
                f"Result: {res_noise.normalized if res_noise else 'Missed'}")

    # 2.4 Slanted / Angled camera view (+3 degrees tilt)
    img_tilt = create_plate_image(test_plate, tilt_angle=3.0)
    res_tilt = anpr_service.process_plate_crop(img_tilt)
    record_test("Condition: Perspective / Tilt Angle (3 deg)", bool(res_tilt and normalize_plate(res_tilt.normalized) == expected),
                f"Result: {res_tilt.normalized if res_tilt else 'Missed'}")

    # -------------------------------------------------------------
    # Category 3: Non-Plate Rejection & False Positive Resistance
    # -------------------------------------------------------------
    print("\n--- [CATEGORY 3] Rejection of Non-Plate Objects ---")
    # Road sign with only letters, no digits
    sign_img = np.ones((100, 300, 3), dtype=np.uint8) * 200
    cv2.putText(sign_img, "SPEED LIMIT", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)
    res_sign = anpr_service.process_plate_crop(sign_img)
    record_test("Non-Plate: Pure Text Traffic Sign ('SPEED LIMIT')", res_sign is None,
                "Correctly rejected: plate must contain valid alphanumeric license structure")

    # Blank image with no text
    blank_img = np.ones((100, 300, 3), dtype=np.uint8) * 128
    res_blank = anpr_service.process_plate_crop(blank_img)
    record_test("Non-Plate: Blank Scene", res_blank is None, "Correctly returned None")

    # -------------------------------------------------------------
    # Category 4: End-to-End REST API Tests
    # -------------------------------------------------------------
    print("\n--- [CATEGORY 4] End-to-End API Workflows ---")
    
    # 4.1 Image upload
    api_plate = "WB 02 K 9988"
    img_bytes = img_to_bytes(create_plate_image(api_plate))
    resp = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("cam_feed.jpg", io.BytesIO(img_bytes), "image/jpeg")},
        data={"camera_id": "CAM-02", "direction": "Outbound"}
    )
    ok_upload = resp.status_code == 200 and resp.json().get("ok") is True
    record_test("API: POST /api/v1/analytics/anpr/image", ok_upload, f"Status {resp.status_code}, Count: {resp.json().get('count') if ok_upload else 0}")

    # 4.2 Watchlist match lifecycle
    wl_target = "GJ 05 AZ 7711"
    # Step A: Register plate to watchlist
    wl_add = client.post("/api/v1/analytics/watchlist", json={"plate_number": wl_target, "description": "High risk test"})
    ok_wl_add = wl_add.status_code == 200
    record_test("API: POST /api/v1/analytics/watchlist (Register)", ok_wl_add, f"Target: {wl_target}")

    # Step B: Detection triggers CRITICAL alert
    target_img = img_to_bytes(create_plate_image(wl_target))
    detect_resp = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("target.jpg", io.BytesIO(target_img), "image/jpeg")},
        data={"camera_id": "ANPR-01", "direction": "Inbound"}
    )
    d_json = detect_resp.json() if detect_resp.status_code == 200 else {}
    has_alert = any(a.get("severity") == "CRITICAL" for a in d_json.get("alerts", []))
    is_wl_status = any(c.get("status") == "WATCHLIST" for c in d_json.get("captures", []))
    record_test("API: Watchlist Detection Alert Trigger", has_alert and is_wl_status,
                f"Alerts: {len(d_json.get('alerts', []))}, Status: {d_json.get('captures', [{}])[0].get('status')}")

    # Step C: Watchlist deletion
    wl_del = client.delete(f"/api/v1/analytics/watchlist/{normalize_plate(wl_target)}")
    record_test("API: DELETE /api/v1/analytics/watchlist/{plate}", wl_del.status_code == 200, f"Deleted {wl_target}")

    # 4.3 Watchlist upload photo auto-OCR
    photo_target = "CH 01 AB 5544"
    p_bytes = img_to_bytes(create_plate_image(photo_target))
    wl_photo_resp = client.post(
        "/api/v1/analytics/watchlist/upload",
        files={"file": ("ref.jpg", io.BytesIO(p_bytes), "image/jpeg")}
    )
    p_json = wl_photo_resp.json() if wl_photo_resp.status_code == 200 else {}
    extracted = p_json.get("plate_number", "")
    record_test("API: POST /api/v1/analytics/watchlist/upload (Auto-OCR)", 
                normalize_plate(photo_target) in normalize_plate(extracted), 
                f"Extracted: '{extracted}'")

    # 4.4 Video upload processing
    print("\n--- [CATEGORY 5] Video Stream Sampling Processing ---")
    video_plates = ["DL 08 CC 1122", "MH 04 AB 3344"]
    vid_bytes = make_video_file_bytes(video_plates, frames_per_plate=16)
    vid_resp = client.post(
        "/api/v1/analytics/anpr/video",
        files={"file": ("test_surveillance.mp4", io.BytesIO(vid_bytes), "video/mp4")},
        data={"camera_id": "CAM-04", "sample_every_n_frames": 10, "max_captures": 10}
    )
    v_ok = vid_resp.status_code == 200 and vid_resp.json().get("ok") is True
    v_data = vid_resp.json() if v_ok else {}
    vid_captures = v_data.get("captures", [])
    record_test("API: POST /api/v1/analytics/anpr/video", v_ok and len(vid_captures) >= 1,
                f"Processed {v_data.get('frames_processed', 0)} frames, captured {len(vid_captures)} vehicles")

    # 4.5 Corrupted file handling (Edge Case)
    print("\n--- [CATEGORY 6] Edge Cases & Input Validation ---")
    corrupt_resp = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("bad.jpg", io.BytesIO(b"not a valid image content"), "image/jpeg")},
    )
    record_test("Validation: Corrupted Image Rejection", corrupt_resp.status_code == 400,
                f"Returned HTTP {corrupt_resp.status_code} with clean error: {corrupt_resp.json().get('detail')}")

    # 4.6 Empty video rejection
    empty_vid_resp = client.post(
        "/api/v1/analytics/anpr/video",
        files={"file": ("empty.mp4", io.BytesIO(b""), "video/mp4")},
    )
    record_test("Validation: Empty Video Rejection", empty_vid_resp.status_code == 400,
                f"Returned HTTP {empty_vid_resp.status_code} with clean error: {empty_vid_resp.json().get('detail')}")

    # -------------------------------------------------------------
    # Category 7: High-Precision Features & Artifact Integrity
    # -------------------------------------------------------------
    print("\n--- [CATEGORY 7] High-Precision Features & Artifact Integrity ---")

    # 7.1 Bharat Series (BH) Plate Format
    bh_plate = "22 BH 5678 AA"
    img_bh = create_plate_image(bh_plate)
    res_bh = anpr_service.process_plate_crop(img_bh)
    record_test("Precision: Bharat Series (BH) Format", bool(res_bh and "BH" in res_bh.normalized),
                f"Parsed: {res_bh.normalized if res_bh else 'Missed'} (State Code: {res_bh.state_code if res_bh else 'None'})")

    # 7.2 State Code Extraction Accuracy
    delhi_plate = "DL 09 PQ 1122"
    img_delhi = create_plate_image(delhi_plate)
    res_delhi = anpr_service.process_plate_crop(img_delhi)
    record_test("Precision: State Code Extraction (DL)", bool(res_delhi and res_delhi.state_code == "DL"),
                f"State extracted: {res_delhi.state_code if res_delhi else 'None'}")

    # 7.3 Laplacian Sharpness Metric (Sharp vs Blurry)
    img_sharp = create_plate_image("MH 01 AB 9999", blur=0)
    img_blurry = create_plate_image("MH 01 AB 9999", blur=7)
    res_sharp = anpr_service.process_plate_crop(img_sharp)
    res_blurry = anpr_service.process_plate_crop(img_blurry)
    sharp_val = res_sharp.sharpness if res_sharp else 0.0
    blur_val = res_blurry.sharpness if res_blurry else 0.0
    record_test("Precision: Laplacian Sharpness Metric Differentiation", sharp_val > blur_val and sharp_val > 50.0,
                f"Sharpness: sharp={sharp_val:.1f} vs blurry={blur_val:.1f}")

    # 7.4 Multi-Artifact HUD & Plate Image Verification in Pipeline
    art_plate = "KA 03 MN 4567"
    art_img_bytes = img_to_bytes(create_plate_image(art_plate))
    art_resp = client.post(
        "/api/v1/analytics/anpr/image",
        files={"file": ("artifacts_test.jpg", io.BytesIO(art_img_bytes), "image/jpeg")},
        data={"camera_id": "CAM-01", "direction": "Inbound"}
    )
    art_data = art_resp.json() if art_resp.status_code == 200 else {}
    art_captures = art_data.get("captures", [])
    has_artifacts = False
    if art_captures:
        cap = art_captures[0]
        has_artifacts = bool(
            cap.get("annotatedImage") and 
            cap.get("plateImage") and 
            cap.get("stateCode") == "KA" and
            cap.get("sharpness", 0) > 0
        )
    record_test("Precision: HUD Annotated & Zoomed Plate Artifact Generation", has_artifacts,
                f"annotatedImage={bool(art_captures and art_captures[0].get('annotatedImage'))}, "
                f"plateImage={bool(art_captures and art_captures[0].get('plateImage'))}, "
                f"stateCode={art_captures[0].get('stateCode') if art_captures else None}")


    # -------------------------------------------------------------
    # Summary
    # -------------------------------------------------------------
    print("\n=================================================================")
    print(f"ANPR TEST SUITE SUMMARY: {passed} / {total} TESTS PASSED ({(passed/total)*100:.1f}%)")
    print("=================================================================")
    for name, stat, detail in results:
        print(f"[{stat:4}] {name.ljust(48)} | {detail}")

    assert passed == total, f"Some tests failed! {total - passed} failure(s)."

if __name__ == "__main__":
    run_suite()
