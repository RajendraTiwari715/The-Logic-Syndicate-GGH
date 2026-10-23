import secrets
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load from .env if present
load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parents[2]
LOCAL_SQLITE_URL = f"sqlite:///{(BACKEND_DIR / 'data' / 'ibvap_ai.db').as_posix()}"

class Settings(BaseSettings):
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "AssistanCCTV AI Backend")
    API_V1_STR: str = os.getenv("API_V1_STR", "/api/v1")
    # In production, change this to a secure random string
    SECRET_KEY: str = os.getenv("JWT_SECRET", "super_secret_for_cctv_project")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    
    # Authoritative store
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", LOCAL_SQLITE_URL)

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # MinIO
    MINIO_ENDPOINT: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    MINIO_ROOT_USER: str = os.getenv("MINIO_ROOT_USER", "admin")
    MINIO_ROOT_PASSWORD: str = os.getenv("MINIO_ROOT_PASSWORD", "admin12345")
    MINIO_SECURE: bool = os.getenv("MINIO_SECURE", "False").lower() in ("true", "1", "yes")

    class Config:
        case_sensitive = True

settings = Settings()
