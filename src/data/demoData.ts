import type {
  Camera,
  EventItem,
  Alert,
  VehicleRecord,
  Zone,
  TrackRecord,
  AuditLog,
  FaceRecord,
  User,
  Detection,
  ScenarioType,
} from '../types';

export const DEMO_USERS: User[] = [
  { id: 'u1', name: 'Col. Rajesh Kumar', username: 'admin', role: 'admin', password: 'admin123' },
  { id: 'u2', name: 'Sub-Inspector Anil Verma', username: 'operator', role: 'operator', password: 'operator123' },
  { id: 'u3', name: 'DIG Priya Sharma', username: 'commander', role: 'commander', password: 'commander123' },
];

const BOP_NAMES = [
  'BOP Alpha', 'BOP Bravo', 'BOP Charlie', 'BOP Delta',
  'BOP Echo', 'BOP Foxtrot', 'BOP Golf', 'BOP Hotel',
];

const CAMERA_NAMES = [
  'Main Gate', 'Border Road', 'Check Post', 'Restricted Zone',
  'Watch Tower', 'Forest Sector', 'River Sector', 'Village Approach',
  'Fence Line A', 'Fence Line B', 'Patrol Track', 'Bridge Crossing',
];

const LOCATIONS = [
  'Punjab Border — Atari Sector 1', 'Punjab Border — Atari Sector 2',
  'Punjab Border — Wagah Approach', 'Sector 4 — Forest Corridor',
  'Sector 5 — Check Post Area', 'Sector 6 — Hill Approach',
  'Sector 7 — Village Perimeter', 'Sector 8 — Open Field',
];

const MAP_COORDS = [
  // Punjab / Amritsar Wagah Border approximate coordinates
  { lat: 31.605, lng: 74.580 }, { lat: 31.608, lng: 74.582 },
  { lat: 31.600, lng: 74.585 }, { lat: 31.595, lng: 74.590 },
  { lat: 31.602, lng: 74.575 }, { lat: 31.610, lng: 74.570 },
  { lat: 31.615, lng: 74.565 }, { lat: 31.620, lng: 74.560 },
];

const SCENARIOS: ScenarioType[] = [
  'normal', 'normal', 'normal', 'normal',
  'normal', 'normal', 'normal', 'normal',
  'normal', 'normal', 'normal', 'normal',
  'normal', 'normal', 'normal', 'normal',
  'normal', 'normal', 'normal', 'normal',
];

function rand(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pick<T>(arr: T[]): T {
  return arr[rand(0, arr.length - 1)];
}

function timeAgo(minutes: number): string {
  const d = new Date(Date.now() - minutes * 60_000);
  return d.toISOString();
}

export function generateCameras(): Camera[] {
  const cameras: Camera[] = [];
  for (let i = 0; i < 20; i++) {
    const bopIdx = Math.floor(i / 2.5);
    const bop = BOP_NAMES[Math.min(bopIdx, 7)];
    const camName = CAMERA_NAMES[i % CAMERA_NAMES.length];
    const status = i === 19 ? 'OFFLINE' : i === 17 ? 'DEGRADED' : 'ONLINE';
    cameras.push({
      id: `BOP-${String(i + 1).padStart(2, '0')}`,
      name: camName,
      bop,
      location: LOCATIONS[i % LOCATIONS.length],
      status: status as Camera['status'],
      fps: status === 'OFFLINE' ? 0 : status === 'DEGRADED' ? rand(8, 14) : rand(22, 30),
      latency: status === 'OFFLINE' ? 0 : rand(28, 85),
      storage: rand(42, 89),
      health: status === 'OFFLINE' ? 0 : status === 'DEGRADED' ? rand(55, 72) : rand(91, 99),
      lastHeartbeat: status === 'OFFLINE' ? timeAgo(rand(10, 240)) : new Date().toISOString(),
      signalQuality: status === 'OFFLINE' ? 0 : status === 'DEGRADED' ? rand(45, 65) : rand(82, 98),
      scenario: SCENARIOS[i] || 'normal',
      recording: status !== 'OFFLINE',
      detectionCount: status === 'OFFLINE' ? 0 : rand(3, 18),
      coords: { x: rand(15, 75), y: rand(15, 75) },
      mapCoord: MAP_COORDS[Math.min(bopIdx, 7)],
      camera_mode: 'ALL',
    });
  }
  return cameras;
}

const EVENT_TYPES = [
  'Person Detected', 'Vehicle Detected', 'Virtual Fence Crossing',
  'Loitering Detected', 'Night Movement', 'ANPR Capture',
  'Face Detected', 'Suspicious Activity', 'Camera Offline',
  'Multiple People', 'Wrong Direction', 'Watchlist Match',
];

const TRACKING_IDS = ['P-101', 'P-102', 'P-103', 'P-104', 'P-105', 'P-106', 'V-021', 'V-022', 'V-023', 'V-024'];

export function generateEvents(cameras: Camera[], count: number): EventItem[] {
  const events: EventItem[] = [];
  for (let i = 0; i < count; i++) {
    const cam = pick(cameras);
    const eventType = pick(EVENT_TYPES);
    const riskScore = rand(5, 98);
    const severity = riskScore <= 30 ? 'LOW' : riskScore <= 60 ? 'MEDIUM' : riskScore <= 80 ? 'HIGH' : 'CRITICAL';
    const reasons: string[] = [];
    if (riskScore > 60) reasons.push('Restricted zone');
    if (eventType.includes('Night')) reasons.push('Night-time detection');
    if (eventType.includes('Fence')) reasons.push('Virtual fence crossing');
    if (eventType.includes('Loiter')) reasons.push('Loitering > 60s');
    if (eventType.includes('Watchlist')) reasons.push('Watchlist match');
    if (reasons.length === 0) reasons.push('Normal activity');
    events.push({
      id: `EVT-${String(10000 + i).padStart(5, '0')}`,
      cameraId: cam.id,
      eventType,
      severity: severity as EventItem['severity'],
      trackingId: pick(TRACKING_IDS),
      description: `${eventType} at ${cam.id} — ${cam.location}`,
      timestamp: timeAgo(rand(1, 4320)),
      status: pick(['NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED']) as EventItem['status'],
      riskScore,
      reasons,
    });
  }
  return events.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export function generateAlerts(events: EventItem[], count: number): Alert[] {
  const alerts: Alert[] = [];
  const highEvents = events.filter(e => e.riskScore > 40).slice(0, count);
  for (const evt of highEvents) {
    const cam = evt.cameraId;
    const status = evt.status;
    alerts.push({
      id: `A-${String(100 + alerts.length).padStart(3, '0')}`,
      eventId: evt.id,
      severity: evt.severity,
      riskScore: evt.riskScore,
      reason: evt.reasons.join(' + '),
      reasons: evt.reasons,
      status: status as Alert['status'],
      createdAt: evt.timestamp,
      acknowledgedAt: status !== 'NEW' ? evt.timestamp : null,
      resolvedAt: status === 'RESOLVED' ? evt.timestamp : null,
      cameraId: cam,
      trackingId: evt.trackingId,
      title: evt.eventType.includes('Fence') ? 'Possible Border Intrusion'
        : evt.eventType.includes('Watchlist') ? 'Vehicle Watchlist Alert'
        : evt.eventType.includes('Night') ? 'Night-Time Intrusion'
        : evt.eventType.includes('Loiter') ? 'Suspicious Loitering'
        : evt.eventType.includes('Offline') ? 'Camera Offline'
        : 'Security Alert',
      what: evt.eventType,
      where: `${cam} / ${evt.description.split(' — ')[1] || 'Restricted Zone'}`,
      when: new Date(evt.timestamp).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true }),
      object: `${evt.trackingId}`,
      why: evt.reasons.join(' + '),
      zone: 'Restricted Border Sector A',
      confidence: rand(88, 99),
    });
  }
  return alerts;
}

const PLATES = [
  'CG04AB1234', 'DL08CD5678', 'UP16EF9012', 'BR01GH3456',
  'CG04XX0007', 'MH12JK7890', 'RJ14LM2345', 'WB05NO6789',
  'CG04XX0007', 'HR26PQ1357', 'GJ01ST2468', 'KA03UV3579',
];

const VEHICLE_TYPES = ['SUV', 'Sedan', 'Truck', 'Motorcycle', 'Pickup', 'Van'];

export function generateVehicles(cameras: Camera[], count: number): VehicleRecord[] {
  const vehicles: VehicleRecord[] = [];
  for (let i = 0; i < count; i++) {
    const cam = pick(cameras.filter(c => c.status !== 'OFFLINE'));
    const plate = pick(PLATES);
    const isWatch = plate === 'CG04XX0007';
    vehicles.push({
      id: `VH-${String(2000 + i).padStart(4, '0')}`,
      cameraId: cam.id,
      vehicleType: pick(VEHICLE_TYPES),
      plateNumber: plate,
      confidence: rand(85, 99),
      timestamp: timeAgo(rand(1, 2880)),
      status: isWatch ? 'WATCHLIST' : pick(['AUTHORIZED', 'UNKNOWN']) as VehicleRecord['status'],
      direction: pick(['Inbound', 'Outbound', 'North', 'South', 'East', 'West']),
    });
  }
  return vehicles.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export function generateZones(): Zone[] {
  return [
    {
      id: 'Z-01', cameraIds: ['BOP-04'], name: 'Restricted Border Sector A',
      zoneType: 'Virtual Fence', severity: 'CRITICAL',
      coordinates: [{ x: 20, y: 30 }, { x: 80, y: 30 }, { x: 80, y: 40 }, { x: 20, y: 40 }],
      rule: 'Person crossing → Critical alert',
    },
    {
      id: 'Z-02', cameraIds: ['BOP-06', 'BOP-07'], name: 'Forest Corridor Watch',
      zoneType: 'Loitering Zone', severity: 'HIGH',
      coordinates: [{ x: 30, y: 50 }, { x: 70, y: 50 }, { x: 70, y: 80 }, { x: 30, y: 80 }],
      rule: 'Loitering > 60 sec → High alert',
    },
    {
      id: 'Z-03', cameraIds: ['BOP-02'], name: 'Border Road Check',
      zoneType: 'Tripwire', severity: 'HIGH',
      coordinates: [{ x: 10, y: 60 }, { x: 90, y: 60 }],
      rule: 'Vehicle crossing → High alert',
    },
    {
      id: 'Z-04', cameraIds: ['BOP-07', 'BOP-08', 'BOP-09'], name: 'River Crossing Zone',
      zoneType: 'Virtual Fence', severity: 'CRITICAL',
      coordinates: [{ x: 25, y: 35 }, { x: 75, y: 35 }, { x: 75, y: 50 }, { x: 25, y: 50 }],
      rule: 'Any movement → Critical alert',
    },
  ];
}

export function generateTracks(cameras: Camera[]): TrackRecord[] {
  const tracks: TrackRecord[] = [];
  const trackData = [
    { id: 'P-101', type: 'person' as const, cam: 'BOP-01', dir: 'North-East', dur: '03:42' },
    { id: 'P-102', type: 'person' as const, cam: 'BOP-03', dir: 'South-West', dur: '01:18' },
    { id: 'P-103', type: 'person' as const, cam: 'BOP-05', dir: 'East', dur: '05:21' },
    { id: 'P-104', type: 'person' as const, cam: 'BOP-04', dir: 'North-East', dur: '01:24' },
    { id: 'P-105', type: 'person' as const, cam: 'BOP-06', dir: 'West', dur: '02:55' },
    { id: 'P-106', type: 'person' as const, cam: 'BOP-08', dir: 'North', dur: '00:47' },
    { id: 'V-021', type: 'vehicle' as const, cam: 'BOP-02', dir: 'Inbound', dur: '00:32' },
    { id: 'V-022', type: 'vehicle' as const, cam: 'BOP-02', dir: 'Outbound', dur: '00:18' },
    { id: 'V-023', type: 'vehicle' as const, cam: 'BOP-07', dir: 'North', dur: '01:05' },
    { id: 'V-024', type: 'vehicle' as const, cam: 'BOP-08', dir: 'South', dur: '00:51' },
  ];
  for (const t of trackData) {
    const history = [
      { cameraId: t.cam, time: timeAgo(rand(5, 10)) },
    ];
    if (t.type === 'person') {
      history.unshift({ cameraId: pick(cameras).id, time: timeAgo(rand(10, 20)) });
      history.unshift({ cameraId: pick(cameras).id, time: timeAgo(rand(20, 30)) });
    }
    tracks.push({
      trackingId: t.id,
      objectType: t.type,
      cameraId: t.cam,
      direction: t.dir,
      duration: t.dur,
      status: pick(['Active', 'Lost', 'Exited']) as TrackRecord['status'],
      firstSeen: timeAgo(rand(20, 40)),
      lastSeen: timeAgo(rand(1, 5)),
      history,
    });
  }
  return tracks;
}

export function generateAuditLogs(users: User[], count: number): AuditLog[] {
  const actions = [
    'logged in', 'viewed BOP-04', 'acknowledged alert A-102',
    'changed virtual fence', 'exported event report', 'viewed Live Surveillance',
    'created zone Restricted Sector B', 'resolved alert A-098',
    'escalated alert A-101', 'viewed Analytics', 'changed system settings',
    'viewed Audit Logs', 'started live demo', 'viewed Border Map',
  ];
  const logs: AuditLog[] = [];
  for (let i = 0; i < count; i++) {
    const user = pick(users);
    logs.push({
      id: `LOG-${String(5000 + i).padStart(5, '0')}`,
      user: user.name,
      action: pick(actions),
      timestamp: timeAgo(rand(1, 2880)),
      details: `Session from workstation-${rand(1, 12)}`,
      result: Math.random() > 0.08 ? 'SUCCESS' : 'FAILED',
      ip: `10.0.${rand(1, 4)}.${rand(10, 250)}`,
    });
  }
  return logs.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export function generateFaces(cameras: Camera[], count: number): FaceRecord[] {
  const identities = ['Person A', 'Person B', 'Person C', 'Person D', 'Person E'];
  const faces: FaceRecord[] = [];
  for (let i = 0; i < count; i++) {
    const cam = pick(cameras.filter(c => c.status !== 'OFFLINE'));
    const identity = pick(identities);
    faces.push({
      id: `FACE-${String(3000 + i).padStart(4, '0')}`,
      cameraId: cam.id,
      identity,
      confidence: rand(82, 99),
      timestamp: timeAgo(rand(1, 1440)),
      database: 'Authorized Personnel',
      status: Math.random() > 0.7 ? 'UNKNOWN' : 'AUTHORIZED' as FaceRecord['status'],
      direction: Math.random() > 0.5 ? 'Inbound' : 'Outbound',
    });
  }
  return faces.sort((a, b) => b.timestamp.localeCompare(a.timestamp));
}

export function generateDetections(cameras: Camera[], count: number): Detection[] {
  const detections: Detection[] = [];
  for (let i = 0; i < count; i++) {
    const cam = pick(cameras.filter(c => c.status !== 'OFFLINE'));
    const type = pick(['person', 'vehicle', 'face', 'plate']) as Detection['objectType'];
    const label = type === 'person' ? 'PERSON' : type === 'vehicle' ? pick(['CAR', 'TRUCK', 'SUV']) : type === 'face' ? 'FACE' : pick(PLATES);
    detections.push({
      id: `DET-${String(8000 + i).padStart(5, '0')}`,
      cameraId: cam.id,
      objectType: type,
      trackingId: type === 'person' ? `P-${rand(100, 120)}` : type === 'vehicle' ? `V-${rand(20, 30)}` : `F-${rand(50, 60)}`,
      confidence: rand(80, 99),
      timestamp: timeAgo(rand(1, 60)),
      bbox: { x: rand(10, 60), y: rand(10, 60), w: rand(15, 30), h: rand(20, 40) },
      label,
      direction: pick(['North', 'South', 'East', 'West', 'North-East', 'South-West']),
    });
  }
  return detections;
}
