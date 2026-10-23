import cv2
import numpy as np
import os

def create_e2e_video():
    print("Building final test video...")
    person_img = cv2.imread("zidane.jpg")
    bus_img = cv2.imread("bus.jpg")

    if person_img is None or bus_img is None:
        print("Images missing.")
        return

    # Resize universally
    H, W = 720, 1280
    person_img = cv2.resize(person_img, (W, H))
    bus_img = cv2.resize(bus_img, (W, H))

    # Add plate to bus
    # YOLO detects bus. We add a large plate in center
    cv2.rectangle(bus_img, (400, 500), (800, 600), (255, 255, 255), -1)
    cv2.rectangle(bus_img, (405, 505), (795, 595), (0, 0, 0), 4)
    cv2.putText(bus_img, "DL 01 AB 1234", (430, 570), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 6)

    # Add plate to bus (Unauthorized variant)
    bus_img2 = bus_img.copy()
    cv2.rectangle(bus_img2, (400, 500), (800, 600), (255, 255, 255), -1)
    cv2.rectangle(bus_img2, (405, 505), (795, 595), (0, 0, 0), 4)
    cv2.putText(bus_img2, "MH 04 UN 5678", (430, 570), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 6)

    out = cv2.VideoWriter("final_test_video.mp4", cv2.VideoWriter_fourcc(*'mp4v'), 2, (W, H))

    # 1. Unknown Person (5 frames)
    for _ in range(5):
        out.write(person_img)

    # 2. Blank frame boundary (1 frame)
    out.write(np.zeros((H, W, 3), dtype=np.uint8))

    # 3. Known Vehicle (Authorized - 5 frames)
    for _ in range(5):
        out.write(bus_img)
        
    out.write(np.zeros((H, W, 3), dtype=np.uint8))

    # 4. Unknown/Unauthorized Vehicle (5 frames)
    for _ in range(5):
        out.write(bus_img2)

    out.release()
    print("Video built successfully at final_test_video.mp4")

if __name__ == "__main__":
    create_e2e_video()
