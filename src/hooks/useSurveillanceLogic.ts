import { useState, useEffect, useCallback, useMemo, useRef } from 'react';

// --- Type Definitions ---

export type DetectionType = 'CAR' | 'SUV' | 'PERSON' | 'FACE';
export type CameraStatus = 'NORMAL' | 'ALERT';

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Detection {
  id: string;
  type: DetectionType;
  confidence: number;
  boundingBox: BoundingBox;
  labelOffset?: number; // Used to avoid label overlap
}

export interface CameraPayload {
  cameraId: string;
  fps: number;
  status: CameraStatus;
  detections: Detection[];
  zone: string; // The zone this camera belongs to
}

export interface CameraState extends CameraPayload {
  lastUpdated: number;
}

// --- Constants ---
const LABEL_HEIGHT_PX = 20; // Estimated pixel height of a label to avoid overlap
const RESTRICTED_ZONES = ['RESTRICTED_ZONE_A', 'BOP-07-BORDER'];

// --- 5. FPS & Timestamp Calculator Utilities ---

/**
 * Parses and formats the live timestamp.
 * Returns time in hh:mm:ss am/pm format.
 */
export const getFormattedTimestamp = (): string => {
  const now = new Date();
  return now.toLocaleTimeString('en-US', {
    hour12: true,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Tracks and calculates active FPS based on message frequency
 */
export const useFPSCounter = () => {
  const [fps, setFps] = useState(0);
  const frameTimes = useRef<number[]>([]);

  const registerFrame = useCallback(() => {
    const now = performance.now();
    frameTimes.current.push(now);
    
    // Keep only frames from the last 1000ms (1 second)
    frameTimes.current = frameTimes.current.filter((time) => now - time <= 1000);
    
    setFps(frameTimes.current.length);
  }, []);

  return { fps, registerFrame };
};

// --- 3. Bounding Box Overlap & Collision Logic ---

/**
 * Checks for collision between labels and adjusts their Y offsets.
 * Modifies the array in place or returns a mapped array.
 */
export const adjustOverlappingLabels = (detections: Detection[]): Detection[] => {
  // Sort detections by Y coordinate to process them top-to-bottom
  const sorted = [...detections].sort((a, b) => a.boundingBox.y - b.boundingBox.y);
  
  for (let i = 0; i < sorted.length; i++) {
    sorted[i].labelOffset = 0;
    
    for (let j = 0; j < i; j++) {
      const prev = sorted[j];
      const curr = sorted[i];
      
      // Check if X coordinates overlap (assuming some label width, e.g., 50px)
      const xOverlap = Math.abs(curr.boundingBox.x - prev.boundingBox.x) < 50;
      
      // Check if Y coordinates overlap
      // We look at the actual Y position plus any existing offsets applied to the previous label
      const prevActualY = prev.boundingBox.y + (prev.labelOffset || 0);
      const currActualY = curr.boundingBox.y + (curr.labelOffset || 0);
      
      if (xOverlap && Math.abs(currActualY - prevActualY) < LABEL_HEIGHT_PX) {
        // Shift current label down to stack underneath the previous one
        curr.labelOffset = (prevActualY - curr.boundingBox.y) + LABEL_HEIGHT_PX;
      }
    }
  }
  
  return sorted;
};


// --- 1. Real-time Data Handling & 2. Camera Navigation & State Management ---

export const useLiveSurveillance = (initialCameras: CameraPayload[] = []) => {
  const [cameras, setCameras] = useState<Record<string, CameraState>>(() => {
    const state: Record<string, CameraState> = {};
    initialCameras.forEach(cam => {
      state[cam.cameraId] = { ...cam, lastUpdated: Date.now() };
    });
    return state;
  });

  const [activeZone, setActiveZone] = useState<string>('ALL');
  const [selectedCameraIds, setSelectedCameraIds] = useState<string[]>([]);
  
  const { fps, registerFrame } = useFPSCounter();

  // --- 4. Alert Trigger System ---
  
  /**
   * Evaluates incoming data for alert conditions.
   * If a PERSON is in a restricted zone or confidence > 95%, triggers an alert.
   */
  const evaluateAlerts = useCallback((payload: CameraPayload) => {
    let triggeredAlert = false;
    
    for (const detection of payload.detections) {
      const isRestrictedZone = RESTRICTED_ZONES.includes(payload.zone);
      
      // Rule 1: Person in restricted zone
      if (detection.type === 'PERSON' && isRestrictedZone) {
        console.warn(`[ALERT] Unauthorized PERSON detected at ${payload.cameraId} in ${payload.zone}`);
        triggeredAlert = true;
      }
      
      // Rule 2: High confidence generic threat (Example logic)
      if (detection.confidence >= 95) {
        console.warn(`[HIGH CONFIDENCE] ${detection.type} detected at ${payload.cameraId} with ${detection.confidence}% confidence`);
        // We could also set triggeredAlert = true here if desired
      }
    }
    
    return triggeredAlert ? 'ALERT' : payload.status;
  }, []);

  /**
   * Handles incoming real-time websocket/api frame data
   */
  const handleIncomingFrame = useCallback((payload: CameraPayload) => {
    registerFrame();
    
    setCameras(prev => {
      // Process bounding box collisions
      const resolvedDetections = adjustOverlappingLabels(payload.detections);
      
      // Evaluate for custom alerts
      const evaluatedStatus = evaluateAlerts(payload);

      return {
        ...prev,
        [payload.cameraId]: {
          ...payload,
          status: evaluatedStatus,
          detections: resolvedDetections,
          lastUpdated: Date.now(),
        }
      };
    });
  }, [registerFrame, evaluateAlerts]);


  // --- Camera Navigation & Filtering ---

  /**
   * Select which camera feeds to show on the active grid (e.g., max 4)
   */
  const toggleCameraOnGrid = useCallback((cameraId: string) => {
    setSelectedCameraIds(prev => {
      if (prev.includes(cameraId)) {
        return prev.filter(id => id !== cameraId);
      }
      if (prev.length < 4) {
        return [...prev, cameraId];
      }
      // If grid is full, replace the oldest one
      return [...prev.slice(1), cameraId];
    });
  }, []);

  /**
   * Memoized array of cameras filtered by the currently active zone
   */
  const filteredCameras = useMemo(() => {
    const allCams = Object.values(cameras);
    if (activeZone === 'ALL') {
      return allCams;
    }
    return allCams.filter(cam => cam.zone === activeZone);
  }, [cameras, activeZone]);

  /**
   * Memoized active cameras displayed on the grid
   */
  const activeGridCameras = useMemo(() => {
    return selectedCameraIds.map(id => cameras[id]).filter(Boolean);
  }, [selectedCameraIds, cameras]);


  return {
    // State
    cameras,
    filteredCameras,
    activeGridCameras,
    activeZone,
    globalFps: fps,
    
    // Actions
    setActiveZone,
    toggleCameraOnGrid,
    handleIncomingFrame,
  };
};
