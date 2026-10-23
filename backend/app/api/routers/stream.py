from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
import cv2
from app.services.video_stream import get_video_stream
from app.services.ml_engine import process_frame
from app.services.snapshot_store import evidence_storage
from pathlib import Path

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


@router.get("/evidence/{filename}")
def get_evidence_image(filename: str):
    """Serve persisted camera snapshots from MinIO or the durable local fallback."""
    if Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid evidence filename")
    contents = evidence_storage.download_evidence(filename)
    if contents is None:
        raise HTTPException(status_code=404, detail="Evidence image not found")
    return Response(
        content=contents,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=3600"},
    )
