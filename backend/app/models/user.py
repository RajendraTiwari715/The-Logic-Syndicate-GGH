from sqlalchemy import Column, Integer, String, Enum, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base
import enum
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    SUPERVISOR = "SUPERVISOR"
    OPERATOR = "OPERATOR"
    INVESTIGATOR = "INVESTIGATOR"

class Role(Base):
    __tablename__ = 'roles'
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(Enum(UserRole), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"

    # Changed from Integer to String to support UUIDs across system
    id = Column(String(36), primary_key=True, default=generate_uuid)
    username = Column(String(100), unique=True, index=True)
    hashed_password = Column(String(255))
    role_name = Column(Enum(UserRole), default=UserRole.OPERATOR)
    assigned_by = Column(String(36), nullable=True) # ID of the admin/sub-admin who assigned this user
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

