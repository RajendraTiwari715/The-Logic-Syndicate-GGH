from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import cv2
from app.services.video_stream import get_video_stream
from app.services.ml_engine import process_frame

router = APIRouter()

def generate_frames():
    stream = get_video_stream()
    while True:
        frame = stream.read()
        if frame is not None:
            # Process frame with ML Engine (YOLO)
            processed_frame, alerts = process_frame(frame)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            
            # Yield as multipart
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@router.get("/live")
def video_feed():
    return StreamingResponse(generate_frames(), media_type="multipart/x-mixed-replace; boundary=frame")
