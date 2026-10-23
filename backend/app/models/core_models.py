import enum
import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
from datetime import datetime

def generate_uuid():
    return str(uuid.uuid4())

class CameraStatus(str, enum.Enum):
    LIVE = "LIVE"
    DEGRADED = "DEGRADED"
    DISCONNECTED = "DISCONNECTED"
    ERROR = "ERROR"
    MAINTENANCE = "MAINTENANCE"

class EventType(str, enum.Enum):
    HUMAN_DETECTED = "HUMAN_DETECTED"
    VEHICLE_DETECTED = "VEHICLE_DETECTED"
    FACE_DETECTED = "FACE_DETECTED"
    PLATE_DETECTED = "PLATE_DETECTED"
    RESTRICTED_ZONE_INTRUSION = "RESTRICTED_ZONE_INTRUSION"
    LOITERING = "LOITERING"
    WRONG_DIRECTION = "WRONG_DIRECTION"
    NIGHT_MOVEMENT = "NIGHT_MOVEMENT"
    WATCHLIST_MATCH = "WATCHLIST_MATCH"
    SUSPICIOUS_ACTIVITY = "SUSPICIOUS_ACTIVITY"
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    AI_SERVICE_FAILURE = "AI_SERVICE_FAILURE"
    NETWORK_FAILURE = "NETWORK_FAILURE"

class AlertState(str, enum.Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    VERIFIED = "VERIFIED"
    DISMISSED = "DISMISSED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"

class Severity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class Camera(Base):
    __tablename__ = "cameras"
    
    # Extended ID mechanism but keeping backward compatibility shape
    id = Column(String(50), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(100))
    bop = Column(String(100)) # e.g. site/BOP
    location = Column(String(200))
    status = Column(String(20), default=CameraStatus.DISCONNECTED) # ONLINE, OFFLINE, LIVE...
    fps = Column(Integer, default=30)
    latency = Column(Integer, default=20)
    storage = Column(Integer, default=100)
    health = Column(Integer, default=100)
    lastHeartbeat = Column(String(50))
    signalQuality = Column(Integer, default=100)
    scenario = Column(String(50), default="normal")
    recording = Column(Boolean, default=True)
    detectionCount = Column(Integer, default=0)
    coords = Column(JSON, nullable=True) # {x, y}
    mapCoord = Column(JSON, nullable=True) # {lat, lng}
    
    # New IBVAP fields
    rtsp_url = Column(String(512), nullable=True)
    protocol = Column(String(20), default="RTSP")
    credentials_ref = Column(String(100), nullable=True)
    resolution = Column(String(20), default="1920x1080")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Unified Architecture
    camera_mode = Column(String(50), default="ALL")
    profile = Column(String(50), default="GENERAL")
    thermal_enabled = Column(Boolean, default=False)


class EventItem(Base):
    __tablename__ = "events"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    eventType = Column(String(100))
    severity = Column(String(20)) # LOW, MEDIUM, HIGH, CRITICAL
    trackingId = Column(String(100), nullable=True)
    description = Column(String(255))
    timestamp = Column(String(50), nullable=True) # For backward compatibility
    event_timestamp = Column(DateTime(timezone=True), server_default=func.now()) # Proper PG format
    status = Column(String(20)) 
    riskScore = Column(Integer, default=0)
    reasons = Column(JSON, nullable=True) # Array of strings / details
    confidence = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    camera = relationship("Camera")

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    eventId = Column(String(100), ForeignKey("events.id"), nullable=True)
    severity = Column(String(20))
    riskScore = Column(Integer, default=0)
    reason = Column(String(255))
    reasons = Column(JSON, nullable=True)
    status = Column(String(20), default=AlertState.NEW)
    createdAt = Column(String(50), nullable=True)
    created_at_dt = Column(DateTime(timezone=True), server_default=func.now())
    acknowledgedAt = Column(String(50), nullable=True)
    resolvedAt = Column(String(50), nullable=True)
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    trackingId = Column(String(100), nullable=True)
    title = Column(String(150))
    what = Column(String(150))
    where = Column(String(150), nullable=True)
    when_time = Column(String(100), nullable=True) 
    object = Column(String(100), nullable=True)
    why = Column(String(255), nullable=True)
    zone = Column(String(100), nullable=True)
    confidence = Column(Integer, default=100)
    acknowledged_by = Column(String(100), nullable=True) # user mapping
    event = relationship("EventItem", foreign_keys=[eventId])


class VehicleRecord(Base):
    __tablename__ = "vehicles"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    vehicleType = Column(String(50))
    plateNumber = Column(String(50))
    confidence = Column(Integer)
    timestamp = Column(String(50))
    status = Column(String(30)) # AUTHORIZED, WATCHLIST, UNKNOWN
    direction = Column(String(50), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    entry_count = Column(Integer, default=0)
    normalized_plate = Column(String(50), nullable=True)
    representative_image = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Person(Base):
    __tablename__ = "persons"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    name = Column(String(150), nullable=True)
    image = Column(Text, nullable=True)
    embedding = Column(JSON, nullable=True)
    authorization_status = Column(String(50), default="UNKNOWN") # AUTHORIZED, UNAUTHORIZED, WATCHLIST, UNKNOWN
    category = Column(String(50), nullable=True)
    notes = Column(String(255), nullable=True)
    first_seen = Column(DateTime(timezone=True), nullable=True)
    last_seen = Column(DateTime(timezone=True), nullable=True)
    entry_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class FaceRecord(Base):
    __tablename__ = "faces"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    identity = Column(String(150))
    confidence = Column(Integer)
    timestamp = Column(String(50))
    database = Column(String(50))
    status = Column(String(30)) 
    image = Column(Text, nullable=True)
    direction = Column(String(50), nullable=True)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    cameraIds = Column(JSON) # list of string IDs // legacy
    cameraId = Column(String(50), ForeignKey('cameras.id'), nullable=True) # new single relation
    name = Column(String(150))
    zoneType = Column(String(50))
    severity = Column(String(20))
    coordinates = Column(JSON) # list of {x, y}
    rule = Column(String(255))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WatchlistRecord(Base):
    __tablename__ = "watchlist"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    plate_number = Column(String(50), unique=True, index=True)
    description = Column(String(255), nullable=True)
    added_at = Column(DateTime(timezone=True), server_default=func.now())



class Detection(Base):
    __tablename__ = "detections"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    objectType = Column(String(50))
    trackingId = Column(String(100))
    confidence = Column(Integer)
    timestamp = Column(String(50))
    bbox = Column(JSON) # {x, y, w, h}
    label = Column(String(50))
    direction = Column(String(50), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(100), primary_key=True, index=True, default=generate_uuid)
    user = Column(String(100)) # legacy 
    actor_id = Column(String(36), nullable=True) # user mapping
    action = Column(String(255))
    timestamp = Column(String(50))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(String(500))
    result = Column(String(20))
    ip = Column(String(50))
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(String(100), nullable=True)


class TrackRecord(Base):
    __tablename__ = "tracks"

    trackingId = Column(String(100), primary_key=True, index=True)
    objectType = Column(String(50))
    cameraId = Column(String(50), ForeignKey("cameras.id"))
    direction = Column(String(50), nullable=True)
    duration = Column(String(50), nullable=True)
    status = Column(String(30)) 
    firstSeen = Column(String(50))
    lastSeen = Column(String(50))
    history = Column(JSON) 
    last_position = Column(JSON, nullable=True)
    velocity = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)

# ---- NEW IBVAP SPECIFIC MODELS ----

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(200))
    status = Column(String(20), default="OPEN")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class IncidentEvent(Base):
    __tablename__ = "incident_events"
    id = Column(Integer, primary_key=True, autoincrement=True)
    incident_id = Column(String(36), ForeignKey("incidents.id"))
    event_id = Column(String(100), ForeignKey("events.id"))

class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(100), ForeignKey("events.id"))
    camera_id = Column(String(50), ForeignKey("cameras.id"))
    file_location = Column(String(512))
    file_url = Column(String(512)) # added for compatibility
    file_type = Column(String(50)) # SNAPSHOT, VIDEO_CLIP
    sha256_hash = Column(String(64))
    integrity_status = Column(String(20), default="PENDING") # VERIFIED, INTEGRITY_FAILURE
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class BlockchainLedger(Base):
    __tablename__ = "blockchain_ledger"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    event_id = Column(String(100), ForeignKey("events.id"), nullable=True)
    previous_hash = Column(String(64), nullable=False)
    block_hash = Column(String(64), nullable=False, unique=True, index=True)
    payload_dump = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# ---- TASK 1: REMAINING DB DOMAIN MODELS ----

class CameraCredential(Base):
    __tablename__ = "camera_credentials"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    camera_id = Column(String(50), ForeignKey("cameras.id"))
    username = Column(String(100))
    password = Column(String(255))
    auth_type = Column(String(50), default="BASIC") # BASIC, DIGEST, TOKEN
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ZoneVertex(Base):
    __tablename__ = "zone_vertices"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    zone_id = Column(String(100), ForeignKey("zones.id"))
    order_idx = Column(Integer)
    x = Column(Float)
    y = Column(Float)

class Plate(Base):
    __tablename__ = "plates"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    vehicle_id = Column(String(100), ForeignKey("vehicles.id"), nullable=True)
    camera_id = Column(String(50), ForeignKey("cameras.id"))
    raw_ocr_text = Column(String(100))
    normalized_plate = Column(String(50))
    confidence = Column(Float)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    evidence_id = Column(String(36), ForeignKey("evidence.id"), nullable=True)

class Watchlist(Base):
    __tablename__ = "watchlists"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100))
    type = Column(String(50)) # VEHICLE, FACE
    severity = Column(String(20), default="HIGH")
    created_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class WatchlistEntry(Base):
    __tablename__ = "watchlist_entries"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    watchlist_id = Column(String(36), ForeignKey("watchlists.id"))
    identifier = Column(String(255)) # plate number or face vector ref
    description = Column(String(500))
    added_by = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ModelVersion(Base):
    __tablename__ = "model_versions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    model_type = Column(String(50)) # YOLO, FACE, OCR
    version_tag = Column(String(100))
    file_path = Column(String(255))
    is_active = Column(Boolean, default=False)
    deployed_at = Column(DateTime(timezone=True), server_default=func.now())

class SystemHealth(Base):
    __tablename__ = "system_health"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    component = Column(String(50)) # EDGE_NODE, CENTRAL_DB, REDIS, MINIO
    status = Column(String(20)) # ONLINE, DEGRADED, OFFLINE
    metrics = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

class SyncJob(Base):
    __tablename__ = "sync_jobs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    edge_id = Column(String(100))
    resource_type = Column(String(50))
    resource_id = Column(String(100))
    payload = Column(JSON)
    status = Column(String(20), default="PENDING")
    retry_count = Column(Integer, default=0)
    last_attempt = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(100))
    alert_id = Column(String(100), ForeignKey("alerts.id"), nullable=True)
    message = Column(String(500))
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

