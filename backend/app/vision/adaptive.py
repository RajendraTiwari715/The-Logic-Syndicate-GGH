import time
import logging

logger = logging.getLogger(__name__)

class AdaptiveController:
    """
    Replaces blindly fixed frame skipping (1 out of N frames).
    Modulates inference FPS gracefully evaluating camera bounds and priority queue levels.
    """
    def __init__(self, camera_id: str, priority: str = "NORMAL"):
        self.camera_id = camera_id
        self.priority = priority
        
        # Determine bounds based on camera priority 
        if priority == "CRITICAL":
            self.min_fps, self.max_fps = 5.0, 30.0
        elif priority == "HIGH":
            self.min_fps, self.max_fps = 2.0, 15.0
        else: # NORMAL / REST 
            self.min_fps, self.max_fps = 1.0, 10.0
        
        self.current_target_fps = (self.min_fps + self.max_fps) / 2.0
        self.last_adjustment_time = time.time()
        self.recent_inferences = 0
        self.throttle_counter = 0

    def adjust(self, queue_depth: int, scene_activity: float = 0.0) -> float:
        """
        Calculates optimal FPS.
        If queue is deep (worker struggling or backpressured), we ease off inference.
        If scene activity is high (detected objects moving), we boost inference FPS to not miss key events.
        """
        now = time.time()
        if now - self.last_adjustment_time < 2.0:
            return self.current_target_fps  # Avoid unstable oscillation. Prevent yo-yo FPS changes.

        # Heuristic rules:
        if queue_depth > 3:
            # Overloaded. Need to drain queue. Reduce FPS drastically but respect minimum bounds.
            self.current_target_fps = max(self.min_fps, self.current_target_fps * 0.7)
            self.throttle_counter += 1
            if self.throttle_counter > 5:
                logger.warning(f"AdaptiveController: {self.camera_id} starved/overloaded. Dropping target fps to {self.current_target_fps:.1f}")
        else:
            self.throttle_counter = 0
            if scene_activity > 0.3:
                # Dense active scene. Boost FPS.
                self.current_target_fps = min(self.max_fps, self.current_target_fps * 1.5)
            elif queue_depth == 0:
                # Chill state. Slowly climb back to mid/max
                self.current_target_fps = min(self.max_fps, self.current_target_fps * 1.1)

        self.last_adjustment_time = now
        return self.current_target_fps

    def should_process_now(self, last_inference_time: float) -> bool:
        """
        True if enough time elapsed given current dynamic FPS. False to drop/skip frame.
        """
        current_time = time.time()
        elapsed = current_time - last_inference_time
        target_interval = 1.0 / self.current_target_fps
        return elapsed >= target_interval
