import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class LedgerService:
    def __init__(self):
        # Local file-based mock append-only ledger for when nodes (Polygon/Solana) are unavailable.
        self.ledger_file = Path("data/ledger.jsonl")
        self.ledger_file.parent.mkdir(parents=True, exist_ok=True)
        self.node_id = "EDGE-NODE-01"
        self._last_hash = self._initialize_ledger()

    def _initialize_ledger(self) -> str:
        if not self.ledger_file.exists():
            return "0" * 64
        try:
            with open(self.ledger_file, 'r') as f:
                lines = f.readlines()
                if lines:
                    last_record = json.loads(lines[-1])
                    return last_record.get("hash", "0" * 64)
        except Exception as e:
            logger.error(f"Error reading ledger: {e}")
        return "0" * 64

    def _append_record(self, payload: Dict[str, Any]) -> str:
        payload["node_id"] = self.node_id
        payload["timestamp"] = datetime.utcnow().isoformat()
        payload["previous_hash"] = self._last_hash
        
        # Consistent ordering for hashing
        record_string = json.dumps(payload, sort_keys=True)
        current_hash = hashlib.sha256(record_string.encode('utf-8')).hexdigest()
        payload["hash"] = current_hash
        
        # Append-only write
        try:
            with open(self.ledger_file, "a") as f:
                f.write(json.dumps(payload) + "\n")
            self._last_hash = current_hash
        except Exception as e:
            logger.error(f"Failed to write to blockchain ledger: {e}")
            
        return current_hash

    def record_evidence_integrity(self, event_id: str, evidence_hash: str, actor: str = "SYSTEM") -> str:
        payload = {
            "type": "EVIDENCE_INTEGRITY",
            "event_id": event_id,
            "evidence_hash": evidence_hash,
            "actor": actor
        }
        return self._append_record(payload)

    def verify_evidence_integrity(self, evidence_hash: str) -> Optional[Dict[str, Any]]:
        # Scan ledger backwards for the hash
        if not self.ledger_file.exists():
            return None
        try:
            with open(self.ledger_file, 'r') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    data = json.loads(line)
                    if data.get("type") == "EVIDENCE_INTEGRITY" and data.get("evidence_hash") == evidence_hash:
                        return data
        except Exception as e:
            logger.error(f"Error verifying from ledger: {e}")
        return None

    def record_audit_event(self, action: str, actor: str, details: Dict[str, Any]) -> str:
        payload = {
            "type": "AUDIT",
            "action": action,
            "actor": actor,
            "details": details
        }
        return self._append_record(payload)

ledger_service = LedgerService()
