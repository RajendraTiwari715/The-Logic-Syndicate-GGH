from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.db.session import get_db
from app.models.core_models import Alert as DB_Alert, EventItem as DB_Event, AlertState
from app.models.user import User
from app.schemas.core_schemas import Alert, AlertCreate, EventItem, EventItemCreate
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/events", response_model=List[EventItem])
def get_events(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    events = db.query(DB_Event).order_by(DB_Event.event_timestamp.desc(), DB_Event.timestamp.desc()).all()
    return events

from app.services.incident_engine import incident_engine

@router.post("/events", response_model=EventItem)
def create_event(
    event: EventItemCreate, 
    db: Session = Depends(get_db) 
):
    db_event = DB_Event(**event.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Process multi-camera algorithmic clustering directly
    try:
        incident_engine.correlate_events(db, db_event)
    except Exception as e:
        # Prevent analytics failures from dropping the crucial real-time tracking Event
        pass
        
    return db_event

@router.get("/", response_model=List[Alert])
def get_alerts(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    alerts = db.query(DB_Alert).order_by(DB_Alert.created_at_dt.desc(), DB_Alert.createdAt.desc()).all()
    return alerts

@router.post("/", response_model=Alert)
def create_alert(alert: AlertCreate, db: Session = Depends(get_db)):
    db_alert = DB_Alert(**alert.model_dump())
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert

from app.services.audit import log_audit_action

@router.put("/{alert_id}/acknowledge", response_model=Alert)
def acknowledge_alert(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_alert = db.query(DB_Alert).filter(DB_Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db_alert.status = AlertState.ACKNOWLEDGED
    time_now = datetime.utcnow()
    db_alert.acknowledgedAt = time_now.isoformat() + "Z"
    db_alert.acknowledged_by = current_user.id
    
    if db_alert.eventId:
        event = db.query(DB_Event).filter(DB_Event.id == db_alert.eventId).first()
        if event:
            event.status = AlertState.ACKNOWLEDGED
            
    db.commit()
    db.refresh(db_alert)
    log_audit_action(db, str(current_user.id), current_user.username, "ACKNOWLEDGE_ALERT", f"Acknowledged alert {db_alert.title}", "Alert", alert_id)
    return db_alert

@router.put("/{alert_id}/investigate", response_model=Alert)
def investigate_alert(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_alert = db.query(DB_Alert).filter(DB_Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    # "INVESTIGATING" translates to ESCALATED or VERIFIED depending on flow. Will map to VERIFIED for now.
    db_alert.status = AlertState.VERIFIED
    
    if db_alert.eventId:
        event = db.query(DB_Event).filter(DB_Event.id == db_alert.eventId).first()
        if event:
            event.status = AlertState.VERIFIED
            
    db.commit()
    db.refresh(db_alert)
    log_audit_action(db, str(current_user.id), current_user.username, "VERIFY_ALERT", f"Verified alert {db_alert.title}", "Alert", alert_id)
    return db_alert

@router.put("/{alert_id}/resolve", response_model=Alert)
def resolve_alert(alert_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_alert = db.query(DB_Alert).filter(DB_Alert.id == alert_id).first()
    if not db_alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    db_alert.status = AlertState.CLOSED
    time_now = datetime.utcnow()
    db_alert.resolvedAt = time_now.isoformat() + "Z"
    
    if db_alert.eventId:
        event = db.query(DB_Event).filter(DB_Event.id == db_alert.eventId).first()
        if event:
            event.status = AlertState.CLOSED
            
    db.commit()
    db.refresh(db_alert)
    log_audit_action(db, str(current_user.id), current_user.username, "RESOLVE_ALERT", f"Resolved alert {db_alert.title}", "Alert", alert_id)
    return db_alert
