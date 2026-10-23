from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid

def generate_uuid() -> str:
    return uuid.uuid4().hex[:12].upper()

class BaseDetection(BaseModel):
    """
    Unified detection schema preventing tight coupling to YOLO classes.
    """
    id: str = Field(default_factory=lambda: f"DET-{generate_uuid()}")
    camera_id: str
    object_class: str
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class BaseTrack(BaseModel):
    """
    Unified tracking schema indicating object state historically.
    """
    track_id: str
    camera_id: str
    object_class: str
    confidence: float
    bbox_xyxy: tuple[int, int, int, int]
    center_xy: tuple[int, int]
    velocity_xy: Optional[tuple[float, float]] = None
    first_seen: datetime
    last_seen: datetime
    duration_ms: int = 0
    zone_id: Optional[str] = None
    direction: Optional[str] = None
    
    @property
    def dwell_time_seconds(self) -> float:
        return max(0.1, (self.last_seen - self.first_seen).total_seconds())

class StandardizedEvent(BaseModel):
    """
    Final generic event object ready for persistence and WebSocket broadcasts, 
    decoupled from raw model outputs.
    """
    event_id: str = Field(default_factory=lambda: f"EVT-{generate_uuid()}")
    event_type: str  # EX: 'SUSPICIOUS_MOVEMENT', 'INTRUSION', 'WATCHLIST_MATCH'
    camera_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    track_id: Optional[str] = None
    object_class: Optional[str] = None
    confidence: float = 0.0
    zone_id: Optional[str] = None
    severity: str = "LOW"  # LOW, WARNING, CRITICAL
    risk_score: float = 0.0
    risk_factors: List[str] = Field(default_factory=list)
    evidence_id: Optional[str] = None
    status: str = "NEW"
    model_version: str = "yolov8n-IBVAP-v1"
    details: Dict[str, Any] = Field(default_factory=dict)
