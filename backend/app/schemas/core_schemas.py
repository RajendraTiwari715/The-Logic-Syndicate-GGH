from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Any, Dict
from datetime import datetime

class CameraBase(BaseModel):
    name: str
    bop: Optional[str] = None
    location: Optional[str] = None
    status: str = "DISCONNECTED"
    fps: int = 30
    latency: int = 20
    storage: int = 100
    health: int = 100
    lastHeartbeat: Optional[str] = None
    signalQuality: int = 100
    scenario: str = "normal"
    recording: bool = True
    detectionCount: int = 0
    coords: Optional[Dict[str, float]] = None
    mapCoord: Optional[Dict[str, float]] = None
    
    # New IBVAP Fields
    rtsp_url: Optional[str] = None
    protocol: Optional[str] = "RTSP"
    credentials_ref: Optional[str] = None
    resolution: Optional[str] = "1920x1080"
    camera_mode: Optional[str] = "ALL"

class CameraCreate(CameraBase):
    pass

class Camera(CameraBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class EventItemBase(BaseModel):
    cameraId: str
    eventType: str
    severity: str
    trackingId: Optional[str] = None
    description: str
    timestamp: Optional[str] = None
    status: str
    riskScore: int = 0
    reasons: Optional[List[str]] = []
    confidence: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

class EventItemCreate(EventItemBase):
    pass

class EventItem(EventItemBase):
    id: str
    event_timestamp: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class AlertBase(BaseModel):
    eventId: Optional[str] = None
    severity: str
    riskScore: int = 0
    reason: str
    reasons: Optional[List[str]] = []
    status: str = "NEW"
    createdAt: Optional[str] = None
    acknowledgedAt: Optional[str] = None
    resolvedAt: Optional[str] = None
    cameraId: str
    trackingId: Optional[str] = None
    title: str
    what: str
    where: Optional[str] = None
    when: Optional[str] = None # Maps to when_time in DB model
    object: Optional[str] = None
    why: Optional[str] = None
    zone: Optional[str] = None
    confidence: int = 100
    acknowledged_by: Optional[str] = None

class AlertCreate(AlertBase):
    pass

class Alert(AlertBase):
    id: str
    created_at_dt: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class VehicleRecordBase(BaseModel):
    cameraId: Optional[str] = None
    vehicleType: Optional[str] = None
    plateNumber: str
    confidence: Optional[int] = None
    timestamp: Optional[str] = None
    status: str
    direction: Optional[str] = None

class VehicleRecordCreate(VehicleRecordBase):
    pass

class VehicleRecord(VehicleRecordBase):
    id: str
    image: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class FaceRecordBase(BaseModel):
    cameraId: str
    identity: str
    confidence: int
    timestamp: str
    database: str
    status: str
    image: Optional[str] = None
    direction: Optional[str] = None

class FaceRecordCreate(FaceRecordBase):
    pass

class FaceRecord(FaceRecordBase):
    id: str
    model_config = ConfigDict(from_attributes=True)

class ZoneBase(BaseModel):
    cameraIds: Optional[List[str]] = None
    cameraId: Optional[str] = None
    name: str
    zoneType: str
    severity: str
    coordinates: List[Dict[str, float]]
    rule: str

class ZoneCreate(ZoneBase):
    pass

class Zone(ZoneBase):
    id: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class DetectionBase(BaseModel):
    cameraId: str
    objectType: str
    trackingId: str
    confidence: int
    timestamp: str
    bbox: Dict[str, float]
    label: str
    direction: Optional[str] = None

class DetectionCreate(DetectionBase):
    pass

class Detection(DetectionBase):
    id: str
    model_config = ConfigDict(from_attributes=True)

class AuditLogBase(BaseModel):
    user: Optional[str] = None
    actor_id: Optional[str] = None
    action: str
    timestamp: Optional[str] = None
    details: str
    result: str
    ip: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None

class AuditLogCreate(AuditLogBase):
    pass

class AuditLog(AuditLogBase):
    id: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class TrackRecordBase(BaseModel):
    objectType: str
    cameraId: str
    direction: Optional[str] = None
    duration: Optional[str] = None
    status: str
    firstSeen: str
    lastSeen: str
    history: List[Dict[str, str]]
    last_position: Optional[Dict[str, float]] = None
    velocity: Optional[Dict[str, float]] = None
    confidence: Optional[float] = None

class TrackRecordCreate(TrackRecordBase):
    trackingId: str

class TrackRecord(TrackRecordBase):
    trackingId: str
    model_config = ConfigDict(from_attributes=True)

class IncidentBase(BaseModel):
    title: str
    status: str = "OPEN"

class IncidentCreate(IncidentBase):
    pass

class Incident(IncidentBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class EvidenceBase(BaseModel):
    event_id: str
    camera_id: str
    file_location: str
    file_type: str
    sha256_hash: str
    integrity_status: str = "PENDING"

class EvidenceCreate(EvidenceBase):
    pass

class Evidence(EvidenceBase):
    id: str
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)
    
class WatchlistRecordBase(BaseModel):
    plate_number: str
    description: Optional[str] = None

class WatchlistRecordCreate(WatchlistRecordBase):
    pass

class WatchlistRecord(WatchlistRecordBase):
    id: str
    added_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

