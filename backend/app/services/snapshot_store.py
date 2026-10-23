from __future__ import annotations
import hashlib
import io
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple, Optional, Any

import cv2
import numpy as np
from minio.error import S3Error

from app.core.config import settings
from app.core.storage import storage_client

logger = logging.getLogger(__name__)

class EvidenceStorageService:
    def __init__(self) -> None:
        self.bucket_name = "evidence"
        self.local_fallback_dir = Path("data/evidence_cache")
        self.local_fallback_dir.mkdir(parents=True, exist_ok=True)
        self._bucket_checked = False

    def _ensure_bucket(self):
        if self._bucket_checked: return
        client = storage_client.get_client()
        if client:
            try:
                if not client.bucket_exists(self.bucket_name):
                    client.make_bucket(self.bucket_name)
                self._bucket_checked = True
            except Exception as e:
                logger.warning(f"Could not initialize MinIO bucket '{self.bucket_name}': {e}")
        else:
            # Mark checked so we don't infinitely retry if client connection is totally failed
            self._bucket_checked = True

    def upload_evidence(self, frame: np.ndarray, camera_id: str, label: str) -> Optional[Tuple[str, str, int]]:
        """
        Saves a video frame to MinIO storage and calculates its SHA-256 cryptographic hash.
        Ensures digital chain-of-custody for the Intelligence interface.
        Returns: (file_url, sha256_hash, file_size_bytes)
        """
        self._ensure_bucket()
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        filename = f"{camera_id}_{label}_{timestamp}.jpg"
        
        success, encoded_image = cv2.imencode('.jpg', frame)
        if not success:
            return None
            
        byte_buffer = encoded_image.tobytes()
        file_size = len(byte_buffer)
        sha256_hash = hashlib.sha256(byte_buffer).hexdigest()
        
        client = storage_client.get_client()
        if client:
            try:
                client.put_object(
                    self.bucket_name,
                    filename,
                    io.BytesIO(byte_buffer),
                    length=file_size,
                    content_type="image/jpeg"
                )
                url = f"/api/v1/stream/evidence/{filename}" # typically served via proxy or presigned url
                return url, sha256_hash, file_size
            except S3Error as e:
                logger.error(f"MinIO PutObject failed: {e}")
            except Exception as e:
                logger.error(f"Storage error: {e}")

        # Edge Fallback Strategy (when Central/MinIO is unreachable)
        output_path = self.local_fallback_dir / filename
        with open(output_path, "wb") as f:
            f.write(byte_buffer)
        
        url = f"/api/v1/stream/evidence/local/{filename}"
        return url, sha256_hash, file_size

    def download_evidence(self, filename: str) -> Optional[bytes]:
        self._ensure_bucket()
        client = storage_client.get_client()
        if client:
            try:
                response = client.get_object(self.bucket_name, filename)
                return response.read()
            except Exception as e:
                logger.error(f"Download failed from MinIO: {e}")
                
        # Fallback check
        local_path = self.local_fallback_dir / filename
        if local_path.exists():
            return local_path.read_bytes()
            
        return None

    def exists(self, filename: str) -> bool:
        self._ensure_bucket()
        client = storage_client.get_client()
        if client:
            try:
                client.stat_object(self.bucket_name, filename)
                return True
            except Exception:
                pass
        return (self.local_fallback_dir / filename).exists()

    def verify_integrity(self, filename: str, expected_hash: str) -> str:
        data = self.download_evidence(filename)
        if not data:
            return "NOT_FOUND"
        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash == expected_hash:
            return "VERIFIED"
        return "INTEGRITY_FAILURE"

evidence_storage = EvidenceStorageService()
