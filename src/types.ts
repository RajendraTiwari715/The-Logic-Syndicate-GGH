export type Role = 'admin' | 'sub_admin' | 'operator' | 'commander';

export type AlertStatus = 'NEW' | 'ACKNOWLEDGED' | 'INVESTIGATING' | 'RESOLVED';
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type CameraStatus = 'ONLINE' | 'OFFLINE' | 'DEGRADED' | 'LIVE' | 'DISCONNECTED' | 'ERROR' | 'MAINTENANCE';
export type CameraMode =
  | 'ALL'
  | 'FACE & OBJECT'
  | 'ANPR';

export type ScenarioType =
  | 'normal'
  | 'intrusion'
  | 'night'
  | 'suspicious'
  | 'vehicle'
  | 'anpr'
  | 'camera_failure';

export type ObjectType = 'person' | 'vehicle' | 'face' | 'plate' | 'animal';

export interface User {
  id: string;
  name: string;
  username: string;
  role: Role;
  password: string;
}

export interface Camera {
  id: string;
  name: string;
  bop: string;
  location: string;
  status: CameraStatus;
  fps: number;
  latency: number;
  storage: number;
  health: number;
  lastHeartbeat: string;
  signalQuality: number;
  scenario: ScenarioType;
  camera_mode: CameraMode;
  recording: boolean;
  detectionCount: number;
  coords: { x: number; y: number };
  mapCoord: { lat: number; lng: number };
  rtsp_url?: string;
  protocol?: string;
  resolution?: string;
}

export interface Detection {
  id: string;
  cameraId: string;
  objectType: ObjectType;
  trackingId: string;
  confidence: number;
  timestamp: string;
  bbox: { x: number; y: number; w: number; h: number };
  label: string;
  direction?: string;
}

export interface EventItem {
  id: string;
  cameraId: string;
  eventType: string;
  severity: RiskLevel;
  trackingId: string;
  description: string;
  timestamp: string;
  status: AlertStatus;
  riskScore: number;
  reasons: string[];
}

export interface Alert {
  id: string;
  eventId: string;
  severity: RiskLevel;
  riskScore: number;
  reason: string;
  reasons: string[];
  status: AlertStatus;
  createdAt: string;
  acknowledgedAt: string | null;
  resolvedAt: string | null;
  cameraId: string;
  trackingId: string;
  title: string;
  what: string;
  where: string;
  when: string;
  object: string;
  why: string;
  zone?: string;
  confidence: number;
  image?: string;
}

export interface VehicleRecord {
  id: string;
  cameraId: string;
  vehicleType: string;
  plateNumber: string;
  confidence: number;
  timestamp: string;
  status: 'AUTHORIZED' | 'WATCHLIST' | 'UNKNOWN';
  direction: string;
  image?: string;
  annotatedImage?: string;
  plateImage?: string;
  stateCode?: string;
  sharpness?: number;
  rawText?: string;
  entryCount?: number;
  history?: { timestamp: string; cameraId: string; image?: string; confidence: number }[];
}

export interface Zone {
  id: string;
  cameraIds: string[];
  name: string;
  zoneType: string;
  severity: RiskLevel;
  coordinates: { x: number; y: number }[];
  rule: string;
}

export interface TrackRecord {
  trackingId: string;
  objectType: ObjectType;
  cameraId: string;
  direction: string;
  duration: string;
  status: 'Active' | 'Lost' | 'Exited';
  firstSeen: string;
  lastSeen: string;
  history: { cameraId: string; time: string }[];
}

export interface AuditLog {
  id: string;
  user: string;
  action: string;
  timestamp: string;
  details: string;
  result: 'SUCCESS' | 'FAILED';
  ip: string;
}

export interface FaceRecord {
  id: string;
  cameraId: string;
  type?: 'human' | 'object';
  identity: string;
  confidence: number;
  timestamp: string;
  database: string;
  status: 'AUTHORIZED' | 'UNKNOWN' | 'FLAGGED';
  direction: 'Inbound' | 'Outbound';
  image?: string;
  thumbnail?: string; // Add thumbnail if it's missing but used
  history?: { timestamp: string; cameraId: string; image?: string; confidence: number }[];
}

export interface SavedFence {
  id: string;
  name: string;
  cameras: string[];
  points: { x: number; y: number }[];
  active: boolean;
}


export const riskColor: Record<RiskLevel, string> = {
  LOW: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  MEDIUM: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  HIGH: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
  CRITICAL: 'text-red-400 bg-red-500/10 border-red-500/30',
};

export const statusColor: Record<AlertStatus, string> = {
  NEW: 'text-red-400 bg-red-500/10 border-red-500/30',
  ACKNOWLEDGED: 'text-amber-400 bg-amber-500/10 border-amber-500/30',
  INVESTIGATING: 'text-accent-400 bg-accent-500/10 border-accent-500/30',
  RESOLVED: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
};

export function riskFromScore(score: number): RiskLevel {
  if (score <= 30) return 'LOW';
  if (score <= 60) return 'MEDIUM';
  if (score <= 80) return 'HIGH';
  return 'CRITICAL';
}
