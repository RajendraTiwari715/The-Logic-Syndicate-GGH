from sqlalchemy.orm import Session
from app.models.core_models import AuditLog
import logging

logger = logging.getLogger(__name__)

def log_audit_action(db: Session, actor_id: str, actor_name: str, action: str, details: str, resource_type: str = None, resource_id: str = None, result: str = "SUCCESS", ip: str = "System"):
    try:
        new_log = AuditLog(
            user=actor_name,
            actor_id=actor_id,
            action=action,
            details=details,
            result=result,
            ip=ip,
            resource_type=resource_type,
            resource_id=resource_id
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to record audit log natively: {e}")
