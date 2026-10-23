import cv2
import numpy as np
import threading
import asyncio
from datetime import datetime
from app.vision.detector import YoloTrackingDetector, DetectionObservation
from app.api.deps import get_db

class MLEngine:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.detector = None
        self.initialized = False
        self.lock = threading.Lock()
        
    def initialize(self):
        with self.lock:
            if not self.initialized:
                try:
                    self.detector = YoloTrackingDetector()
                    self.initialized = True
                    print("MLEngine adapter initialized properly.")
                except Exception as e:
                    print(f"Error initializing MLEngine: {e}")

    def process_frame(self, frame, camera_id="BOP-04"):
        if not self.initialized:
            self.initialize()
            
        alerts = []
        processed_frame = frame.copy()
        
        if not self.detector:
            return processed_frame, alerts
            
        detections = self.detector.infer(frame)
        
        for det in detections:
            x1, y1, x2, y2 = det.bbox_xyxy
            
            color = (0, 255, 0)
            if det.object_type == "person":
                color = (255, 165, 0) # Orange
                
            cv2.rectangle(processed_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, 2)
            label = f"{det.object_class} {det.confidence:.2f}"
            if det.raw_track_id is not None:
                label += f" [ID:{det.raw_track_id}]"
                
            cv2.putText(processed_frame, label, (int(x1), int(y1) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            # Connect virtual fence and risk engine
            if det.object_type == "person" and det.confidence > 0.6:
                # Trigger Event
                # For testing local pipeline seamlessly, we construct raw mock integration
                alert_payload = {
                    "eventType": "HUMAN_DETECTED",
                    "camera_id": camera_id,
                    "confidence": det.confidence,
                    "bbox": det.bbox_xyxy,
                    "riskScore": 75,
                    "severity": "HIGH",
                    "reason": "Person detected in critical view"
                }
                alerts.append(alert_payload)
                
        return processed_frame, alerts

_engine = MLEngine.get_instance()

def process_frame(frame, camera_id="BOP-04"):
    return _engine.process_frame(frame, camera_id=camera_id)

