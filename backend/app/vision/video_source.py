from abc import ABC, abstractmethod
import cv2
import numpy as np
import time
import base64
import os
from typing import Optional, Tuple

class BaseVideoSource(ABC):
    """
    Abstract Base Class for video ingestion streams.
    Ensures the downstream AI pipeline consumes frames transparently
    whether they come from a file, an RTSP stream, or a Base64 socket.
    """
    def __init__(self, source_id: str):
        self.source_id = source_id
        self.is_connected = False
        self.last_frame_time = time.time()
        self.reconnect_count = 0
        self.frames_processed = 0

    @abstractmethod
    def connect(self) -> bool:
        pass

    @abstractmethod
    def read(self) -> Optional[np.ndarray]:
        pass

    @abstractmethod
    def reconnect(self) -> bool:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    def health(self) -> dict:
        return {
            "source_id": self.source_id,
            "connected": self.is_connected,
            "reconnect_count": self.reconnect_count,
            "uptime_seconds": time.time() - self.last_frame_time,
            "frames_processed": self.frames_processed
        }

class DemoVideoSource(BaseVideoSource):
    """
    Consumes a localized demo video file.
    """
    def __init__(self, source_id: str, file_path: str):
        super().__init__(source_id)
        self.file_path = file_path
        self._cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        self._cap = cv2.VideoCapture(self.file_path)
        self.is_connected = self._cap.isOpened()
        return self.is_connected

    def read(self) -> Optional[np.ndarray]:
        if not self.is_connected or not self._cap:
            return None
        ret, frame = self._cap.read()
        if ret:
            self.last_frame_time = time.time()
            self.frames_processed += 1
            return frame
        else:
            # Loop for demo
            self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self._cap.read()
            if ret:
                self.last_frame_time = time.time()
                self.frames_processed += 1
                return frame
            return None

    def reconnect(self) -> bool:
        self.reconnect_count += 1
        self.close()
        return self.connect()

    def close(self) -> None:
        if self._cap:
            self._cap.release()
        self.is_connected = False

class RTSPVideoSource(BaseVideoSource):
    """
    Consumes live RTSP network streams for production.
    """
    def __init__(self, source_id: str, rtsp_url: str):
        super().__init__(source_id)
        self.rtsp_url = rtsp_url
        self._cap: Optional[cv2.VideoCapture] = None

    def connect(self) -> bool:
        # Optimizations for low latency RTSP read
        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
        self._cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        self.is_connected = self._cap.isOpened()
        return self.is_connected

    def read(self) -> Optional[np.ndarray]:
        if not self.is_connected or not self._cap:
            return None
        ret, frame = self._cap.read()
        if ret:
            self.last_frame_time = time.time()
            self.frames_processed += 1
            return frame
        else:
            self.is_connected = False
            return None

    def reconnect(self) -> bool:
        self.reconnect_count += 1
        self.close()
        # Add slight backoff
        time.sleep(1)
        return self.connect()

    def close(self) -> None:
        if self._cap:
            self._cap.release()
        self.is_connected = False

class Base64Source(BaseVideoSource):
    """
    Adapter for immediate frontend legacy support during transition.
    Injects base64 strings directly via read(base64_str).
    """
    def __init__(self, source_id: str):
        super().__init__(source_id)
        self.connect()

    def connect(self) -> bool:
        self.is_connected = True
        return True

    def _decode_b64(self, b64_str: str) -> np.ndarray:
        if "," in b64_str:
            b64_str = b64_str.split(",", 1)[1]
        raw = base64.b64decode(b64_str, validate=True)
        img_array = np.frombuffer(raw, dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    def read(self, payload: Optional[str] = None) -> Optional[np.ndarray]:
        if not payload:
            return None
        self.last_frame_time = time.time()
        self.frames_processed += 1
        try:
            return self._decode_b64(payload)
        except Exception:
            return None

    def reconnect(self) -> bool:
        return True

    def close(self) -> None:
        self.is_connected = False
