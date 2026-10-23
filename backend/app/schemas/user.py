from pydantic import BaseModel
from app.models.user import UserRole
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str
    role_name: UserRole = UserRole.OPERATOR

class UserResponse(UserBase):
    id: str
    role_name: UserRole
    assigned_by: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    role: Optional[UserRole] = None

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None
