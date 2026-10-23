from minio import Minio
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class StorageClient:
    def __init__(self):
        self.client = None
    
    def connect(self):
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ROOT_USER,
                secret_key=settings.MINIO_ROOT_PASSWORD,
                secure=settings.MINIO_SECURE
            )
            logger.info("Connected to MinIO")
        except Exception as e:
            logger.error(f"Failed to connect to MinIO: {e}")

    def is_healthy(self) -> bool:
        if not self.client:
            self.connect()
        if not self.client:
            return False
        try:
            self.client.list_buckets()
            return True
        except Exception:
            return False

    @property
    def minio(self):
        if not self.client:
            self.connect()
        return self.client

    def get_client(self):
        if not self.client:
            self.connect()
        return self.client

storage_client = StorageClient()
