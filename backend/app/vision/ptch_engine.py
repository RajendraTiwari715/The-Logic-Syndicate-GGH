import logging
from typing import Optional, Dict, Any
from app.vision.tracker import TrackState

logger = logging.getLogger(__name__)

class PTCHEngine:
    """
    Predictive Trajectory & Cross-Camera Handshake Engine
    Detects when an object leaves a camera frame at high speed, calculates
    a predicted arrival time at adjacent locations geographically, and broadcasts
    a handshake alert for neighboring cameras to wake up or boost FPS.
    """
    def __init__(self):
        # A simple geographic map linking camera border exits to expected target cameras.
        # Format: { "SourceCameraID": { "ExitBoundary": ("TargetCameraID", rough_distance_meters) } }
        self.geo_topology = {
            "CAM-01": {
                "East": ("CAM-02", 15.0),
                "North": ("CAM-03", 20.0)
            },
            "CAM-02": {
                "West": ("CAM-01", 15.0),
                "North": ("CAM-04", 45.0)
            },
            "Punjab Sector - Cam 1": {
                "East": ("Punjab Sector - Cam 2", 50.0)
            }
        }
        
    def evaluate_track_exit(self, track: TrackState) -> Optional[Dict[str, Any]]:
        """
        Called when a Track is marked as 'Lost' or 'Exited'. 
        Uses calculated speeds to generate a Handshake Event.
        """
        if track.status not in ["Exited", "Lost"]:
            return None
            
        boundary = track.exit_boundary
        if not boundary:
            return None
            
        # Get target camera expected from geographic rules
        routes = self.geo_topology.get(track.camera_id, {})
        target_route = routes.get(boundary)
        
        if not target_route:
            return None
            
        target_camera, distance_m = target_route
        speed = track.speed_units_per_sec  # In pixels per sec
        # Convert pixels to arbitrary meters (Depends heavily on camera calibration, 1px ~ 0.05m roughly)
        speed_m_s = max(0.5, speed * 0.05)
        
        eta_seconds = round(distance_m / speed_m_s, 1)
        
        alert = {
            "type": "PREDICTED_HANDSHAKE",
            "source_camera": track.camera_id,
            "target_camera": target_camera,
            "track_id": track.tracking_id,
            "object_class": track.object_class,
            "exit_boundary": boundary,
            "speed_m_s": round(speed_m_s, 2),
            "eta_seconds": eta_seconds,
            "message": f"Subject {track.tracking_id} exited {boundary} at {round(speed_m_s, 1)} m/s. Expect arrival at {target_camera} in {eta_seconds} seconds."
        }
        logger.info(f"PTCH Handshake Generated: {alert['message']}")
        return alert

ptch_engine = PTCHEngine()
