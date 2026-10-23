from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import cv2
import numpy as np
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.database.models import AlertModel, CameraModel, DetectionModel, EventModel, TrackingModel, ZoneModel
from app.services.snapshot_store import SnapshotStore
from app.vision.detector import DetectionObservation, YoloTrackingDetector
from app.vision.risk_engine import RiskEngine, RiskSignals
from app.vision.tracker import TrackRegistry, TrackState
from app.vision.zones import bbox_bottom_center, crossed_line, percent_points_to_pixels, point_in_polygon
from app.websocket.manager import WebSocketManager


def utcnow() -> datetime:
    return datetime.utcnow()


def to_time_label(value: datetime) -> str:
    return value.strftime("%I:%M:%S %p")


def safe_json_loads(raw: str, default: Any) -> Any:
    try:
        return json.loads(raw)
    except Exception:
        return default


class CameraWorker:
    def __init__(
        self,
        camera_id: str,
        session_factory: sessionmaker[Session],
        websocket_manager: WebSocketManager,
        risk_engine: RiskEngine,
    ) -> None:
        self.camera_id = camera_id
        self.session_factory = session_factory
        self.websocket_manager = websocket_manager
        self.risk_engine = risk_engine
        self.snapshot_store = SnapshotStore()
        self.registry = TrackRegistry(camera_id)
        self.detector = YoloTrackingDetector()
        self._stop_event = threading.Event()
        self._frame_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name=f"camera-worker-{camera_id}", daemon=True)
        self._latest_frame: bytes | None = None
        self._latest_detections: list[dict] = []
        self._status = "OFFLINE"
        self._reconnect_attempts = 0
        self._alerted_offline = False

    def start(self) -> None:
        if not self._thread.is_alive():
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def latest_frame(self) -> bytes | None:
        with self._frame_lock:
            return self._latest_frame

    def latest_detections(self) -> list[dict]:
        return list(self._latest_detections)

    def _get_camera(self, db: Session) -> CameraModel:
        camera = db.get(CameraModel, self.camera_id)
        if camera is None:
            raise RuntimeError(f"Camera {self.camera_id} no longer exists")
        return camera

    def _open_capture(self, source: str) -> cv2.VideoCapture:
        source_value = int(source) if source.isdigit() else source
        capture = cv2.VideoCapture(source_value)
        capture.set(cv2.CAP_PROP_BUFFERSIZE, 2)
        return capture

    def _store_frame(self, frame: np.ndarray) -> None:
        success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if success:
            with self._frame_lock:
                self._latest_frame = encoded.tobytes()

    def _broadcast(self, payload: dict) -> None:
        self.websocket_manager.broadcast_from_thread(payload)

    def _transition_status(self, db: Session, camera: CameraModel, new_status: str, message: str) -> None:
        old_status = camera.status
        self._status = new_status
        camera.status = new_status
        camera.last_heartbeat = utcnow()
        if new_status == "ONLINE":
            self._alerted_offline = False
        if old_status == new_status:
            return

        event_name = "camera_online" if new_status == "ONLINE" else "camera_offline"
        event_id = f"EVT-{uuid4().hex[:12]}"
        event_time = utcnow()
        event = EventModel(
            id=event_id,
            camera_id=self.camera_id,
            event_type=event_name,
            severity="HIGH" if new_status == "OFFLINE" else "LOW",
            tracking_id="INFRA",
            description=message,
            timestamp=event_time,
            status="NEW",
            risk_score=74 if new_status == "OFFLINE" else 12,
            reasons_json=json.dumps(["Camera disconnected", "Reconnect scheduled"] if new_status == "OFFLINE" else ["Camera stream restored"]),
            payload_json=json.dumps({"camera_id": self.camera_id, "status": new_status}),
        )
        db.add(event)

        payload = {
            "event": event_name,
            "camera_id": self.camera_id,
            "timestamp": event_time.isoformat(),
            "message": message,
        }

        if new_status == "OFFLINE" and not self._alerted_offline:
            alert_id = f"A-{uuid4().hex[:10]}"
            alert = AlertModel(
                id=alert_id,
                event_id=event_id,
                severity="HIGH",
                risk_score=74,
                reason="Camera hardware failure / signal loss",
                reasons_json=json.dumps(["Camera hardware failure", "Signal loss"]),
                status="NEW",
                created_at=event_time,
                camera_id=self.camera_id,
                tracking_id="INFRA",
                title="CAMERA OFFLINE",
                what="Camera went offline",
                where=self.camera_id,
                when_display=to_time_label(event_time),
                object_label="Infrastructure",
                why="Camera hardware failure / signal loss",
                zone=None,
                confidence=100.0,
                snapshot_path=None,
            )
            db.add(alert)
            payload["alert"] = {
                "id": alert_id,
                "title": alert.title,
                "severity": alert.severity,
                "camera_id": alert.camera_id,
            }
            self._alerted_offline = True

        self._broadcast(payload)

    def _upsert_tracking(self, db: Session, track: TrackState) -> None:
        record = db.get(TrackingModel, track.tracking_id)
        history_json = json.dumps(track.history)
        if record is None:
            record = TrackingModel(
                tracking_id=track.tracking_id,
                camera_id=track.camera_id,
                object_class=track.object_class,
                object_type=track.object_type,
                confidence=track.confidence,
                direction=track.direction,
                first_seen=track.first_seen,
                last_seen=track.last_seen,
                status=track.status,
                duration_seconds=track.duration_seconds,
                history_json=history_json,
            )
            db.add(record)
            return

        record.camera_id = track.camera_id
        record.object_class = track.object_class
        record.object_type = track.object_type
        record.confidence = track.confidence
        record.direction = track.direction
        record.first_seen = track.first_seen
        record.last_seen = track.last_seen
        record.status = track.status
        record.duration_seconds = track.duration_seconds
        record.history_json = history_json

    def _persist_detection(self, db: Session, track: TrackState, detection: dict, timestamp: datetime) -> None:
        record = DetectionModel(
            id=f"DET-{uuid4().hex[:12]}",
            camera_id=self.camera_id,
            object_class=detection["label"].lower(),
            object_type=detection["objectType"],
            tracking_id=track.tracking_id,
            confidence=detection["confidence"] / 100.0,
            bbox_x=detection["bbox"]["x"],
            bbox_y=detection["bbox"]["y"],
            bbox_w=detection["bbox"]["w"],
            bbox_h=detection["bbox"]["h"],
            direction=track.direction,
            first_seen=track.first_seen,
            last_seen=track.last_seen,
            timestamp=timestamp,
            snapshot_path=None,
        )
        db.add(record)

    def _create_detection_event(self, db: Session, track: TrackState, detection: dict, timestamp: datetime) -> None:
        event_id = f"EVT-{uuid4().hex[:12]}"
        event = EventModel(
            id=event_id,
            camera_id=self.camera_id,
            event_type="detection_created",
            severity="LOW",
            tracking_id=track.tracking_id,
            description=f"{track.object_class.title()} detected on {self.camera_id}",
            timestamp=timestamp,
            status="NEW",
            risk_score=18,
            reasons_json=json.dumps([f"{track.object_class.title()} detected"]),
            payload_json=json.dumps(detection),
        )
        db.add(event)
        self._broadcast(
            {
                "event": "detection_created",
                "camera_id": self.camera_id,
                "tracking_id": track.tracking_id,
                "object_type": track.object_type,
                "object_class": track.object_class,
                "confidence": detection["confidence"] / 100.0,
                "timestamp": timestamp.isoformat(),
            }
        )

    def _create_zone_alert(
        self,
        db: Session,
        track: TrackState,
        zone: ZoneModel,
        event_type: str,
        evaluation_score: int,
        evaluation_severity: str,
        reasons: list[str],
        timestamp: datetime,
        frame: np.ndarray,
    ) -> None:
        event_id = f"EVT-{uuid4().hex[:12]}"
        alert_id = f"A-{uuid4().hex[:10]}"
        snapshot_path = self.snapshot_store.save(frame, self.camera_id, event_type) if evaluation_severity == "CRITICAL" else None

        title = "POSSIBLE BORDER INTRUSION" if event_type == "intrusion_detected" else "SUSPICIOUS LOITERING"
        description = (
            f"Person {track.tracking_id} crossed the configured boundary at {zone.name}"
            if event_type == "intrusion_detected"
            else f"Person {track.tracking_id} remained inside {zone.name}"
        )

        event = EventModel(
            id=event_id,
            camera_id=self.camera_id,
            event_type=event_type,
            severity=evaluation_severity,
            tracking_id=track.tracking_id,
            description=description,
            timestamp=timestamp,
            status="NEW",
            risk_score=evaluation_score,
            reasons_json=json.dumps(reasons),
            snapshot_path=snapshot_path,
            payload_json=json.dumps(
                {
                    "camera_id": self.camera_id,
                    "tracking_id": track.tracking_id,
                    "object_type": track.object_type,
                    "zone": zone.name,
                    "severity": evaluation_severity.lower(),
                    "risk_score": evaluation_score,
                    "reasons": reasons,
                }
            ),
        )
        alert = AlertModel(
            id=alert_id,
            event_id=event_id,
            severity=evaluation_severity,
            risk_score=evaluation_score,
            reason=" + ".join(reasons),
            reasons_json=json.dumps(reasons),
            status="NEW",
            created_at=timestamp,
            camera_id=self.camera_id,
            tracking_id=track.tracking_id,
            title=title,
            what=description,
            where=f"{self.camera_id} / {zone.name}",
            when_display=to_time_label(timestamp),
            object_label=f"{track.object_class.title()} / {track.tracking_id}",
            why=" + ".join(reasons),
            zone=zone.name,
            confidence=round(track.confidence * 100, 1),
            snapshot_path=snapshot_path,
        )
        db.add(event)
        db.add(alert)
        self._broadcast(
            {
                "event": event_type,
                "camera_id": self.camera_id,
                "tracking_id": track.tracking_id,
                "object_type": track.object_type,
                "zone": zone.name,
                "severity": evaluation_severity.lower(),
                "risk_score": evaluation_score,
                "reasons": reasons,
                "snapshot_path": snapshot_path,
                "timestamp": timestamp.isoformat(),
            }
        )

    def _cooldown_ready(self, track: TrackState, zone_id: str, event_name: str, timestamp: datetime) -> bool:
        runtime = track.zone_states[zone_id]
        last_emitted = runtime.cooldowns.get(event_name)
        if last_emitted and (timestamp - last_emitted).total_seconds() < settings.alert_cooldown_seconds:
            return False
        runtime.cooldowns[event_name] = timestamp
        return True

    def _evaluate_zones(self, db: Session, zones: list[ZoneModel], track: TrackState, timestamp: datetime, frame: np.ndarray) -> None:
        if track.object_class != "person":
            return

        height, width = frame.shape[:2]
        x1, y1, x2, y2 = track.bbox_xyxy
        point = bbox_bottom_center(x1, y1, x2, y2)
        night_time = self.risk_engine.is_night_time(timestamp)

        for zone in zones:
            points = percent_points_to_pixels(safe_json_loads(zone.coordinates_json, []), width, height)
            if len(points) < 2:
                continue

            runtime = track.zone_states.setdefault(zone.id, type(track.zone_states.setdefault(zone.id, None))() if False else None)
            if runtime is None:
                from app.vision.tracker import ZoneRuntimeState

                runtime = ZoneRuntimeState()
                track.zone_states[zone.id] = runtime

            if zone.zone_type.lower() == "tripwire" or len(points) == 2:
                crossed = crossed_line(runtime.last_point, point, points[:2])
                runtime.last_point = point
                if crossed and self._cooldown_ready(track, zone.id, "intrusion_detected", timestamp):
                    evaluation = self.risk_engine.evaluate(
                        RiskSignals(
                            object_class="person",
                            zone_name=zone.name,
                            restricted_zone=True,
                            fence_crossed=True,
                            night_time=night_time,
                        )
                    )
                    self._create_zone_alert(
                        db,
                        track,
                        zone,
                        "intrusion_detected",
                        evaluation.score,
                        evaluation.severity,
                        evaluation.reasons,
                        timestamp,
                        frame,
                    )
                continue

            inside = point_in_polygon(point, points)
            if inside and not runtime.inside:
                runtime.inside = True
                runtime.entered_at = timestamp
                if self._cooldown_ready(track, zone.id, "intrusion_detected", timestamp):
                    evaluation = self.risk_engine.evaluate(
                        RiskSignals(
                            object_class="person",
                            zone_name=zone.name,
                            restricted_zone=True,
                            night_time=night_time,
                        )
                    )
                    self._create_zone_alert(
                        db,
                        track,
                        zone,
                        "intrusion_detected",
                        evaluation.score,
                        evaluation.severity,
                        evaluation.reasons,
                        timestamp,
                        frame,
                    )
            elif inside and runtime.entered_at is not None:
                dwell = (timestamp - runtime.entered_at).total_seconds()
                if dwell >= settings.loitering_threshold and self._cooldown_ready(track, zone.id, "loitering_detected", timestamp):
                    evaluation = self.risk_engine.evaluate(
                        RiskSignals(
                            object_class="person",
                            zone_name=zone.name,
                            restricted_zone=True,
                            loitering=True,
                            night_time=night_time,
                        )
                    )
                    self._create_zone_alert(
                        db,
                        track,
                        zone,
                        "loitering_detected",
                        evaluation.score,
                        evaluation.severity,
                        evaluation.reasons,
                        timestamp,
                        frame,
                    )
            else:
                runtime.inside = False
                runtime.entered_at = None

    def _make_detection_payload(
        self,
        observation: DetectionObservation,
        track: TrackState,
        frame_width: int,
        frame_height: int,
        timestamp: datetime,
    ) -> dict:
        x1, y1, x2, y2 = observation.bbox_xyxy
        return {
            "id": f"DET-{track.tracking_id}-{int(timestamp.timestamp() * 1000)}",
            "cameraId": self.camera_id,
            "objectType": observation.object_type,
            "trackingId": track.tracking_id,
            "confidence": round(observation.confidence * 100, 1),
            "timestamp": timestamp.isoformat(),
            "bbox": {
                "x": round(max(0.0, min(100.0, x1 / frame_width * 100)), 2),
                "y": round(max(0.0, min(100.0, y1 / frame_height * 100)), 2),
                "w": round(max(0.0, min(100.0, (x2 - x1) / frame_width * 100)), 2),
                "h": round(max(0.0, min(100.0, (y2 - y1) / frame_height * 100)), 2),
            },
            "label": observation.object_class.upper(),
            "direction": track.direction,
        }

    def _update_camera_metrics(self, db: Session, camera: CameraModel, fps: float, latency_ms: float, detection_count: int) -> None:
        camera.status = "ONLINE"
        camera.fps = round(fps, 2)
        camera.latency = round(latency_ms, 2)
        camera.signal_quality = 100.0
        camera.health = max(20.0, min(99.0, 100.0 - latency_ms * 0.15 - self._reconnect_attempts * 3))
        camera.last_heartbeat = utcnow()
        camera.recording = 1
        camera.reconnect_attempts = self._reconnect_attempts
        camera.detection_count += detection_count

    def _run(self) -> None:
        while not self._stop_event.is_set():
            with self.session_factory() as db:
                camera = self._get_camera(db)
                capture = self._open_capture(camera.source)

                if not capture.isOpened():
                    self._reconnect_attempts += 1
                    self._transition_status(db, camera, "OFFLINE", f"{self.camera_id} is unavailable. Retrying connection.")
                    db.commit()
                    capture.release()
                    time.sleep(settings.reconnect_delay_seconds)
                    continue

                self._transition_status(db, camera, "ONLINE", f"{self.camera_id} stream connected.")
                db.commit()
                frame_index = 0
                fps_window_start = time.perf_counter()
                fps_window_frames = 0

                while not self._stop_event.is_set():
                    ok, frame = capture.read()
                    if not ok or frame is None:
                        self._reconnect_attempts += 1
                        self._transition_status(db, camera, "OFFLINE", f"{self.camera_id} stream disconnected. Reconnecting.")
                        db.commit()
                        capture.release()
                        break

                    frame_index += 1
                    fps_window_frames += 1
                    self._store_frame(frame)

                    if frame_index % max(settings.process_every_n_frames, 1) != 0:
                        continue

                    started = time.perf_counter()
                    timestamp = utcnow()
                    detections = self.detector.infer(frame)
                    latency_ms = (time.perf_counter() - started) * 1000.0

                    active_tracking_ids: set[str] = set()
                    frame_payload: list[dict] = []
                    zones = db.query(ZoneModel).filter(ZoneModel.camera_id == self.camera_id).all()
                    frame_height, frame_width = frame.shape[:2]

                    for observation in detections:
                        track, is_new = self.registry.update(
                            raw_track_id=observation.raw_track_id,
                            object_class=observation.object_class,
                            object_type=observation.object_type,
                            confidence=observation.confidence,
                            bbox_xyxy=observation.bbox_xyxy,
                            timestamp=timestamp,
                        )
                        active_tracking_ids.add(track.tracking_id)
                        payload = self._make_detection_payload(observation, track, frame_width, frame_height, timestamp)
                        frame_payload.append(payload)
                        self._persist_detection(db, track, payload, timestamp)
                        self._upsert_tracking(db, track)
                        if is_new:
                            self._create_detection_event(db, track, payload, timestamp)
                        self._evaluate_zones(db, zones, track, timestamp, frame)

                    self.registry.mark_missing(active_tracking_ids, timestamp)
                    for track in self.registry.list_tracks():
                        self._upsert_tracking(db, track)

                    fps_elapsed = max(time.perf_counter() - fps_window_start, 0.001)
                    fps = fps_window_frames / fps_elapsed
                    self._update_camera_metrics(db, camera, fps, latency_ms, len(frame_payload))
                    self._latest_detections = frame_payload
                    db.commit()

                    self._broadcast(
                        {
                            "event": "frame_state",
                            "camera_id": self.camera_id,
                            "timestamp": timestamp.isoformat(),
                            "detections": frame_payload,
                        }
                    )

                    if fps_elapsed >= 1.0:
                        fps_window_start = time.perf_counter()
                        fps_window_frames = 0

            time.sleep(settings.reconnect_delay_seconds)


class CameraManager:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        websocket_manager: WebSocketManager,
        risk_engine: RiskEngine,
    ) -> None:
        self.session_factory = session_factory
        self.websocket_manager = websocket_manager
        self.risk_engine = risk_engine
        self._workers: dict[str, CameraWorker] = {}

    @staticmethod
    def detect_source_type(source: str) -> str:
        if source.isdigit():
            return "webcam"
        if source.startswith("rtsp://") or source.startswith("rtsps://"):
            return "rtsp"
        if Path(source).exists():
            return "video_file"
        return "stream"

    def bootstrap(self) -> None:
        with self.session_factory() as db:
            cameras = db.query(CameraModel).all()
            if not cameras:
                default_camera = CameraModel(
                    id=settings.default_camera_id,
                    name=settings.default_camera_name,
                    bop=settings.default_bop,
                    location=settings.default_location,
                    source=str(settings.camera_source),
                    source_type=self.detect_source_type(str(settings.camera_source)),
                    status="OFFLINE",
                    fps=0.0,
                    latency=0.0,
                    storage=0.0,
                    health=0.0,
                    signal_quality=0.0,
                    scenario="normal",
                    recording=1,
                    detection_count=0,
                    coords_x=settings.default_coords_x,
                    coords_y=settings.default_coords_y,
                    map_lat=settings.default_map_lat,
                    map_lng=settings.default_map_lng,
                )
                db.add(default_camera)
                db.commit()
                cameras = [default_camera]

            for camera in cameras:
                self.start_camera(camera.id)

    def stop_all(self) -> None:
        for worker in list(self._workers.values()):
            worker.stop()
        self._workers.clear()

    def start_camera(self, camera_id: str) -> None:
        if camera_id in self._workers:
            return
        worker = CameraWorker(
            camera_id=camera_id,
            session_factory=self.session_factory,
            websocket_manager=self.websocket_manager,
            risk_engine=self.risk_engine,
        )
        self._workers[camera_id] = worker
        worker.start()

    def restart_camera(self, camera_id: str) -> None:
        worker = self._workers.pop(camera_id, None)
        if worker is not None:
            worker.stop()
        self.start_camera(camera_id)

    def latest_frame(self, camera_id: str) -> bytes | None:
        worker = self._workers.get(camera_id)
        if worker is None:
            return None
        return worker.latest_frame()

    def latest_detections(self, camera_id: str) -> list[dict]:
        worker = self._workers.get(camera_id)
        if worker is None:
            return []
        return worker.latest_detections()
