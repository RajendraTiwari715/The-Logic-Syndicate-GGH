from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class CameraModel(Base):
    __tablename__ = "cameras"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    bop: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(String(255))
    source: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(30), default="webcam")
    status: Mapped[str] = mapped_column(String(20), default="OFFLINE")
    fps: Mapped[float] = mapped_column(Float, default=0.0)
    latency: Mapped[float] = mapped_column(Float, default=0.0)
    storage: Mapped[float] = mapped_column(Float, default=0.0)
    health: Mapped[float] = mapped_column(Float, default=0.0)
    last_heartbeat: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    signal_quality: Mapped[float] = mapped_column(Float, default=0.0)
    scenario: Mapped[str] = mapped_column(String(30), default="normal")
    recording: Mapped[int] = mapped_column(Integer, default=1)
    detection_count: Mapped[int] = mapped_column(Integer, default=0)
    coords_x: Mapped[float] = mapped_column(Float, default=20.0)
    coords_y: Mapped[float] = mapped_column(Float, default=20.0)
    map_lat: Mapped[float] = mapped_column(Float, default=28.05)
    map_lng: Mapped[float] = mapped_column(Float, default=81.12)
    reconnect_attempts: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DetectionModel(Base):
    __tablename__ = "detections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(40), index=True)
    object_class: Mapped[str] = mapped_column(String(40))
    object_type: Mapped[str] = mapped_column(String(40))
    tracking_id: Mapped[str] = mapped_column(String(40), index=True)
    confidence: Mapped[float] = mapped_column(Float)
    bbox_x: Mapped[float] = mapped_column(Float)
    bbox_y: Mapped[float] = mapped_column(Float)
    bbox_w: Mapped[float] = mapped_column(Float)
    bbox_h: Mapped[float] = mapped_column(Float)
    direction: Mapped[str | None] = mapped_column(String(60), nullable=True)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class TrackingModel(Base):
    __tablename__ = "tracking_events"

    tracking_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(40), index=True)
    object_class: Mapped[str] = mapped_column(String(40))
    object_type: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(60), default="Stationary")
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(20), default="Active")
    duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    history_json: Mapped[str] = mapped_column(Text, default="[]")


class EventModel(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(40), index=True)
    event_type: Mapped[str] = mapped_column(String(60), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    tracking_id: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    status: Mapped[str] = mapped_column(String(20), default="NEW")
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")


class AlertModel(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), index=True)
    severity: Mapped[str] = mapped_column(String(20))
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    reason: Mapped[str] = mapped_column(Text, default="")
    reasons_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="NEW")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    camera_id: Mapped[str] = mapped_column(String(40), index=True)
    tracking_id: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(160))
    what: Mapped[str] = mapped_column(Text)
    where: Mapped[str] = mapped_column(Text)
    when_display: Mapped[str] = mapped_column(String(80))
    object_label: Mapped[str] = mapped_column(String(120))
    why: Mapped[str] = mapped_column(Text)
    zone: Mapped[str | None] = mapped_column(String(120), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)


class ZoneModel(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    camera_id: Mapped[str] = mapped_column(String(40), index=True)
    name: Mapped[str] = mapped_column(String(120))
    zone_type: Mapped[str] = mapped_column(String(60))
    severity: Mapped[str] = mapped_column(String(20))
    coordinates_json: Mapped[str] = mapped_column(Text, default="[]")
    rule: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLogModel(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    result: Mapped[str] = mapped_column(String(20), default="SUCCESS")
    ip: Mapped[str] = mapped_column(String(80), default="127.0.0.1")

class WatchlistModel(Base):
    __tablename__ = "watchlist"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    plate_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

