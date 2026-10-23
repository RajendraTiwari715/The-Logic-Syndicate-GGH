from datetime import datetime, tzinfo, timezone
from typing import Optional, List, Dict, Any
from app.models.core_models import EventType, EventItem, Detection, AlertState, Alert
from app.db.session import get_db
from app.services.offline_sync import offline_queue

class EventEngine:
    def __init__(self):
        # Time constraints and thresholds
        self.loitering_threshold_seconds = 60
        self.active_tracks: Dict[str, Dict[str, Any]] = {}
        self.night_mode_start_hour = 19
        self.night_mode_end_hour = 5

    def _is_night(self) -> bool:
        h = datetime.now().hour
        if self.night_mode_start_hour <= 23 or h <= self.night_mode_end_hour:
            return h >= self.night_mode_start_hour or h <= self.night_mode_end_hour
        return False

    def process_detection(self, db, detection: Detection) -> List[EventItem]:
        events_generated = []
        
        # 1. Base Class Identification
        if detection.objectType.lower() == "person":
            events_generated.append(self._create_event(db, detection.cameraId, EventType.HUMAN_DETECTED, "LOW", tracking_id=detection.trackingId))
        elif detection.objectType.lower() in ["car", "truck", "motorcycle", "vehicle"]:
            events_generated.append(self._create_event(db, detection.cameraId, EventType.VEHICLE_DETECTED, "LOW", tracking_id=detection.trackingId))
        
        # 2. Night Movement
        if self._is_night():
            events_generated.append(self._create_event(db, detection.cameraId, EventType.NIGHT_MOVEMENT, "MEDIUM", tracking_id=detection.trackingId))

        return events_generated

    def process_track(self, db, tracking_id: str, camera_id: str, first_seen: datetime, last_seen: datetime, zones: List[str]) -> Optional[EventItem]:
        dwell_time = (last_seen - first_seen).total_seconds()
        if dwell_time >= self.loitering_threshold_seconds:
            # check deduplication: if we already fired loitering for this track recently
            return self._create_event(db, camera_id, EventType.LOITERING, "HIGH", tracking_id=tracking_id, reasons=[f"Dwell > {self.loitering_threshold_seconds}s"])
        return None
        
    def emit_camera_offline(self, db, camera_id: str):
        self._create_event(db, camera_id, EventType.CAMERA_OFFLINE, "CRITICAL")

    def _create_event(self, db, camera_id: str, event_type: EventType, severity: str, tracking_id: str = None, reasons: List[str] = None) -> EventItem:
        # Check DB deduplication here natively to prevent spamming
        event = EventItem(
            cameraId=camera_id,
            eventType=event_type,
            severity=severity,
            trackingId=tracking_id,
            description=f"{event_type} at {camera_id}",
            reasons=reasons or [],
            status="NEW",
            riskScore=50
        )
        if db:
            db.add(event)
            db.commit()
            db.refresh(event)
            
        # Add to offline queue for edge logic
        offline_queue.enqueue("event", {"camera_id": camera_id, "type": event_type, "severity": severity})
            
        return event

event_engine = EventEngine()
