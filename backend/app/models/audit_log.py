from sqlalchemy import Column, Integer, String, DateTime
from app.db.session import Base
from datetime import datetime

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    action = Column(String) # e.g., "Started Camera 1", "Acknowledged Alert #112"
    timestamp = Column(DateTime, default=datetime.utcnow)
