import threading
import logging
from typing import Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_MODEL_PATH = BACKEND_DIR / "yolov8n.pt"

class ModelManager:
    """
    Singleton AI model loader.
    Ensures YOLO and other large models are loaded into memory exactly ONCE 
    per process, avoiding overlapping RAM usage. Provides shared references.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ModelManager, cls).__new__(cls)
                cls._instance._yolo_model = None
                cls._instance._yolo_class_ids = None
                cls._instance._yolo_error = None
                cls._instance._yolo_lock = threading.Lock()
        return cls._instance

    def get_yolo(self, model_path: Optional[str] = None) -> tuple[Any, list[int], str]:
        """
        Returns (model, class_ids, error) thread-safely.
        """
        with self._yolo_lock:
            if self._yolo_model is not None or self._yolo_error is not None:
                return self._yolo_model, self._yolo_class_ids, self._yolo_error
            
            try:
                from ultralytics import YOLO
                path = model_path or str(DEFAULT_MODEL_PATH if DEFAULT_MODEL_PATH.exists() else "yolov8n.pt")
                logger.info(f"Loading YOLO model once from {path}")
                self._yolo_model = YOLO(path)
                
                # Pre-filter vehicle/person class IDs
                names = getattr(self._yolo_model, "names", {})
                
                # Keep person and vehicles
                TARGET_LABELS = {"person", "car", "motorcycle", "bus", "truck"}
                self._yolo_class_ids = [cid for cid, label in names.items() if label in TARGET_LABELS]
                
                # Warmup inference
                import numpy as np
                dummy = np.zeros((320, 320, 3), dtype=np.uint8)
                self._yolo_model(dummy, verbose=False)
                logger.info("YOLO model warmed up successfully.")
                
            except Exception as e:
                self._yolo_error = str(e)
                logger.error(f"Failed to load YOLO: {e}")

            return self._yolo_model, self._yolo_class_ids or [], self._yolo_error

model_manager = ModelManager()
