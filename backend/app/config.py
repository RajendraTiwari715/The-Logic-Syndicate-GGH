from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_DIR / "data"
EVENTS_DIR = DATA_DIR / "events"
UPLOADS_DIR = DATA_DIR / "uploads"


class Settings(BaseSettings):
    camera_source: str = "0"
    default_camera_id: str = "BOP-01"
    default_camera_name: str = "Primary Command Camera"
    default_bop: str = "BOP Alpha"
    default_location: str = "Sector 1 — Live Feed"
    default_coords_x: float = 18.0
    default_coords_y: float = 22.0
    default_map_lat: float = 28.05
    default_map_lng: float = 81.12

    database_url: str = Field(
        default=f"sqlite:///{(DATA_DIR / 'ibvap_ai.db').as_posix()}",
    )
    model_path: str | None = None
    confidence_threshold: float = 0.4
    image_size: int = 640
    max_fps: int = 12
    process_every_n_frames: int = 2
    loitering_threshold: int = 60
    alert_cooldown_seconds: int = 45
    reconnect_delay_seconds: int = 3
    night_start: str = "22:00"
    night_end: str = "05:00"

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_base_url: str = "http://127.0.0.1:8000"
    allowed_origins: str = "http://127.0.0.1:5173,http://localhost:5173"

    snapshot_dir: str = str(EVENTS_DIR)
    upload_dir: str = str(UPLOADS_DIR)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @property
    def camera_source_value(self) -> int | str:
        return int(self.camera_source) if self.camera_source.isdigit() else self.camera_source


settings = Settings()

Path(settings.snapshot_dir).mkdir(parents=True, exist_ok=True)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
