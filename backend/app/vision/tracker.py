from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(slots=True)
class ZoneRuntimeState:
    inside: bool = False
    entered_at: datetime | None = None
    last_point: tuple[float, float] | None = None
    cooldowns: dict[str, datetime] = field(default_factory=dict)


@dataclass(slots=True)
class TrackState:
    raw_key: str
    tracking_id: str
    camera_id: str
    object_class: str
    object_type: str
    first_seen: datetime
    last_seen: datetime
    confidence: float
    bbox_xyxy: tuple[float, float, float, float]
    direction: str = "Stationary"
    status: str = "Active"
    history: list[dict[str, str]] = field(default_factory=list)
    zone_states: dict[str, ZoneRuntimeState] = field(default_factory=dict)
    last_center: tuple[float, float] | None = None
    velocity: tuple[float, float] = (0.0, 0.0)
    exit_boundary: str | None = None

    @property
    def speed_units_per_sec(self) -> float:
        return (self.velocity[0]**2 + self.velocity[1]**2) ** 0.5

    @property
    def duration_seconds(self) -> float:
        return max((self.last_seen - self.first_seen).total_seconds(), 0.0)


class TrackRegistry:
    def __init__(self, camera_id: str) -> None:
        self.camera_id = camera_id
        self._mapping: dict[str, str] = {}
        self._tracks: dict[str, TrackState] = {}
        self._person_counter = 100
        self._vehicle_counter = 20
        self._fallback_counter = 0

    def _allocate_tracking_id(self, object_type: str) -> str:
        if object_type == "person":
            self._person_counter += 1
            return f"P-{self._person_counter:03d}"
        self._vehicle_counter += 1
        return f"V-{self._vehicle_counter:03d}"

    @staticmethod
    def _to_direction(previous_center: tuple[float, float] | None, current_center: tuple[float, float]) -> str:
        if previous_center is None:
            return "Stationary"
        dx = current_center[0] - previous_center[0]
        dy = current_center[1] - previous_center[1]
        if abs(dx) < 2 and abs(dy) < 2:
            return "Stationary"
        horizontal = "East" if dx > 0 else "West"
        vertical = "South" if dy > 0 else "North"
        if abs(dx) < 4:
            return vertical
        if abs(dy) < 4:
            return horizontal
        return f"{vertical}-{horizontal}"

    def update(
        self,
        raw_track_id: int | None,
        object_class: str,
        object_type: str,
        confidence: float,
        bbox_xyxy: tuple[float, float, float, float],
        timestamp: datetime,
    ) -> tuple[TrackState, bool]:
        if raw_track_id is None:
            self._fallback_counter += 1
            raw_key = f"fallback:{object_class}:{self._fallback_counter}"
        else:
            raw_key = f"{object_type}:{int(raw_track_id)}"

        tracking_id = self._mapping.get(raw_key)
        is_new = False
        if tracking_id is None:
            tracking_id = self._allocate_tracking_id(object_type)
            self._mapping[raw_key] = tracking_id
            is_new = True

        center = ((bbox_xyxy[0] + bbox_xyxy[2]) / 2.0, bbox_xyxy[3])
        track = self._tracks.get(tracking_id)
        if track is None:
            track = TrackState(
                raw_key=raw_key,
                tracking_id=tracking_id,
                camera_id=self.camera_id,
                object_class=object_class,
                object_type=object_type,
                first_seen=timestamp,
                last_seen=timestamp,
                confidence=confidence,
                bbox_xyxy=bbox_xyxy,
                history=[{"cameraId": self.camera_id, "time": timestamp.isoformat()}],
                last_center=center,
            )
            self._tracks[tracking_id] = track
            return track, True

        if track.last_center:
            dt = max((timestamp - track.last_seen).total_seconds(), 0.05)
            vx = (center[0] - track.last_center[0]) / dt
            vy = (center[1] - track.last_center[1]) / dt
            # Exponential moving average smooths jitter
            track.velocity = (track.velocity[0] * 0.7 + vx * 0.3, track.velocity[1] * 0.7 + vy * 0.3)

            # Frame boundary exit logic (assuming generic 1280x720 frame bounds if unknown, checking outer 5%)
            if center[0] > 1200: track.exit_boundary = "East"
            elif center[0] < 80: track.exit_boundary = "West"
            elif center[1] > 680: track.exit_boundary = "South"
            elif center[1] < 40: track.exit_boundary = "North"
            else: track.exit_boundary = None

        track.direction = self._to_direction(track.last_center, center)
        track.last_center = center
        track.last_seen = timestamp
        track.confidence = confidence
        track.bbox_xyxy = bbox_xyxy
        track.status = "Active"
        if not track.history or track.history[-1]["time"] != timestamp.isoformat():
            track.history.append({"cameraId": self.camera_id, "time": timestamp.isoformat()})
            track.history = track.history[-10:]
        return track, is_new

    def mark_missing(self, active_ids: set[str], timestamp: datetime) -> None:
        for tracking_id, track in self._tracks.items():
            if tracking_id not in active_ids:
                age_seconds = (timestamp - track.last_seen).total_seconds()
                if age_seconds > 8:
                    track.status = "Exited"
                elif age_seconds > 3:
                    track.status = "Lost"

    def list_tracks(self) -> list[TrackState]:
        return sorted(self._tracks.values(), key=lambda track: track.last_seen, reverse=True)
