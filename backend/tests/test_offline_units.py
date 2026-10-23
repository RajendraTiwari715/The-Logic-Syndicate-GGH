import os
import pytest
import numpy as np
from unittest.mock import patch
from datetime import datetime
from app.vision.risk_engine import RiskEngine, RiskSignals, score_to_severity
from app.services.snapshot_store import EvidenceStorageService
import hashlib

def test_risk_severity():
    assert score_to_severity(30) == "LOW"
    assert score_to_severity(50) == "MEDIUM"
    assert score_to_severity(80) == "HIGH"
    assert score_to_severity(90) == "CRITICAL"

def test_risk_engine_evaluation():
    engine = RiskEngine()
    signals = RiskSignals(object_class="person", restricted_zone=True, fence_crossed=True)
    evaluation = engine.evaluate(signals)
    assert evaluation.score > 70
    assert "Restricted zone" in evaluation.reasons
    
    signals_critical = RiskSignals(object_class="person", camera_offline=True)
    eval_critical = engine.evaluate(signals_critical)
    assert eval_critical.severity == "HIGH" or eval_critical.severity == "CRITICAL"
    
@patch('app.core.storage.storage_client.get_client', return_value=None)
def test_evidence_storage_hash(mock_get_client):
    storage = EvidenceStorageService()
    # Mock frame 64x64 green image
    frame = np.zeros((64, 64, 3), dtype=np.uint8)
    frame[:] = (0, 255, 0)
    
    result = storage.upload_evidence(frame, "CAM-TEST", "INTRUSION")
    assert result is not None
    url, sha_hash, size = result
    assert size > 0
    assert len(sha_hash) == 64 # SHA-256 is 64 hex characters
    assert "local" in url or "evidence" in url
    
    # Extract filename
    filename = url.split("/")[-1]
    
    status = storage.verify_integrity(filename, sha_hash)
    assert status == "VERIFIED"
    
    status_fail = storage.verify_integrity(filename, "wronghashvalue")
    assert status_fail == "INTEGRITY_FAILURE"

    status_404 = storage.verify_integrity("missing_file.jpg", "hash")
    assert status_404 == "NOT_FOUND"

def test_anpr_ocr_normalization():
    # Example test logic for plate normalization (e.g. DL 01 AB 1234 -> DL01AB1234)
    raw_plate = "DL 01 A B 12 34"
    normalized = "".join(raw_plate.split()).upper()
    assert normalized == "DL01AB1234"

import asyncio
from datetime import timedelta
from app.services.offline_sync import OfflineSyncQueue
from app.services.event_engine import EventEngine

def test_offline_edge_queue_idempotency():
    queue = OfflineSyncQueue()
    # Ensure dir exists safely for tests without polluting prod
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory() as tmpdirname:
        queue.queue_dir = Path(tmpdirname)
        
        job_id = queue.enqueue("event", {"camera_id": "TEST_CAM", "severity": "HIGH"})
        assert job_id is not None
        
        jobs = queue.list_jobs()
        assert len(jobs) == 1
        assert jobs[0]["resource_type"] == "event"
        
        # Test background sync failure recovery mapping
        asyncio.run(queue.synchronize())
        # The mock currently succeeds asynchronously, destroying the file.
        assert len(queue.list_jobs()) == 0

def test_loitering_edge_cases():
    engine = EventEngine()
    engine.loitering_threshold_seconds = 30
    
    t1 = datetime.utcnow()
    # Case 1: Dwell time under threshold
    res1 = engine.process_track(None, "track-123", "cam-1", t1, t1 + timedelta(seconds=20), [])
    assert res1 is None
    
    # Case 2: Dwell time over threshold triggers loitering event
    res2 = engine.process_track(None, "track-123", "cam-1", t1, t1 + timedelta(seconds=35), [])
    assert res2 is not None
    assert res2.eventType == "LOITERING"
    assert "Dwell > 30s" in res2.reasons[0]
