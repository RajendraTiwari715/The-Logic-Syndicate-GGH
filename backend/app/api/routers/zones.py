from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.core_models import Zone as DB_Zone
from app.models.user import User
from app.schemas.core_schemas import Zone, ZoneCreate
from app.api.deps import get_current_user, get_current_active_supervisor

router = APIRouter()

@router.get("/", response_model=List[Zone])
def get_zones(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    zones = db.query(DB_Zone).all()
    return zones

from app.services.audit import log_audit_action

@router.post("/", response_model=Zone)
def create_zone(
    zone: ZoneCreate, 
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    new_zone = DB_Zone(**zone.model_dump())
    db.add(new_zone)
    db.commit()
    db.refresh(new_zone)
    
    log_audit_action(db, str(supervisor.id), supervisor.username, "CREATE_ZONE", f"Created zone {new_zone.name}", "Zone", str(new_zone.id))
    return new_zone

@router.put("/{zone_id}", response_model=Zone)
def update_zone(
    zone_id: str,
    zone_in: ZoneCreate,
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    db_zone = db.query(DB_Zone).filter(DB_Zone.id == zone_id).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    update_data = zone_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_zone, field, value)
        
    db.commit()
    db.refresh(db_zone)
    
    log_audit_action(db, str(supervisor.id), supervisor.username, "UPDATE_ZONE", f"Updated zone {db_zone.name}", "Zone", str(db_zone.id))
    return db_zone

@router.delete("/{zone_id}")
def delete_zone(
    zone_id: str, 
    db: Session = Depends(get_db),
    supervisor: User = Depends(get_current_active_supervisor)
):
    db_zone = db.query(DB_Zone).filter(DB_Zone.id == zone_id).first()
    if not db_zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    db.delete(db_zone)
    db.commit()
    
    log_audit_action(db, str(supervisor.id), supervisor.username, "DELETE_ZONE", f"Deleted zone {db_zone.name}", "Zone", str(zone_id))
    return {"message": "Zone deleted successfully"}
