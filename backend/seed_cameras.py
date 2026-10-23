import os
import sys

# Add the app path so it can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), "app"))

from sqlalchemy.orm import Session
from app.db.session import SessionLocal, engine, Base
from app.models.core_models import Camera

# Ensure tables are created
Base.metadata.create_all(bind=engine)

def seed_cameras():
    db = SessionLocal()
    try:
        existing_cams = db.query(Camera).count()
        if existing_cams > 0:
            print(f"Database already has {existing_cams} cameras. Skipping seed.")
            return

        mock_cameras = [
            Camera(id='CAM-01', name='Main Gate', location='North Entrance', bop='Command', status='ONLINE', fps=30, scenario='normal', recording=True),
            Camera(id='CAM-02', name='Perimeter West', location='West Wall', bop='Command', status='ONLINE', fps=30, scenario='normal', recording=False),
            Camera(id='CAM-03', name='Sector Alpha', location='Watchtower 1', bop='Alpha', status='ONLINE', fps=30, scenario='normal', recording=True),
            Camera(id='CAM-04', name='Sector Bravo', location='Checkpoint 2', bop='Bravo', status='OFFLINE', fps=0, scenario='normal', recording=False),
            Camera(id='CAM-05', name='Back Entry', location='South Gate', bop='Command', status='ONLINE', fps=30, scenario='normal', recording=True)
        ]
        
        db.add_all(mock_cameras)
        db.commit()
        print("Successfully seeded 5 mock cameras into the database.")
    except Exception as e:
        print(f"Error seeding cameras: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_cameras()
