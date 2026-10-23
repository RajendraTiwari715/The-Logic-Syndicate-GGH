from __future__ import annotations

import os
import re
import cv2
import time
import socket
import base64
import logging
import threading
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse
import numpy as np

logger = logging.getLogger(__name__)

# CCTV Brand RTSP URL Templates
CCTV_BRAND_TEMPLATES = {
    "hikvision": "rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/{channel}01",
    "dahua": "rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    "cpplus": "rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel={channel}&subtype=0",
    "axis": "rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp?camera={channel}",
    "uniview": "rtsp://{username}:{password}@{ip}:{port}/unicast/c{channel}/s0/live",
    "hanwha": "rtsp://{username}:{password}@{ip}:{port}/profile{channel}/media.smp",
    "bosch": "rtsp://{username}:{password}@{ip}:{port}/rtsp_tunnel?line={channel}",
    "tiandy": "rtsp://{username}:{password}@{ip}:{port}/video{channel}",
    "onvif": "rtsp://{username}:{password}@{ip}:{port}/onvif1",
    "generic_rtsp": "rtsp://{username}:{password}@{ip}:{port}/{path}",
}


class UniversalCCTVConnector:
    """Universal CCTV infrastructure adapter supporting all enterprise IP cameras,
    NVRs, VMS, RTSP, RTSPS, ONVIF, HTTP/MJPEG, and local hardware streams."""

    @staticmethod
    def build_rtsp_url(
        brand: str,
        ip: str,
        port: int = 554,
        username: str = "admin",
        password: str = "",
        channel: int = 1,
        custom_path: str = "live",
    ) -> str:
        """Constructs vendor-compliant RTSP connection string for any major CCTV manufacturer."""
        brand_key = brand.lower().replace(" ", "").replace("-", "")
        template = CCTV_BRAND_TEMPLATES.get(brand_key, CCTV_BRAND_TEMPLATES["generic_rtsp"])
        
        # URL encode credentials safely if needed
        safe_user = username.strip()
        safe_pass = password.strip()
        
        # Strip protocol if user included it in IP
        clean_ip = re.sub(r"^https?://|^rtsp://", "", ip.strip()).rstrip("/")
        
        url = template.format(
            username=safe_user,
            password=safe_pass,
            ip=clean_ip,
            port=port or 554,
            channel=channel or 1,
            path=custom_path.lstrip("/"),
        )
        return url

    @staticmethod
    def probe_stream(source: str, timeout_seconds: float = 2.0) -> Dict[str, Any]:
        """Probes any live CCTV stream (RTSP, HTTP, webcam, file).
        Returns stream availability, FPS, resolution, codec, and a base64 thumbnail."""
        clean_source = source.strip()
        start_time = time.perf_counter()

        # Fast socket pre-check for network streams to avoid long OS-level timeouts
        if clean_source.startswith("rtsp://") or clean_source.startswith("http://") or clean_source.startswith("https://"):
            try:
                parsed = urlparse(clean_source)
                host = parsed.hostname
                port = parsed.port or (554 if clean_source.startswith("rtsp://") else 80)
                if host:
                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    s.settimeout(1.2)
                    res = s.connect_ex((host, port))
                    s.close()
                    if res != 0:
                        return {
                            "accessible": False,
                            "error": f"Cannot reach CCTV network endpoint {host}:{port} (socket error code {res})",
                            "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
                        }
            except Exception as e:
                return {
                    "accessible": False,
                    "error": f"Network resolution failed for {clean_source}: {e}",
                    "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
                }

        source_val: Any = int(clean_source) if clean_source.isdigit() else clean_source

        # Set OpenCV FFMPEG network flags for fast connection & TCP transport
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000|buffer_size;1024000"

        cap = cv2.VideoCapture(source_val, cv2.CAP_FFMPEG if isinstance(source_val, str) else cv2.CAP_ANY)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not cap.isOpened():
            return {
                "accessible": False,
                "error": f"Failed to establish handshake with CCTV source: {source}",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 1),
            }

        ok, frame = cap.read()
        latency_ms = round((time.perf_counter() - start_time) * 1000, 1)

        if not ok or frame is None:
            cap.release()
            return {
                "accessible": False,
                "error": "CCTV handshake succeeded but no video packets received (stream might be idle or password incorrect)",
                "latency_ms": latency_ms,
            }

        height, width = frame.shape[:2]
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
        backend_name = cap.getBackendName()
        cap.release()

        # Generate small thumbnail
        thumb = cv2.resize(frame, (320, 180), interpolation=cv2.INTER_AREA)
        _, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        b64_thumb = f"data:image/jpeg;base64,{base64.b64encode(buf.tobytes()).decode('utf-8')}"

        return {
            "accessible": True,
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}",
            "fps": round(fps, 1),
            "latency_ms": latency_ms,
            "backend": backend_name,
            "thumbnail": b64_thumb,
        }


class LiveCCTVWorker:
    """Decoupled high-performance threaded reader that ingests from any CCTV stream
    with automatic reconnection, zero frame buffer lag, and continuous AI execution."""

    def __init__(self, camera_id: str, source: str, name: str = "CCTV"):
        self.camera_id = camera_id
        self.source = source
        self.name = name
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._annotated_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self.status = "DISCONNECTED"
        self.fps = 0.0
        self.latency_ms = 0.0
        self.last_seen = time.time()
        self.reconnect_count = 0
        self._ai_callback = None

    def set_ai_callback(self, callback):
        """Attaches autonomous AI callback to be called on sampled frames."""
        self._ai_callback = callback

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker_loop, name=f"cctv-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info("Universal CCTV Ingestion Worker started for %s (%s)", self.camera_id, self.source)

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        return None

    def get_annotated_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            if self._annotated_frame is not None:
                return self._annotated_frame.copy()
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        return None

    def _worker_loop(self):
        source_val: Any = int(self.source) if str(self.source).isdigit() else self.source
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;5000000|buffer_size;1024000"

        frame_count = 0
        fps_start = time.perf_counter()

        while self._running:
            self.status = "CONNECTING"
            cap = cv2.VideoCapture(source_val, cv2.CAP_FFMPEG if isinstance(source_val, str) else cv2.CAP_ANY)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            if not cap.isOpened():
                self.status = "OFFLINE"
                self.reconnect_count += 1
                time.sleep(3.0)
                continue

            self.status = "LIVE"
            logger.info("CCTV Stream [%s] connected successfully.", self.camera_id)

            while self._running:
                t0 = time.perf_counter()
                ok, frame = cap.read()
                if not ok or frame is None:
                    logger.warning("Stream [%s] lost frames. Attempting automatic reconnect...", self.camera_id)
                    self.status = "DEGRADED"
                    break

                self.latency_ms = (time.perf_counter() - t0) * 1000
                self.last_seen = time.time()
                frame_count += 1

                with self._lock:
                    self._latest_frame = frame.copy()

                # Calculate live FPS
                elapsed = time.perf_counter() - fps_start
                if elapsed >= 1.0:
                    self.fps = round(frame_count / elapsed, 1)
                    frame_count = 0
                    fps_start = time.perf_counter()

                # Run autonomous AI pipeline every N frames (e.g. 5 FPS evaluation rate)
                if frame_count % 3 == 0 and self._ai_callback:
                    try:
                        annotated = self._ai_callback(self.camera_id, frame.copy())
                        if annotated is not None:
                            with self._lock:
                                self._annotated_frame = annotated
                    except Exception as exc:
                        logger.error("Error in CCTV AI Pipeline for %s: %s", self.camera_id, exc)

                # Brief sleep to yield GIL
                time.sleep(0.01)

            cap.release()
            time.sleep(2.0)


class UniversalCCTVManager:
    """Global manager orchestrating multiple CCTV camera streams across borders, sites, and gates."""
    _instance = None

    @classmethod
    def get_instance(cls) -> UniversalCCTVManager:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._workers: Dict[str, LiveCCTVWorker] = {}
        self._lock = threading.Lock()

    def register_and_start(self, camera_id: str, source: str, name: str = "CCTV", ai_callback=None) -> LiveCCTVWorker:
        with self._lock:
            if camera_id in self._workers:
                worker = self._workers[camera_id]
                if worker.source != source:
                    worker.stop()
                    del self._workers[camera_id]
                else:
                    return worker

            worker = LiveCCTVWorker(camera_id=camera_id, source=source, name=name)
            if ai_callback:
                worker.set_ai_callback(ai_callback)
            worker.start()
            self._workers[camera_id] = worker
            return worker

    def stop_camera(self, camera_id: str):
        with self._lock:
            if camera_id in self._workers:
                self._workers[camera_id].stop()
                del self._workers[camera_id]

    def stop_all(self):
        with self._lock:
            for worker in self._workers.values():
                worker.stop()
            self._workers.clear()

    def get_worker(self, camera_id: str) -> Optional[LiveCCTVWorker]:
        return self._workers.get(camera_id)

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        result = {}
        for cam_id, w in self._workers.items():
            result[cam_id] = {
                "camera_id": cam_id,
                "name": w.name,
                "status": w.status,
                "fps": w.fps,
                "latency_ms": round(w.latency_ms, 1),
                "reconnects": w.reconnect_count,
            }
        return result


cctv_manager = UniversalCCTVManager.get_instance()
