import threading
import queue
import time
import logging
from typing import Optional, Callable
import numpy as np

logger = logging.getLogger(__name__)

class CameraWorker:
    """
    Isolated worker thread per camera.
    Ingests frames through backpressured limited queue, ensuring one camera 
    stalling does not block other cameras or memory leak.
    """
    def __init__(self, camera_id: str, priority: str = "NORMAL", max_queue_size: int = 5):
        self.camera_id = camera_id
        self.priority = priority
        self.max_queue_size = max_queue_size
        
        # Bounded queue forces backpressure
        self.frame_queue: queue.Queue = queue.Queue(maxsize=max_queue_size)
        self.is_running = False
        self._thread: Optional[threading.Thread] = None
        self._inference_callback: Optional[Callable[[np.ndarray, str, dict], None]] = None
        self.fps_target = 15.0 if priority == "CRITICAL" else 5.0
        self.frames_dropped = 0
        self.frames_processed = 0

        # Video Recording State
        import os
        from app.config import settings
        self.storage_dir = os.path.join(getattr(settings, "DATA_DIR", "data"), "recordings")
        os.makedirs(self.storage_dir, exist_ok=True)
        self._video_writer = None
        self._frames_in_chunk = 0
        self.chunk_size_frames = int(self.fps_target) * 30  # 30 seconds chunks for SIH demo

    def set_callback(self, callback: Callable[[np.ndarray, str, dict], None]):
        self._inference_callback = callback

    def enqueue_frame(self, frame: np.ndarray, context: dict = None) -> bool:
        """
        Push new frame into worker queue. 
        Drops oldest frame actively if overloaded (Backpressure).
        """
        if not self.is_running:
            return False

        try:
            self.frame_queue.put_nowait((frame, context or {}))
            return True
        except queue.Full:
            # Overloaded logic DROP OLD FRAME
            try:
                self.frame_queue.get_nowait()
                self.frames_dropped += 1
            except queue.Empty:
                pass
            
            # Put the fresh frame
            try:
                self.frame_queue.put_nowait((frame, context or {}))
                return True
            except queue.Full:
                return False

    def _worker_loop(self):
        logger.info(f"Worker {self.camera_id} started. Priority {self.priority}.")
        while self.is_running:
            try:
                frame, context = self.frame_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            start_time = time.time()

            try:
                self._record_frame(frame)
            except Exception as e:
                logger.error(f"Recording error on {self.camera_id}: {e}")

            try:
                if self._inference_callback:
                    # Execute AI Pipeline segment
                    self._inference_callback(frame, self.camera_id, context)
                    self.frames_processed += 1
            except Exception as e:
                logger.error(f"Worker {self.camera_id} inference failed: {e}")

            # Adaptive Inference FPS Throttle
            processing_time = time.time() - start_time
            sleep_time = max(0.0, (1.0 / self.fps_target) - processing_time)
            
            if sleep_time > 0:
                time.sleep(sleep_time)
                
        logger.info(f"Worker {self.camera_id} stopping.")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._worker_loop, daemon=True, name=f"Worker-{self.camera_id}")
        self._thread.start()

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        self._release_writer()

    def _release_writer(self):
        import cv2
        if self._video_writer:
            self._video_writer.release()
            self._video_writer = None

    def _record_frame(self, frame: np.ndarray):
        import cv2
        import time
        import os
        
        if self._video_writer is None or self._frames_in_chunk >= self.chunk_size_frames:
            self._release_writer()
            self._frames_in_chunk = 0
            filename = f"cam_{self.camera_id}_{int(time.time())}.mp4"
            filepath = os.path.join(self.storage_dir, filename)
            # Use mp4v codec for generic browser support natively
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            height, width = frame.shape[:2]
            self._video_writer = cv2.VideoWriter(filepath, fourcc, self.fps_target, (width, height))
            logger.info(f"Started new video chunk for {self.camera_id}: {filename}")
            
        if self._video_writer:
            self._video_writer.write(frame)
            self._frames_in_chunk += 1

    def stats(self) -> dict:
        return {
            "camera_id": self.camera_id,
            "priority": self.priority,
            "queue_depth": self.frame_queue.qsize(),
            "frames_dropped": self.frames_dropped,
            "frames_processed": self.frames_processed
        }
