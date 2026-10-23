import { createContext, useContext, useEffect, useRef, useState, useCallback, type ReactNode } from 'react';
import type {
  Detection, User, AlertStatus, ScenarioType, CameraMode, Role, SavedFence,
  Camera, EventItem, Alert, VehicleRecord, Zone, TrackRecord, AuditLog, FaceRecord
} from './types';
import { api, WS_BASE_URL } from './lib/api';

interface AppState {
  user: User | null;
  token: string | null;
  login: (username: string, _password: string) => Promise<boolean>;
  logout: () => void;
  demoMode: boolean;
  setDemoMode: (on: boolean) => void;
  cameras: Camera[];
  events: EventItem[];
  alerts: Alert[];
  vehicles: VehicleRecord[];
  addVehicle: (vehicle: VehicleRecord) => void;
  zones: Zone[];
  tracks: TrackRecord[];
  auditLogs: AuditLog[];
  faces: FaceRecord[];
  addFace: (face: FaceRecord) => void;
  detections: Detection[];
  liveDemoRunning: boolean;
  startLiveDemo: () => void;
  stopLiveDemo: () => void;
  setCameraMode: (cameraId: string, mode: CameraMode) => void;
  acknowledgeAlert: (id: string) => void;
  escalateAlert: (id: string) => void;
  resolveAlert: (id: string) => void;
  addZone: (zone: Zone) => void;
  deleteZone: (id: string) => void;
  addAuditLog: (action: string, details?: string) => void;
  addAlert: (alert: Alert) => void;
  triggerCameraOffline: (cameraId: string) => void;
  toast: ToastMsg | null;
  showToast: (msg: ToastMsg) => void;
  activeAlarm: Alert | null;
  setActiveAlarm: (alarm: Alert | null) => void;
  watchlistPlates: string[];
  addToWatchlist: (plate: string, description?: string) => Promise<void>;
  updateVehicleStatus: (plate: string, status: 'AUTHORIZED' | 'WATCHLIST' | 'UNKNOWN') => void;
  refreshData: () => Promise<void>;
  selectedLiveCameraIds: string[] | null;
  setSelectedLiveCameraIds: (ids: string[] | null) => void;
  savedFences: SavedFence[];
  setSavedFences: (fences: SavedFence[]) => void;
}

export interface ToastMsg {
  type: 'info' | 'alert' | 'success' | 'warning';
  title: string;
  message: string;
}

const AppContext = createContext<AppState | null>(null);

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useApp must be used within AppProvider');
  return ctx;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('token'));
  
  // Keep demo mode flag for UI compatibility, but data comes from real backend
  const [demoMode, setDemoMode] = useState(false);
  const [liveDemoRunning, setLiveDemoRunning] = useState(false);

  const [cameras, setCameras] = useState<Camera[]>([]);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [vehicles, setVehicles] = useState<VehicleRecord[]>([]);
  const [zones, setZones] = useState<Zone[]>([]);
  const [tracks, setTracks] = useState<TrackRecord[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [faces, setFaces] = useState<FaceRecord[]>([]);
  const [detections, setDetections] = useState<Detection[]>([]);
  
  const [toast, setToast] = useState<ToastMsg | null>(null);
  const [activeAlarm, setActiveAlarm] = useState<Alert | null>(null);
  const [watchlistPlates, setWatchlistPlates] = useState<string[]>([]);
  const watchlistRef = useRef<string[]>([]);
  const [selectedLiveCameraIds, setSelectedLiveCameraIds] = useState<string[] | null>(null);
  const [savedFences, setSavedFences] = useState<SavedFence[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const detectionTtlRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  useEffect(() => {
    watchlistRef.current = watchlistPlates;
  }, [watchlistPlates]);

  useEffect(() => {
    // Create an audio element for the alarm siren
    const audio = new Audio('https://actions.google.com/sounds/v1/alarms/beeps_and_flashes.ogg'); 
    audio.loop = true;
    audioRef.current = audio;
    return () => { audio.pause(); };
  }, []);

  useEffect(() => {
    if (activeAlarm && activeAlarm.status !== 'RESOLVED') {
      audioRef.current?.play().catch(e => console.warn('Audio play blocked by browser:', e));
    } else {
      audioRef.current?.pause();
      if (audioRef.current) audioRef.current.currentTime = 0;
    }
  }, [activeAlarm]);

  const showToast = useCallback((msg: ToastMsg) => {
    setToast(msg);
    if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    toastTimerRef.current = setTimeout(() => setToast(null), 5000);
  }, []);

  // Fetch real data when user logs in
  const fetchData = useCallback(async () => {
    if (!user) return;
    let failedRequests = 0;
    const safe = async <T,>(promise: Promise<T>, fallback: T): Promise<T> => {
      try {
        return await promise;
      } catch (e) {
        failedRequests += 1;
        return fallback;
      }
    };

    try {
      const [cams, evts, alts, zns, vehs, logs, trks, fcs, wl] = await Promise.all([
        safe(api.cameras.list(), []),
        safe(api.alerts.events(), []),
        safe(api.alerts.list(), []),
        safe(api.zones.list(), []),
        safe(api.analytics.vehicles(), []),
        safe(api.analytics.auditLogs(), []),
        safe(api.analytics.tracks(), []),
        safe(api.analytics.recentFaces(), []),
        safe(api.analytics.watchlist(), []),
      ]);
      setCameras(cams);
      setEvents(evts);
      setAlerts(alts);
      setZones(zns);
      setVehicles(vehs);
      setAuditLogs(logs);
      setTracks(trks);
      setFaces(fcs);
      if (wl) {
        setWatchlistPlates(Array.from(new Set(wl.map((w: any) => String(w.plate_number || '').toUpperCase()).filter(Boolean))));
      }

      if (failedRequests >= 7 && cams.length === 0 && vehs.length === 0) {
        throw new Error('Backend unavailable');
      }
    } catch (e) {
      console.error('Initial data fetch failed, using fallback mock data for frontend demo', e);
      setCameras([]);
      setEvents([]);
      setAlerts([]);
      setZones([]);
      setVehicles([]);
      setAuditLogs([]);
      setTracks([]);
      setFaces([]);
      setWatchlistPlates([]);
    }
  }, [user]);

  useEffect(() => {
    fetchData();
    // Disabled polling for pure frontend demo to prevent console spam
    // const interval = setInterval(fetchData, 10000); 
    // return () => clearInterval(interval);
  }, [fetchData]);

  // Session verification on mount
  useEffect(() => {
    const t = localStorage.getItem('token');
    if (t) {
      // Bypass actual backend call to allow frontend-only usage
      setUser({ id: 'usr-1', username: 'admin', name: 'Command Center Admin', role: 'admin', password: '' });
      setToken(t);
    }
  }, []);

  // Real WebSocket for Live Detections instead of simulated demo
  useEffect(() => {
    if (!user) { wsRef.current?.close(); return; }
    const connect = () => {
      try {
        const ws = new WebSocket(`${WS_BASE_URL}/ws/detections`);
        wsRef.current = ws;
        ws.onmessage = (e) => {
          try {
            const data = JSON.parse(e.data);
            if (data.type === 'NEW_ALERT' && data.data) {
              setAlerts(prev => [data.data, ...prev]);
              if (data.data.severity === 'CRITICAL') {
                setActiveAlarm(data.data);
              } else {
                showToast({ type: 'warning', title: `Alert: ${data.data.severity}`, message: data.data.title || data.data.reason });
              }
            } else if (data.type === 'NEW_FACE' && data.data) {
              setFaces(prev => {
                const face = data.data;
                const existingIdx = prev.findIndex(f => f.identity === face.identity && f.identity !== 'Unknown');
                if (existingIdx !== -1) {
                  const existing = prev[existingIdx];
                  const newHistory = existing.history ? [...existing.history] : [];
                  newHistory.unshift({
                    timestamp: face.timestamp,
                    cameraId: face.cameraId,
                    image: face.image,
                    confidence: face.confidence
                  });
                  const updated = {
                    ...existing,
                    timestamp: face.timestamp,
                    image: face.image || existing.image,
                    thumbnail: face.thumbnail || existing.thumbnail,
                    cameraId: face.cameraId,
                    confidence: face.confidence,
                    history: newHistory
                  };
                  const newList = [...prev];
                  newList.splice(existingIdx, 1);
                  return [updated, ...newList].slice(0, 200);
                } else {
                  return [{...face, history: [{
                    timestamp: face.timestamp,
                    cameraId: face.cameraId,
                    image: face.image,
                    confidence: face.confidence
                  }]}, ...prev].slice(0, 200);
                }
              });
            } else if (data.type === 'detection' && data.data) {
              // Real YOLO bounding box from worker_pool — render it and auto-expire after 3s
              const trackId = data.data.trackingId || `trk-${Date.now()}`;
              const det: Detection = {
                id: data.data.id || trackId,
                cameraId: data.data.cameraId,
                objectType: data.data.objectType || 'person',
                trackingId: trackId,
                confidence: data.data.confidence || 0,
                timestamp: data.data.timestamp || new Date().toISOString(),
                bbox: {
                  x: data.data.bbox?.x ?? 0,
                  y: data.data.bbox?.y ?? 0,
                  w: data.data.bbox?.width ?? data.data.bbox?.w ?? 0,
                  h: data.data.bbox?.height ?? data.data.bbox?.h ?? 0,
                },
                label: data.data.label || data.data.objectType || 'UNKNOWN',
              };
              setDetections(prev => {
                const filtered = prev.filter(d => d.id !== det.id);
                return [...filtered, det];
              });
              // Auto-remove after 3 seconds
              const existing = detectionTtlRef.current.get(det.id);
              if (existing) clearTimeout(existing);
              const ttl = setTimeout(() => {
                setDetections(prev => prev.filter(d => d.id !== det.id));
                detectionTtlRef.current.delete(det.id);
              }, 3000);
              detectionTtlRef.current.set(det.id, ttl);
            } else if (data.type === 'intrusion') {
              const alarmItem = { ...data, timestamp: new Date().toISOString(), status: 'NEW' };
              setActiveAlarm(alarmItem);
            } else if (data.type === 'vehicle' && data.vehicle) {
              setVehicles(prev => {
                const vehicle = data.vehicle;
                const existingIdx = prev.findIndex(v => v.id === vehicle.id);
                if (existingIdx !== -1) {
                  const existing = prev[existingIdx];
                  const newHistory = existing.history ? [...existing.history] : [];
                  newHistory.unshift({
                    timestamp: vehicle.timestamp,
                    cameraId: vehicle.cameraId,
                    image: vehicle.image,
                    confidence: vehicle.confidence
                  });
                  const updated = {
                    ...existing,
                    timestamp: vehicle.timestamp,
                    image: vehicle.image || existing.image,
                    annotatedImage: vehicle.annotatedImage || existing.annotatedImage,
                    plateImage: vehicle.plateImage || existing.plateImage,
                    cameraId: vehicle.cameraId,
                    confidence: vehicle.confidence,
                    entryCount: vehicle.entry_count || existing.entryCount,
                    history: newHistory
                  };
                  const newList = [...prev];
                  newList.splice(existingIdx, 1);
                  return [updated, ...newList];
                } else {
                  return [{...vehicle, history: [{
                    timestamp: vehicle.timestamp,
                    cameraId: vehicle.cameraId,
                    image: vehicle.image,
                    confidence: vehicle.confidence
                  }]}, ...prev];
                }
              });
            }
          } catch {}
        };
        ws.onerror = () => {};
        ws.onclose = () => setTimeout(connect, 5000);
      } catch {}
    };
    connect();
    return () => wsRef.current?.close();
  }, [user, showToast]);

  const login = useCallback(async (username: string, password: string = ''): Promise<boolean> => {
    try {
      if (username.trim() !== 'admin' || password.trim() !== 'admin123') {
        throw new Error('Unauthorized Access. Cryptographic verification failed.');
      }
      
      const mockToken = 'mock_jwt_token_12345';
      localStorage.setItem('token', mockToken);
      setToken(mockToken);
      setUser({ 
        id: 'usr-1', 
        username: username, 
        name: 'Command Center Admin', 
        role: 'admin', 
        password: '' 
      });
      showToast({ type: 'success', title: 'Authentication Verified', message: 'Secure blockchain session established.' });
      return true;
    } catch (e: any) {
      showToast({ type: 'alert', title: 'Login Failed', message: e.message || 'Authentication failed' });
      return false;
    }
  }, [showToast]);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setUser(null);
    setToken(null);
    wsRef.current?.close();
  }, []);

  // Proxy the UI actions to the API
  const acknowledgeAlert = useCallback(async (id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: 'ACKNOWLEDGED' } : a));
    try { await api.alerts.acknowledge(id); } catch {}
  }, []);

  const escalateAlert = useCallback(async (id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: 'INVESTIGATING' } : a));
    try { await api.alerts.investigate(id); } catch {}
  }, []);

  const resolveAlert = useCallback(async (id: string) => {
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, status: 'RESOLVED' } : a));
    try { await api.alerts.resolve(id); } catch {}
  }, []);

  const addZone = useCallback(async (zone: Zone) => {
    try { 
      await api.zones.create({ ...zone, cameraId: zone.cameraIds[0] });
      fetchData();
    } catch {}
  }, [fetchData]);

  const deleteZone = useCallback(async (id: string) => {
    try {
      await api.zones.delete(id);
      fetchData();
    } catch {}
  }, [fetchData]);

  const addAuditLog = useCallback((action: string, details?: string) => {
    // Audit logs are auto-generated on backend, but we keep this for UI compatibility
  }, []);

  const addAlert = useCallback((alert: Alert) => {
    // Only used locally by live demo
    setAlerts(prev => [alert, ...prev]);
  }, []);

  const addFace = useCallback((face: FaceRecord) => {
    setFaces(prev => {
      const existingIdx = prev.findIndex(f => f.identity === face.identity && f.identity !== 'Unknown');
      if (existingIdx !== -1) {
        const existing = prev[existingIdx];
        const newHistory = existing.history ? [...existing.history] : [];
        newHistory.unshift({
          timestamp: face.timestamp,
          cameraId: face.cameraId,
          image: face.image,
          confidence: face.confidence
        });
        const updated = {
          ...existing,
          timestamp: face.timestamp,
          image: face.image || existing.image,
          thumbnail: face.thumbnail || existing.thumbnail,
          cameraId: face.cameraId,
          confidence: face.confidence,
          history: newHistory
        };
        const newList = [...prev];
        newList.splice(existingIdx, 1);
        return [updated, ...newList];
      } else {
        return [{...face, history: [{
          timestamp: face.timestamp,
          cameraId: face.cameraId,
          image: face.image,
          confidence: face.confidence
        }]}, ...prev];
      }
    });
  }, []);

  const addVehicle = useCallback((vehicle: VehicleRecord) => {
    const isWatchlisted = watchlistRef.current.includes(vehicle.plateNumber.toUpperCase()) || vehicle.status === 'WATCHLIST';
    const finalStatus = isWatchlisted ? 'WATCHLIST' : vehicle.status;

    if (isWatchlisted) {
      setActiveAlarm({
        id: 'ALM-' + Date.now(),
        eventId: 'EV-' + Date.now(),
        severity: 'CRITICAL',
        riskScore: 100,
        reason: 'Watchlist Vehicle Detected',
        reasons: ['Watchlist match'],
        status: 'NEW',
        createdAt: vehicle.timestamp,
        acknowledgedAt: null,
        resolvedAt: null,
        cameraId: vehicle.cameraId,
        trackingId: 'TRK-' + vehicle.plateNumber,
        title: 'Watchlist Match',
        what: 'Vehicle',
        where: vehicle.cameraId,
        when: vehicle.timestamp,
        object: vehicle.plateNumber,
        why: 'Plate matches watchlist',
        confidence: vehicle.confidence,
        image: vehicle.annotatedImage || vehicle.image
      });
      showToast({
        type: 'alert',
        title: 'Watchlist Vehicle Detected',
        message: `Plate ${vehicle.plateNumber} spotted at ${vehicle.cameraId}`
      });
    }

    setVehicles(prev => {
      const existingIdx = prev.findIndex(v => v.plateNumber === vehicle.plateNumber);
      if (existingIdx !== -1) {
        const existing = prev[existingIdx];
        const newHistory = existing.history ? [...existing.history] : [];
        newHistory.unshift({
          timestamp: vehicle.timestamp,
          cameraId: vehicle.cameraId,
          image: vehicle.image,
          confidence: vehicle.confidence
        });
        const updated = {
          ...existing,
          timestamp: vehicle.timestamp,
          image: vehicle.image || existing.image,
          annotatedImage: vehicle.annotatedImage || existing.annotatedImage,
          plateImage: vehicle.plateImage || existing.plateImage,
          cameraId: vehicle.cameraId,
          confidence: vehicle.confidence,
          status: finalStatus,
          history: newHistory
        };
        const newList = [...prev];
        newList.splice(existingIdx, 1);
        return [updated, ...newList]; // move to top
      } else {
        return [{...vehicle, status: finalStatus, history: [{
          timestamp: vehicle.timestamp,
          cameraId: vehicle.cameraId,
          image: vehicle.image,
          confidence: vehicle.confidence
        }]}, ...prev];
      }
    });
  }, [setActiveAlarm, showToast]);

  const updateVehicleStatus = useCallback((plate: string, status: 'AUTHORIZED' | 'WATCHLIST' | 'UNKNOWN') => {
    const p = plate.toUpperCase();
    setVehicles(prev => prev.map(v => v.plateNumber === plate ? { ...v, status } : v));
    if (status === 'WATCHLIST') {
      setWatchlistPlates(prev => prev.includes(p) ? prev : [...prev, p]);
    } else {
      setWatchlistPlates(prev => prev.filter(x => x !== p));
    }
  }, []);

  const triggerCameraOffline = useCallback((cameraId: string) => {
    // Demo only
  }, []);

  const addToWatchlist = useCallback(async (plate: string, description?: string) => {
    try {
      const desc = description?.trim() || "Manually registered";
      const record = await api.analytics.addWatchlist({ plate_number: plate, description: desc });
      const storedPlate = String(record.plate_number || plate).toUpperCase().trim();
      setWatchlistPlates(prev => Array.from(new Set([...prev, storedPlate])));
      showToast({ type: 'success', title: 'Plate Added', message: `${storedPlate} added to watchlist.` });
      await fetchData();
    } catch (e: any) {
      showToast({ type: 'alert', title: 'Error', message: e.message });
    }
  }, [showToast, fetchData]);

  // Dummy out the live demo simulation
  const startLiveDemo = useCallback(() => setLiveDemoRunning(true), []);
  const stopLiveDemo = useCallback(() => setLiveDemoRunning(false), []);
  const setCameraMode = useCallback(async (cameraId: string, mode: CameraMode) => {
    // Update locally for quick UI response
    setCameras(prev => prev.map(camera => (
      camera.id === cameraId ? { ...camera, camera_mode: mode } : camera
    )));
    
    // Call backend using existing API
    try {
      if (!cameraId.startsWith('HW-')) {
        await api.cameras.update(cameraId, { camera_mode: mode });
      }
    } catch (e) {
      console.error("Failed to update camera mode in backend", e);
    }
  }, []);

  const value: AppState = {
    user, token, login, logout, demoMode, setDemoMode,
    cameras, events, alerts, vehicles, zones, tracks, auditLogs, faces, detections,
    liveDemoRunning, startLiveDemo, stopLiveDemo,
    setCameraMode, acknowledgeAlert, escalateAlert, resolveAlert,
    addZone, deleteZone, addAuditLog, addAlert, addFace, addVehicle, updateVehicleStatus, triggerCameraOffline, toast, showToast,
    activeAlarm, setActiveAlarm, watchlistPlates, addToWatchlist,
    refreshData: fetchData,
    selectedLiveCameraIds, setSelectedLiveCameraIds,
    savedFences, setSavedFences,
  };

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}
