import { useEffect, useState } from 'react';
import { Camera as CameraIcon, Expand, MapPin, Radio } from 'lucide-react';
import type { Camera as CameraRecord, Detection } from '../types';
import { API_BASE_URL } from '../lib/api';

interface Props {
  camera: CameraRecord;
  detections: Detection[];
  onOpen: () => void;
  spanClass: string;
}

export default function DashboardCameraCard({ camera, detections, onOpen, spanClass }: Props) {
  const isOffline = ['OFFLINE', 'DISCONNECTED', 'ERROR'].includes(camera.status);
  const hasLiveSource = !isOffline && Boolean(camera.rtsp_url || camera.status === 'LIVE');
  const [streamState, setStreamState] = useState<'idle' | 'connecting' | 'live' | 'error'>('idle');
  const streamUrl = `${API_BASE_URL}/api/v1/cameras/${encodeURIComponent(camera.id)}/live`;

  useEffect(() => {
    setStreamState(hasLiveSource ? 'connecting' : 'idle');
  }, [hasLiveSource, streamUrl]);

  const statusLabel = isOffline
    ? 'OFFLINE'
    : hasLiveSource
      ? streamState === 'live'
        ? 'LIVE'
        : streamState === 'connecting'
          ? 'CONNECTING'
          : 'NO SIGNAL'
      : camera.status === 'DEGRADED'
        ? 'DEGRADED'
        : 'NO FRAME';
  const statusTone = isOffline
    ? 'border-red-300/30 bg-red-500/20 text-red-100'
    : statusLabel === 'LIVE'
      ? 'border-emerald-300/30 bg-emerald-500/20 text-emerald-100'
      : statusLabel === 'NO SIGNAL'
        ? 'border-amber-300/30 bg-amber-500/20 text-amber-100'
        : 'border-white/20 bg-slate-900/55 text-slate-100';
  const showLiveImage = hasLiveSource && streamState !== 'error';
  const visibleDetections = hasLiveSource && streamState === 'live'
    ? detections.filter(detection => detection.cameraId === camera.id).slice(0, 3)
    : [];
  const placeholderMessage = isOffline
    ? 'Camera offline'
    : hasLiveSource && streamState === 'error'
      ? 'Live signal unavailable'
      : hasLiveSource
        ? 'Connecting to camera'
        : 'No live frame available';

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label={`Open live surveillance for ${camera.id}, ${camera.name}`}
      className={`group relative block w-full overflow-hidden rounded-xl border border-slate-700/70 bg-slate-950 text-left shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-slate-500 hover:shadow-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 ${spanClass}`}
    >
      <div className="relative aspect-[1.9/1] overflow-hidden">
        {showLiveImage ? (
          <img
            src={streamUrl}
            alt={`Live camera feed ${camera.id}`}
            className="absolute inset-0 h-full w-full object-cover transition duration-500 group-hover:scale-[1.025]"
            onLoad={() => setStreamState('live')}
            onError={() => setStreamState('error')}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[radial-gradient(ellipse_at_center,_#1e293b_0%,_#0f172a_70%)] text-slate-400">
            {isOffline ? <CameraIcon className="h-8 w-8" /> : <Radio className="h-8 w-8" />}
            <span className="text-[10px] font-semibold uppercase tracking-[0.14em]">{placeholderMessage}</span>
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-b from-slate-950/75 via-transparent to-slate-950/75" />

        {visibleDetections.map(detection => (
          <div
            key={detection.id}
            className={`absolute z-10 rounded-sm border-2 ${detection.objectType === 'vehicle' ? 'border-red-400' : 'border-emerald-400'}`}
            style={{ left: `${detection.bbox.x}%`, top: `${detection.bbox.y}%`, width: `${detection.bbox.w}%`, height: `${detection.bbox.h}%` }}
          >
            <span className={`absolute -top-5 left-[-2px] whitespace-nowrap rounded-t px-1.5 py-0.5 text-[9px] font-bold text-white ${detection.objectType === 'vehicle' ? 'bg-red-600/90' : 'bg-emerald-600/90'}`}>
              {detection.label} {Math.round(detection.confidence)}%
            </span>
          </div>
        ))}

        <div className="absolute inset-x-0 top-0 flex items-center justify-between gap-2 px-3 py-2.5">
          <div className="min-w-0">
            <p className="truncate text-xs font-bold text-white sm:text-sm">{camera.id} · {camera.name}</p>
            {!hasLiveSource && !isOffline && <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-white/70">No live frame</p>}
          </div>
          <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2 py-1 text-[9px] font-bold uppercase tracking-wider ${statusTone}`}>
            <span className={`h-1.5 w-1.5 rounded-full ${isOffline ? 'bg-red-400' : statusLabel === 'LIVE' ? 'animate-pulse bg-emerald-400' : statusLabel === 'NO SIGNAL' ? 'bg-amber-300' : 'bg-slate-300'}`} />
            {statusLabel}
          </span>
        </div>

        <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-2 px-3 py-2.5">
          <div className="min-w-0">
            <p className="flex items-center gap-1 truncate text-[10px] font-medium text-white/85">
              <MapPin className="h-3 w-3 shrink-0" /> {camera.location}
            </p>
            <p className="mt-1 text-[9px] font-semibold uppercase tracking-[0.14em] text-white/60">{camera.bop}</p>
          </div>
          <span className="rounded-lg border border-white/20 bg-black/35 p-1.5 text-white/90 transition group-hover:bg-white/15">
            <Expand className="h-3.5 w-3.5" />
          </span>
        </div>
      </div>
    </button>
  );
}
