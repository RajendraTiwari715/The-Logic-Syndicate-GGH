import time
import hashlib
from typing import Optional, Dict

class AlertEngine:
    """
    Minimizes alert fatigue by deduplicating incidents.
    Many Detections -> 1 Event -> 1 Alert -> 1 Incident.
    """
    def __init__(self, cooldown_seconds: int = 15):
        self.cooldown_seconds = cooldown_seconds
        # Stores hash of "camera_id, object_class, risk_severity" -> last_alert_time
        self._recent_alerts: Dict[str, float] = {}

    def _generate_incident_hash(self, camera_id: str, zone_id: Optional[str], event_type: str) -> str:
        """
        Groups similar events occurring in exact location into one unified incident tracker.
        """
        raw = f"{camera_id}_{zone_id or 'none'}_{event_type}"
        return hashlib.md5(raw.encode()).hexdigest()

    def should_trigger_alert(self, camera_id: str, zone_id: Optional[str], event_type: str, severity: str) -> bool:
        """
        Determines if this event deserves a fresh UI alert or if it's part of an ongoing incident.
        """
        incident_hash = self._generate_incident_hash(camera_id, zone_id, event_type)
        now = time.time()
        
        last_time = self._recent_alerts.get(incident_hash, 0.0)
        
        # Critical severity bypasses normal cooldown entirely, or uses a tiny one
        effective_cooldown = 2 if severity == "CRITICAL" else self.cooldown_seconds
        
        if now - last_time > effective_cooldown:
            self._recent_alerts[incident_hash] = now
            return True
            
        return False
        
    def cleanup(self):
        """
        Prunes old memory to prevent dict growth over months of runtime.
        """
        now = time.time()
        stale_keys = [k for k, v in self._recent_alerts.items() if now - v > (self.cooldown_seconds * 2)]
        for k in stale_keys:
            del self._recent_alerts[k]

alert_engine = AlertEngine()
