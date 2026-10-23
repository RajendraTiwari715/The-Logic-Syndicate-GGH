# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.core_models import Person, VehicleRecord

class IdentityManager:
    RE_ENTRY_TIMEOUT_SEC = 120 # 2 minutes cooldown
    
    # Class-level or instance-level session maps to persist across frames
    _track_to_person: dict[str, str] = {}
    _track_to_vehicle: dict[str, str] = {}

    def __init__(self, db: Session):
        self.db = db

    def resolve_person(self, tracking_id: str, face_embedding: list = None, name: str = None, live_image: str = None) -> tuple[Person, bool]:
        permanent_id = self._track_to_person.get(tracking_id)
        person = None
        if permanent_id:
            person = self.db.query(Person).filter(Person.id == permanent_id).first()

        is_new_entry_event = False
        
        if not person:
            # Check if this face embedding matches ANY recently seen or known person
            matched_person = None
            if face_embedding:
                known_faces = self.db.query(Person).filter(Person.embedding.isnot(None)).all()
                best_distance = 0.15 # Stricter cosine similarity threshold for histogram-based embeddings
                
                for kf in known_faces:
                    try:
                        import math
                        emb1 = face_embedding
                        emb2 = kf.embedding
                        
                        # Calculate Cosine Distance using standard Python math
                        sum_xx, sum_yy, sum_xy = 0.0, 0.0, 0.0
                        for i in range(min(len(emb1), len(emb2))):
                            x = float(emb1[i])
                            y = float(emb2[i])
                            sum_xx += x * x
                            sum_yy += y * y
                            sum_xy += x * y
                            
                        norm1 = math.sqrt(sum_xx)
                        norm2 = math.sqrt(sum_yy)
                        
                        if norm1 > 0 and norm2 > 0:
                            dist = 1.0 - (sum_xy / (norm1 * norm2))
                        else:
                            dist = 1.0
                            
                        if dist < best_distance:
                            best_distance = dist
                            matched_person = kf
                    except Exception as e:
                        pass
                        
            if matched_person:
                person = matched_person
                self._track_to_person[tracking_id] = person.id
                # Only update last_seen and check for re-entry
                time_diff = datetime.now(timezone.utc) - person.last_seen.replace(tzinfo=timezone.utc)
                if time_diff.total_seconds() > self.RE_ENTRY_TIMEOUT_SEC:
                    person.entry_count += 1
                    is_new_entry_event = True
                person.last_seen = datetime.now(timezone.utc)
            else:
                from app.models.core_models import generate_uuid
                new_id = generate_uuid()
                person = Person(
                    id=new_id,
                    name=name or "UNKNOWN",
                    embedding=face_embedding,
                    authorization_status="UNKNOWN",
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    entry_count=1,
                    image=live_image
                )
                self._track_to_person[tracking_id] = new_id
                is_new_entry_event = True
                self.db.add(person)
        else:
            # Debounce re-entry logic
            time_diff = datetime.now(timezone.utc) - person.last_seen.replace(tzinfo=timezone.utc)
            if time_diff.total_seconds() > self.RE_ENTRY_TIMEOUT_SEC:
                person.entry_count += 1
                is_new_entry_event = True
            person.last_seen = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(person)
        return person, is_new_entry_event

    def resolve_vehicle(self, tracking_id: str, plate_number: str, live_image: str = None) -> tuple[VehicleRecord, bool]:
        # Check tracking ID session first (for fast debouncing without DB scan)
        permanent_id = self._track_to_vehicle.get(tracking_id)
        vehicle = None
        if permanent_id:
            vehicle = self.db.query(VehicleRecord).filter(VehicleRecord.id == permanent_id).first()

        is_new_entry_event = False
        
        if not vehicle:
            # 1. New Track Session: Search historical databases for the plate
            historical_match = None
            if plate_number and len(plate_number) > 3:
                historical_match = self.db.query(VehicleRecord).filter(
                    VehicleRecord.normalized_plate == plate_number, 
                    VehicleRecord.status.in_(["AUTHORIZED", "WATCHLIST"])
                ).first()

            if historical_match:
                vehicle = historical_match
                self._track_to_vehicle[tracking_id] = vehicle.id
                
                # Re-entry check
                if vehicle.last_seen:
                    now_utc = datetime.now(timezone.utc)
                    last_seen_utc = vehicle.last_seen.replace(tzinfo=timezone.utc) if vehicle.last_seen.tzinfo is None else vehicle.last_seen
                    delta_sec = (now_utc - last_seen_utc).total_seconds()
                else:
                    delta_sec = 0

                if delta_sec > self.RE_ENTRY_TIMEOUT_SEC:
                    vehicle.entry_count += 1
                    is_new_entry_event = True
                vehicle.last_seen = datetime.now(timezone.utc)
            else:
                from app.models.core_models import generate_uuid
                new_id = generate_uuid()
                vehicle = VehicleRecord(
                    id=new_id,
                    plateNumber=plate_number,
                    normalized_plate=plate_number,
                    status="UNKNOWN",
                    first_seen=datetime.now(timezone.utc),
                    last_seen=datetime.now(timezone.utc),
                    entry_count=1,
                    representative_image=live_image
                )
                self._track_to_vehicle[tracking_id] = new_id
                is_new_entry_event = True
                self.db.add(vehicle)
        else:
            # Debounce re-entry logic
            if vehicle.last_seen:
                now_utc = datetime.now(timezone.utc)
                last_seen_utc = vehicle.last_seen.replace(tzinfo=timezone.utc) if vehicle.last_seen.tzinfo is None else vehicle.last_seen
                delta_sec = (now_utc - last_seen_utc).total_seconds()
            else:
                delta_sec = 0

            if delta_sec > self.RE_ENTRY_TIMEOUT_SEC:
                vehicle.entry_count += 1
                is_new_entry_event = True
            vehicle.last_seen = datetime.now(timezone.utc)
            if plate_number:
                vehicle.plateNumber = plate_number # Use latest consensus
        self.db.commit()
        self.db.refresh(vehicle)
        return vehicle, is_new_entry_event
