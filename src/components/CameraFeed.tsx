import { useEffect, useRef, useState } from 'react';
import type { Camera, Detection } from '../types';
import { useApp } from '../store';
import { API_BASE_URL } from '../lib/api';

interface Props {
  camera: Camera;
  detections?: Detection[];
  showOverlay?: boolean;
  compact?: boolean;
  liveStream?: MediaStream | null;
  fit?: 'cover' | 'contain';
  fullHeight?: boolean;
}

const scenarioLabels: Record<string, string> = {
  normal: 'NORMAL',
  intrusion: 'INTRUSION',
  night: 'NIGHT MODE',
  suspicious: 'SUSPICIOUS',
  vehicle: 'VEHICLE',
  anpr: 'ANPR',
  camera_failure: 'OFFLINE',
};

export default function CameraFeed({ camera, detections = [], showOverlay = true, compact = false, liveStream = null, fit = 'cover', fullHeight = false }: Props) {
  const { zones, savedFences } = useApp();
  const [time, setTime] = useState(new Date());
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (camera.status === 'OFFLINE') return;
  }, [camera.status]);

  useEffect(() => {
    if (liveStream && videoRef.current) {
      videoRef.current.srcObject = liveStream;
      videoRef.current.play().catch(() => {});
    }
  }, [liveStream]);

  // Push frames to the backend AI whenever this explicitly streams hardware
  useEffect(() => {
    let ws: WebSocket | null = null;
    let frameInterval: any = null;
    
    // Only HW streams are pushed independently from frontend
    if (liveStream && camera.id.startsWith('HW-')) {
      // Find actual Fencing ID map "HW:12ac..." based on name fallback or let it match any
      // For this demo mockHwCam name = device.label, so we map to HW:deviceId. But wait!
      // In LiveSurveillance we assigned HW-1, HW-2 to mockHwCam.id. We need to pass the real ID.
      // We will look up Fences that have ANY hardware mapped. To simplify, we'll map the active fences directly.
      ws = new WebSocket('ws://localhost:8000/ws/detections');
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      canvas.width = 640;
      canvas.height = 480;

      ws.onopen = () => {
         frameInterval = setInterval(() => {
            const video = videoRef.current;
            if (video && video.readyState >= 2) {
               ctx?.drawImage(video, 0, 0, canvas.width, canvas.height);
               const base64 = canvas.toDataURL('image/jpeg', 0.6);
               
               // Retrieve ALL fences containing ANY hardware camera to ensure they trigger
               const activeZonesForCam = savedFences
                  .filter(f => f.active && f.cameras.some(c => c.startsWith('HW:')))
                  .map(f => ({ id: f.id, name: f.name, points: f.points }));

               ws?.send(JSON.stringify({ 
                  type: 'frame', 
                  camera_id: camera.id, 
                  image: base64,
                  zones: activeZonesForCam,
                  camera_mode: camera.camera_mode || 'ALL'
               }));
            }
         }, 500); 
      };
    }
    
    return () => {
      if (frameInterval) clearInterval(frameInterval);
      if (ws) ws.close();
    };
  }, [liveStream, camera.id, savedFences]);

  const isOffline = camera.status === 'OFFLINE';
  const isNight = camera.scenario === 'night';
  const camDetections = detections.filter(d => d.cameraId === camera.id);
  const hasLive = !!liveStream;
  const camZones = zones.filter(z => z.cameraIds?.includes(camera.id));

  return (
    <div className={`relative overflow-hidden rounded-lg border bg-black flex flex-col ${isOffline ? 'border-red-500/30' : hasLive ? 'border-emerald-500/40' : 'border-white/10'} ${fullHeight ? 'h-full w-full' : 'h-full'}`}>
      <div className={`relative flex-1 w-full aspect-video ${fullHeight ? 'h-full' : compact ? 'h-40 min-h-[14rem]' : 'min-h-[14rem]'} overflow-hidden`}>
        {isOffline ? (
          <div className="flex h-full w-full items-center justify-center bg-black">
            <div className="text-center">
              <div className="mb-2 text-4xl text-red-500/40">!</div>
              <p className="text-xs font-mono text-red-400/60">SIGNAL LOST</p>
              <p className="mt-1 text-[10px] text-slate-600">Last frame unavailable</p>
            </div>
          </div>
        ) : (
          <div className={`relative h-full w-full ${isNight ? 'bg-gradient-to-b from-slate-950 via-indigo-950/40 to-slate-950' : 'bg-gradient-to-b from-slate-800 via-slate-700/60 to-slate-900'}`}>
            {/* Live video from phone camera */}
            {hasLive && (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`absolute inset-0 h-full w-full ${fit === 'contain' ? 'object-contain' : 'object-cover'}`}
              />
            )}

            {/* Live Universal CCTV Stream from backend */}
            {!hasLive && (camera.rtsp_url || camera.status === 'LIVE') && (
              <img
                src={`${API_BASE_URL}/api/v1/cameras/${camera.id}/live`}
                alt={camera.name}
                loading="lazy"
                className={`absolute inset-0 h-full w-full ${fit === 'contain' ? 'object-contain' : 'object-cover'}`}
                onError={(e) => {
                  (e.currentTarget as HTMLElement).style.display = 'none';
                }}
              />
            )}

            {/* Grid overlay */}
            {!hasLive && <div className="absolute inset-0 grid-overlay opacity-40" />}

            {/* Scanline */}
            <div className="absolute inset-x-0 h-px bg-accent-400/20 pointer-events-none custom-scan-line" />

            {/* Simulated scene elements (only when no live video) */}
            {!hasLive && (
              <div className={`absolute ${isNight ? 'opacity-30' : 'opacity-60'}`}>
                {camera.scenario === 'vehicle' || camera.scenario === 'anpr' ? (
                  <div className="absolute bottom-8 left-1/2 -translate-x-1/2">
                    <div className="h-8 w-20 rounded bg-slate-600/50 shadow-lg" />
                    <div className="mx-auto -mt-6 h-5 w-16 rounded-t bg-slate-500/50" />
                  </div>
                ) : null}
              </div>
            )}

            {/* Virtual Fences Overlay */}
            {camZones.length > 0 && (
              <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100" preserveAspectRatio="none">
                {camZones.map(zone => (
                  <polygon
                    key={zone.id}
                    points={zone.coordinates.map((p: { x: number; y: number }) => `${p.x},${p.y}`).join(' ')}
                    fill="rgba(239,68,68,0.1)"
                    stroke={zone.severity === 'CRITICAL' ? '#ef4444' : '#f97316'}
                    strokeWidth="0.5"
                    strokeDasharray="2 1"
                  />
                ))}
              </svg>
            )}

            {/* Detection boxes */}
            <div className="absolute inset-0 pointer-events-none z-30">
              {showOverlay && camDetections.map(det => (
                <DetectionBox key={det.id} det={det} night={isNight} />
              ))}
            </div>

            {/* Default simulated detection if no explicit detections - removed for strict real system */}

            {/* Night vision tint */}
            {isNight && (
              <div className="absolute inset-0 bg-emerald-900/10 mix-blend-overlay pointer-events-none" />
            )}
          </div>
        )}

        {/* Top overlay bar */}
        {!isOffline && (
          <div className="absolute top-0 left-0 right-0 flex items-center justify-between px-2 py-1 bg-gradient-to-b from-black/70 to-transparent pointer-events-none">
            <div className="flex items-center gap-1.5">
              <span className={`status-dot ${hasLive ? 'bg-emerald-400' : camera.status === 'ONLINE' ? 'bg-emerald-400' : 'bg-amber-400'} animate-pulse`} />
              <span className="text-[10px] font-mono text-slate-700">{camera.id}</span>
              {hasLive && (
                <span className="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 text-[9px] px-1 py-0">LIVE CAM</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              {camera.recording && (
                <span className="flex items-center gap-1 text-[10px] text-red-400">
                  <span className="status-dot bg-red-500 animate-pulse" /> REC
                </span>
              )}
              <span className="text-[10px] font-mono text-slate-600">{hasLive ? '30 FPS' : `${camera.fps} FPS`}</span>
            </div>
          </div>
        )}

        {/* Bottom overlay bar */}
        {!isOffline && !compact && (
          <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-2 py-1 bg-gradient-to-t from-black/70 to-transparent pointer-events-none">
            <span className="text-[10px] text-slate-700 truncate">{camera.name} — {camera.location}</span>
            <span className="text-[10px] font-mono text-accent-300">
              {time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
            </span>
          </div>
        )}

        {/* Scenario badge */}
        {!isOffline && (
          <div className="absolute top-7 right-2 pointer-events-none">
            <span className={`badge ${camera.scenario === 'normal' ? 'bg-emerald-500/20 text-emerald-300' : camera.scenario === 'night' ? 'bg-indigo-500/20 text-indigo-300' : camera.scenario === 'intrusion' ? 'bg-red-500/20 text-red-300' : 'bg-amber-500/20 text-amber-300'}`}>
              {scenarioLabels[camera.scenario]}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function DetectionBox({ det, night }: { det: Detection; night: boolean }) {
  const colors: Record<string, string> = {
    person: 'border-accent-400',
    vehicle: 'border-blue-400',
    face: 'border-purple-400',
    plate: 'border-amber-400',
    animal: 'border-orange-400',
  };
  const color = colors[det.objectType] || 'border-accent-400';
  const labelBg: Record<string, string> = {
    person: 'bg-accent-500/80',
    vehicle: 'bg-blue-500/80',
    face: 'bg-purple-500/80',
    plate: 'bg-amber-500/80',
    animal: 'bg-orange-500/80',
  };

  return (
    <div
      className={`absolute border-2 ${color} rounded-sm pointer-events-none shadow-[0_0_10px_rgba(0,0,0,0.5)] z-40 transition-all duration-100 ease-linear`}
      style={{
        left: `${det.bbox.x}%`,
        top: `${det.bbox.y}%`,
        width: `${det.bbox.w}%`,
        height: `${det.bbox.h}%`,
      }}
    >
      <div className={`absolute -top-6 left-[-2px] ${labelBg[det.objectType]} px-1.5 py-0.5 rounded-t text-[10px] font-bold text-white whitespace-nowrap shadow-md`}>
        {det.label.toUpperCase()} {Math.round(det.confidence)}%
      </div>
      {det.objectType === 'person' && (
        <div className="absolute inset-0 flex items-center justify-center">
          <div className={`w-2 h-2 rounded-full ${night ? 'bg-accent-300' : 'bg-accent-400'} animate-ping`} />
        </div>
      )}
    </div>
  );
}

