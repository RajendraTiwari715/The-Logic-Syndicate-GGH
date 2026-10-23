from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from app.models.core_models import EventItem, Incident, IncidentEvent, Detection
import logging

logger = logging.getLogger(__name__)

class IncidentEngine:
    def __init__(self):
        self.correlation_window_seconds = 300 # 5 minutes

    def correlate_events(self, db: Session, new_event: EventItem) -> Optional[Incident]:
        """
        Check if an event maps to an ongoing incident based on time, location/camera clusters, 
        and object type, to prevent duplicates and link activity across cameras.
        """
        if not new_event.event_timestamp:
            return None

        time_threshold = new_event.event_timestamp - timedelta(seconds=self.correlation_window_seconds)
        
        # Super simplified locational correlation mapping
        # In a real deployed IBVAP, we would calculate Haversine distance from new_event.camera.mapCoord 
        
        # 1. Search for recent open incidents mapping to this event type
        recent_events = db.query(EventItem).filter(
            EventItem.eventType == new_event.eventType,
            EventItem.event_timestamp >= time_threshold,
            EventItem.id != new_event.id
        ).all()
        
        for event in recent_events:
            # Check if event belongs to an existing incident
            link = db.query(IncidentEvent).filter(IncidentEvent.event_id == event.id).first()
            if link:
                # Add this new event to the existing Incident
                new_link = IncidentEvent(incident_id=link.incident_id, event_id=new_event.id)
                db.add(new_link)
                db.commit()
                return db.query(Incident).filter(Incident.id == link.incident_id).first()

        # If it's a high severity event without an incident, create a new Incident
        if new_event.severity in ["HIGH", "CRITICAL"]:
            title = f"{new_event.severity} Incident: {new_event.eventType} Correlation"
            new_incident = Incident(title=title, status="OPEN")
            db.add(new_incident)
            db.commit()
            db.refresh(new_incident)
            
            # Map the event
            mapping = IncidentEvent(incident_id=new_incident.id, event_id=new_event.id)
            db.add(mapping)
            db.commit()
            return new_incident
            
        return None

incident_engine = IncidentEngine()
