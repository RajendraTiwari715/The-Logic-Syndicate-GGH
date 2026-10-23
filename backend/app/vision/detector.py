from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from ultralytics import YOLO

from app.config import settings


TARGET_CLASSES = {"person", "car", "motorcycle", "bus", "truck", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear"}


@dataclass(slots=True)
class DetectionObservation:
    raw_track_id: int | None
    object_class: str
    object_type: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]


class YoloTrackingDetector:
    def __init__(self) -> None:
        model_reference = settings.model_path or "yolov8n.pt"
        self.model = YOLO(model_reference)
        names = self.model.names
        self.class_ids = [class_id for class_id, label in names.items() if label in TARGET_CLASSES]

    def infer(self, frame: np.ndarray) -> list[DetectionObservation]:
        results = self.model.track(
            frame,
            persist=True,
            tracker="bytetrack.yaml",
            classes=self.class_ids,
            conf=settings.confidence_threshold,
            imgsz=settings.image_size,
            verbose=False,
        )
        if not results:
            return []

        boxes = results[0].boxes
        if boxes is None or boxes.xyxy is None:
            return []

        xyxy = boxes.xyxy.cpu().numpy()
        confidences = boxes.conf.cpu().numpy() if boxes.conf is not None else np.array([])
        class_ids = boxes.cls.cpu().numpy().astype(int) if boxes.cls is not None else np.array([], dtype=int)
        track_ids = boxes.id.cpu().numpy().astype(int) if boxes.id is not None else np.array([None] * len(xyxy), dtype=object)

        detections: list[DetectionObservation] = []
        for index, box in enumerate(xyxy):
            object_class = str(self.model.names[int(class_ids[index])])
            
            if object_class == "person":
                object_type = "person"
            elif object_class in {"car", "motorcycle", "bus", "truck"}:
                object_type = "vehicle"
            else:
                object_type = "animal"
                
            detections.append(
                DetectionObservation(
                    raw_track_id=None if track_ids[index] is None else int(track_ids[index]),
                    object_class=object_class,
                    object_type=object_type,
                    confidence=float(confidences[index]),
                    bbox_xyxy=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
                )
            )
        return detections
