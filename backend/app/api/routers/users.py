from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core import security
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserResponse
from app.api.deps import get_current_user

router = APIRouter()

@router.post("/", response_model=UserResponse)
def create_user(
    user_in: UserCreate, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    # Rule 1: Only Admin can create Supervisors, Operators or Investigators
    # Rule 2: Supervisor can only create Operators or Investigators
    # Rule 3: Operator & Investigator cannot create any user
    
    if current_user.role_name in [UserRole.OPERATOR, UserRole.INVESTIGATOR]:
        raise HTTPException(status_code=403, detail="Operators/Investigators cannot create users")
    
    if current_user.role_name == UserRole.SUPERVISOR and user_in.role_name not in [UserRole.OPERATOR, UserRole.INVESTIGATOR]:
        raise HTTPException(status_code=403, detail="Supervisors can only create Operators or Investigators")

    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already registered")
        
    hashed_password = security.get_password_hash(user_in.password)
    db_user = User(
        username=user_in.username, 
        hashed_password=hashed_password, 
        role_name=user_in.role_name,
        assigned_by=current_user.id
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/assigned", response_model=list[UserResponse])
def get_assigned_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Returns users assigned by the current user
    users = db.query(User).filter(User.assigned_by == current_user.id).all()
    return users
