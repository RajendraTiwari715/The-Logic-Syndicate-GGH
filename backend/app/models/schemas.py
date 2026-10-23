from __future__ import annotations

from pydantic import BaseModel


class CoordPoint(BaseModel):
    x: float
    y: float


class MapPoint(BaseModel):
    lat: float
    lng: float


class CameraCreateRequest(BaseModel):
    camera_id: str | None = None
    name: str | None = None
    bop: str | None = None
    location: str | None = None
    source: str
    source_type: str | None = None
    coords: CoordPoint | None = None
    map_coord: MapPoint | None = None


class ZoneCreateRequest(BaseModel):
    camera_id: str
    name: str
    zone_type: str
    severity: str
    coordinates: list[CoordPoint]
    rule: str | None = None


class HealthSummary(BaseModel):
    online: int
    offline: int
    degraded: int
    average_health: float


class VideoUploadResponse(BaseModel):
    filename: str
    source_path: str

class WatchlistCreateRequest(BaseModel):
    plate_number: str
    description: str | None = None
