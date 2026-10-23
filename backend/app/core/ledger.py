import hashlib
import json
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.models.core_models import BlockchainLedger, EventItem
import logging

logger = logging.getLogger(__name__)

def record_event_ledger(db: Session, event: EventItem) -> str:
    """
    Creates an immutable cryptographic block for the event to prove it was not tampered with.
    """
    try:
        # Get genesis hash or previous block hash
        last_block = db.query(BlockchainLedger).order_by(desc(BlockchainLedger.created_at)).first()
        prev_hash = last_block.block_hash if last_block else "0000000000000000000000000GENESIS"
        
        # Serialize the event data cleanly for hashing verification
        payload = {
            "id": event.id,
            "camera": event.cameraId,
            "type": event.eventType,
            "severity": event.severity,
            "score": event.riskScore,
            "desc": event.description,
            "time": str(event.timestamp)
        }
        payload_dump = json.dumps(payload, sort_keys=True)
        
        # SHA-256 cascade combination
        raw = f"{prev_hash}||{payload_dump}"
        block_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        
        ledger_entry = BlockchainLedger(
            event_id=event.id,
            previous_hash=prev_hash,
            block_hash=block_hash,
            payload_dump=payload_dump
        )
        db.add(ledger_entry)
        db.commit()
        return block_hash
        
    except Exception as e:
        logger.error(f"Failed to record event to blockchain ledger: {e}")
        db.rollback()
        return None
