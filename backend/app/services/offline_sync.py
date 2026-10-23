import json
import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime
from uuid import uuid4
from pathlib import Path

logger = logging.getLogger(__name__)

class OfflineSyncQueue:
    def __init__(self):
        self.queue_dir = Path("data/edge_queue")
        self.queue_dir.mkdir(parents=True, exist_ok=True)
        self.sync_active = False

    def enqueue(self, resource_type: str, payload: Dict[str, Any]) -> str:
        job_id = str(uuid4())
        job_file = self.queue_dir / f"{job_id}.json"
        
        envelope = {
            "id": job_id,
            "resource_type": resource_type,
            "payload": payload,
            "created_at": datetime.utcnow().isoformat(),
            "retry_count": 0
        }
        
        try:
            with open(job_file, "w") as f:
                json.dump(envelope, f)
            logger.info(f"Enqueued offline job {job_id} for {resource_type}")
        except Exception as e:
            logger.error(f"Failed to enqueue offline job: {e}")
            
        return job_id

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        for file_path in self.queue_dir.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    jobs.append(json.load(f))
            except Exception:
                continue
        # Sort by creation logic
        jobs.sort(key=lambda x: x.get("created_at", ""))
        return jobs

    async def synchronize(self):
        """ Runs in background task to push jobs to central (or local DB if edge) """
        if self.sync_active:
            return
        
        self.sync_active = True
        try:
            jobs = self.list_jobs()
            if not jobs:
                return

            logger.info(f"Starting synchronization of {len(jobs)} edge offline objects")
            
            for job in jobs:
                success = await self._process_job(job)
                if success:
                    job_file = self.queue_dir / f"{job['id']}.json"
                    job_file.unlink(missing_ok=True)
                else:
                    job['retry_count'] += 1
                    # backoff would rely on retry count
                    job_file = self.queue_dir / f"{job['id']}.json"
                    with open(job_file, "w") as f:
                        json.dump(job, f)
                    
        finally:
            self.sync_active = False

    async def _process_job(self, job: Dict[str, Any]) -> bool:
        # Mock logic. In real IBVAP, we would HTTP POST to Central API.
        # Idempotency prevents duplicates logic on Central's end.
        logger.info(f"Syncing Job {job['id']} -> {job['resource_type']}")
        await asyncio.sleep(0.1) # Simulate network transmission delay
        return True # Fake success

offline_queue = OfflineSyncQueue()
