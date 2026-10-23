# IBVAP AI Backend Setup

## 1. Install Python dependencies

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. YOLO model

The backend uses Ultralytics YOLO with ByteTrack.

- Default: leave `MODEL_PATH` empty and the service will use `yolov8n.pt`.
- Offline/manual: download a YOLO model file yourself and set `MODEL_PATH=/absolute/path/to/yolov8n.pt`.

## 3. Environment setup

From the project root:

```bash
cp .env.example .env
```

Key variables:

- `CAMERA_SOURCE=0` for laptop webcam
- `CAMERA_SOURCE=rtsp://...` for RTSP/IP camera
- `MODEL_PATH=` optional custom YOLO model path
- `CONFIDENCE_THRESHOLD=0.4`
- `IMAGE_SIZE=640`
- `MAX_FPS=12`
- `LOITERING_THRESHOLD=60`
- `NIGHT_START=22:00`
- `NIGHT_END=05:00`
- `VITE_AI_API_BASE=http://127.0.0.1:8000`

## 4. Start the FastAPI AI service

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 5. Start webcam mode

Set:

```bash
CAMERA_SOURCE=0
```

Then start the backend. The default camera is exposed as `BOP-01`.

## 6. Use an uploaded video file

Start the backend, then upload a file:

```bash
curl -F "file=@/absolute/path/to/video.mp4" http://127.0.0.1:8000/api/cameras/upload
```

Use the returned `source_path` to create a camera:

```bash
curl -X POST http://127.0.0.1:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "BOP-VID",
    "name": "Uploaded Video",
    "bop": "BOP Video",
    "location": "Forensic Playback",
    "source": "/absolute/path/from/upload/response.mp4"
  }'
```

## 7. Configure an RTSP CCTV camera

Set either:

```bash
CAMERA_SOURCE=rtsp://username:password@camera-ip:554/stream
```

or create a new camera dynamically:

```bash
curl -X POST http://127.0.0.1:8000/api/cameras \
  -H "Content-Type: application/json" \
  -d '{
    "camera_id": "BOP-RTSP",
    "name": "Gate RTSP Camera",
    "bop": "BOP Bravo",
    "location": "Gate 2",
    "source": "rtsp://username:password@camera-ip:554/stream"
  }'
```

Do not hardcode real CCTV credentials into the codebase.

## 8. Connect the existing frontend

```bash
npm install
npm run dev
```

The frontend reads `VITE_AI_API_BASE` and can switch between:

- Demo Mode
- Real Camera Mode

In Real Camera Mode, the frontend uses:

- MJPEG stream: `/api/stream/{camera_id}`
- REST APIs under `/api/...`
- WebSocket: `/ws/analytics`

## 9. Virtual fences

Virtual fence coordinates are stored as percentages relative to the rendered frame.

- `Tripwire` or any 2-point zone: line crossing detection
- Polygon zones: restricted-area entry + loitering timing
- Person alerts are created from real tracked detections only

## 10. Troubleshooting

- Webcam does not open:
  - Check that no other app is holding the device.
  - Try `CAMERA_SOURCE=0` or `1` depending on your machine.
- YOLO model fails to load:
  - Set `MODEL_PATH` to a local `.pt` file.
- RTSP feed disconnects:
  - Check the URL, firewall, and network reachability.
  - The backend retries automatically.
- Frontend shows no real data:
  - Confirm backend is running on `http://127.0.0.1:8000`.
  - Confirm `.env` includes `VITE_AI_API_BASE=http://127.0.0.1:8000`.
- Alerts do not appear:
  - Check `/api/events`, `/api/alerts`, and the backend terminal logs.

## Current prototype notes

- Real detections/tracking are backed by YOLO + ByteTrack in Real Camera Mode.
- ANPR/OCR is not implemented in the real pipeline yet, so the ANPR page remains limited outside Demo Mode.
- Cross-camera identity handoff is not implemented yet; tracking is stable within each individual camera stream.
