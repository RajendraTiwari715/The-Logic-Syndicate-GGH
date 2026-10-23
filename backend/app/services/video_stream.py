import cv2
import threading
import time
import os

class VideoStreamProcessor:
    def __init__(self, source=0):
        print(f"Initializing VideoStreamProcessor with source: {source}")
        self.source = source
        self.cap = None
        self.frame = None
        self.running = False
        self.lock = threading.Lock()
        self._thread = None

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self.update, daemon=True)
        self._thread.start()

    def update(self):
        self.cap = cv2.VideoCapture(self.source)
        if not self.cap.isOpened():
            print(f"Warning: Could not open video source {self.source}")

        while self.running:
            if not self.cap.isOpened():
                time.sleep(2) # Wait before retry (good for RTSP reconnects)
                self.cap = cv2.VideoCapture(self.source)
                continue
                
            ret, frame = self.cap.read()
            if not ret:
                # Reconnect logic for RTSP or loop for Video file
                print("Warning: Stream lost or ended, attempting reconnect...")
                if isinstance(self.source, str) and not self.source.startswith("rtsp"):
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0) # Video loop
                else:
                    self.cap.release()
                    time.sleep(2) # wait before RTSP reconnect
                continue

            with self.lock:
                self.frame = frame.copy()
            
            # Tiny sleep to yield thread and control FPS reading
            time.sleep(0.01)

    def read(self):
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
        return None

    def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if self.cap and self.cap.isOpened():
            self.cap.release()

# Instead of global auto-start, create a registry
_streams = {}

def get_video_stream(source="0") -> VideoStreamProcessor:
    if source not in _streams:
        source_val = int(source) if str(source).isdigit() else source
        _streams[source] = VideoStreamProcessor(source=source_val)
        _streams[source].start()
    return _streams[source]

def stop_video_stream(source="0"):
    if source in _streams:
        _streams[source].stop()
        del _streams[source]
