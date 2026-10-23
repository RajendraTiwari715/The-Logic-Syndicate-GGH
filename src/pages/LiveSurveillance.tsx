import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useApp } from '../store';
import { api } from '../lib/api';
import CameraFeed from '../components/CameraFeed';
import ModeSelector from '../components/ModeSelector';
import {
  Activity,
  AlertTriangle,
  Bell,
  Camera as CameraIcon,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  Cctv,
  Grid3x3,
  Layers,
  Loader,
  MapPin,
  Maximize,
  Minimize,
  Play,
  Radio,
  RefreshCw,
  Smartphone,
  X,
} from 'lucide-react';
import type { Camera } from '../types';

// Remove SCENARIOS as it is now in ModeSelector

type FeedScope = 'all' | 'online' | 'offline' | 'activity';

const isOfflineStatus = (status: Camera['status']) => ['OFFLINE', 'DISCONNECTED', 'ERROR'].includes(status);
const isOnlineStatus = (status: Camera['status']) => status === 'ONLINE' || status === 'LIVE';

function HardwareVideoPlayer({ stream }: { stream: MediaStream }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (ref.current && stream) {
      ref.current.srcObject = stream;
      ref.current.play().catch(e => console.log('Fullscreen HW camera play error', e));
    }
  }, [stream]);

  return (
    <video
      ref={ref}
      autoPlay
      muted
      playsInline
      className="absolute inset-0 h-full w-full object-cover bg-black"
    />
  );
}

export default function LiveSurveillance() {
  const { cameras, alerts, setCameraMode, detections, selectedLiveCameraIds, setSelectedLiveCameraIds, savedFences, showToast, refreshData } = useApp();
  const [gridSize, setGridSize] = useState<'2x2' | '3x3'>('2x2');
  const [gridPage, setGridPage] = useState(0);
  const [feedScope, setFeedScope] = useState<FeedScope>('all');
  const [selectedLocation, setSelectedLocation] = useState('all');
  const [liveStream, setLiveStream] = useState<MediaStream | null>(null);
  const [camError, setCamError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);
  const [expandedCameraId, setExpandedCameraId] = useState<string | null>(null);
  const streamRef = useRef<MediaStream | null>(null);

  // Universal CCTV Infrastructure State
  const [showCctvModal, setShowCctvModal] = useState(false);
  const [cctvName, setCctvName] = useState('Sector 4 Boundary Camera');
  const [cctvBop, setCctvBop] = useState('BOP-04');
  const [cctvLocation, setCctvLocation] = useState('Perimeter Fence East');
  const [customRtsp, setCustomRtsp] = useState('');
  const [probing, setProbing] = useState(false);
  const [probeResult, setProbeResult] = useState<any>(null);
  const [deploying, setDeploying] = useState(false);

  const getGeneratedRtsp = () => {
    return customRtsp.trim() || '0';
  };

  const handleProbe = async () => {
    setProbing(true);
    setProbeResult(null);
    try {
      const url = getGeneratedRtsp();
      const res = await api.cameras.probe(url);
      setProbeResult(res);
      if (res.accessible) {
        showToast?.({ type: 'success', title: 'CCTV Verified', message: `Connected at ${res.resolution} (${res.fps} FPS, ${res.latency_ms}ms latency)` });
      } else {
        showToast?.({ type: 'alert', title: 'CCTV Unreachable', message: res.error });
      }
    } catch (err: any) {
      setProbeResult({ accessible: false, error: err.message || 'Probe request failed' });
      showToast?.({ type: 'alert', title: 'Probe Error', message: err.message });
    } finally {
      setProbing(false);
    }
  };

  const handleDeployCctv = async () => {
    setDeploying(true);
    try {
      const url = getGeneratedRtsp();
      const cleanBop = cctvBop.replace(/[^A-Za-z0-9]/g, '').toUpperCase() || 'BOP';
      const newId = `CAM-${cleanBop}-${Date.now().toString().slice(-4)}`;
      await api.cameras.create({
        camera_id: newId,
        name: cctvName,
        bop: cctvBop,
        location: cctvLocation,
        source: url,
        source_type: url === '0' || url === '1' ? 'webcam' : 'rtsp',
      });
      // Trigger Autonomous AI start
      await api.cameras.startAi(newId);
      showToast?.({ type: 'success', title: 'CCTV Deployed & AI Active', message: `Autonomous AI surveillance initiated on ${cctvName}` });
      setShowCctvModal(false);
      refreshData?.();
    } catch (err: any) {
      showToast?.({ type: 'alert', title: 'Deployment Failed', message: err.message || 'Could not save camera stream' });
    } finally {
      setDeploying(false);
    }
  };

  const isExpanded = expandedCameraId !== null;

  useEffect(() => {
    // Only standard component mounts here. Global Alarm handles timer.
  }, []);

  const connectPhoneCamera = useCallback(async () => {
    setCamError(null);
    setConnecting(true);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API not available. Use HTTPS or localhost.');
      }
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      setLiveStream(stream);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to access camera';
      setCamError(msg);
    } finally {
      setConnecting(false);
    }
  }, []);

  const disconnectPhoneCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
      streamRef.current = null;
    }
    setLiveStream(null);
  }, []);

  const selectedCameras = selectedLiveCameraIds && selectedLiveCameraIds.length > 0
    ? cameras.filter(c => selectedLiveCameraIds.includes(c.id))
    : cameras;

  const [hardwareCameras, setHardwareCameras] = useState<MediaDeviceInfo[]>([]);
  const hardwareStreamsRef = useRef<{ [deviceId: string]: MediaStream }>({});

  const visibleHwCameras = hardwareCameras.filter(device =>
    !selectedLiveCameraIds || selectedLiveCameraIds.length === 0 || selectedLiveCameraIds.includes(`HW:${device.deviceId}`)
  );

  const onlineCameraCount = cameras.filter(camera => isOnlineStatus(camera.status)).length;
  const offlineCameraCount = cameras.filter(camera => isOfflineStatus(camera.status)).length;
  const hardwareLiveCount = Object.values(hardwareStreamsRef.current).filter(stream => stream.getVideoTracks().some(track => track.readyState === 'live')).length;
  const activeAlertCount = alerts.filter(alert => alert.status !== 'RESOLVED').length;
  const detectedCameraIds = new Set(detections.map(detection => detection.cameraId));
  const locations = Array.from(new Set(cameras.map(camera => camera.location))).sort();
  const filteredCameras = selectedCameras.filter(camera => {
    if (selectedLocation !== 'all' && camera.location !== selectedLocation) return false;
    if (feedScope === 'online' && !isOnlineStatus(camera.status)) return false;
    if (feedScope === 'offline' && !isOfflineStatus(camera.status)) return false;
    if (feedScope === 'activity' && !detectedCameraIds.has(camera.id)) return false;
    return true;
  });
  const scopedHardwareCameras = visibleHwCameras.filter((device, index) => {
    if (selectedLocation !== 'all' || feedScope === 'offline') return false;
    if (feedScope === 'activity' && !detectedCameraIds.has(`HW-${index + 1}`) && !detectedCameraIds.has(`HW:${device.deviceId}`)) return false;
    return true;
  });

  const feedItems = [
    ...filteredCameras.map(camera => ({
      key: camera.id,
      camera,
      stream: liveStream,
      hardware: false,
      sourceLabel: camera.rtsp_url ? 'IP CAMERA' : 'NETWORK',
    })),
    ...scopedHardwareCameras.map((device, index) => {
      const cameraId = `HW-${index + 1}`;
      const camera = cameras.find(existing => existing.id === cameraId) ?? {
        id: cameraId,
        name: device.label || `USB Camera ${index + 1}`,
        bop: 'Command Center',
        location: 'Local System',
        status: 'ONLINE' as const,
        fps: 30,
        latency: 0,
        storage: 0,
        health: 100,
        lastHeartbeat: new Date().toISOString(),
        signalQuality: 100,
        scenario: 'normal' as const,
        camera_mode: 'ALL' as const,
        recording: false,
        detectionCount: 0,
        coords: { x: 0, y: 0 },
        mapCoord: { lat: 0, lng: 0 },
      } satisfies Camera;
      return {
        key: `HW:${device.deviceId}`,
        camera,
        stream: hardwareStreamsRef.current[device.deviceId] ?? null,
        hardware: true,
        sourceLabel: 'LOCAL DEVICE',
      };
    }),
  ];
  const pageSize = gridSize === '2x2' ? 4 : 9;
  const pageCount = Math.max(1, Math.ceil(feedItems.length / pageSize));
  const pageFeedItems = feedItems.slice(gridPage * pageSize, (gridPage + 1) * pageSize);
  const activityScopeCount = new Set(detections.map(detection => detection.cameraId)).size;

  useEffect(() => {
    setGridPage(0);
  }, [feedScope, gridSize, selectedLiveCameraIds, selectedLocation]);

  useEffect(() => {
    if (gridPage >= pageCount) setGridPage(Math.max(0, pageCount - 1));
  }, [gridPage, pageCount]);

  useEffect(() => {
    // Only standard component mounts here. Global Alarm handles timer.
    const loadHardwareCameras = async () => {
      try {
        if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) return;
        const devices = await navigator.mediaDevices.enumerateDevices();
        const videoDevices = devices.filter(d => d.kind === 'videoinput');
        setHardwareCameras(videoDevices);

        // Auto-connect to them
        for (const device of videoDevices) {
          if (!hardwareStreamsRef.current[device.deviceId]) {
            try {
              const stream = await navigator.mediaDevices.getUserMedia({
                video: { deviceId: { exact: device.deviceId } },
                audio: false
              });
              hardwareStreamsRef.current[device.deviceId] = stream;
            } catch (e) {
              console.error("Could not start hardware camera", device.label, e);
            }
          }
        }
        // Force a re-render to show streams
        setHardwareCameras([...videoDevices]);
      } catch (err) {
        console.error("Hardware enumeration failed", err);
      }
    };

    loadHardwareCameras();

    if (navigator.mediaDevices) {
      navigator.mediaDevices.addEventListener('devicechange', loadHardwareCameras);
    }

    return () => {
      if (navigator.mediaDevices) {
        navigator.mediaDevices.removeEventListener('devicechange', loadHardwareCameras);
      }
      // Stop streams on unmount
      Object.values(hardwareStreamsRef.current).forEach(stream => {
        stream.getTracks().forEach(t => t.stop());
      });
      hardwareStreamsRef.current = {};
    };
  }, []);

  return (
    <div className="live-shell relative animate-fade-in space-y-4 pb-8">
      <header className="relative overflow-hidden rounded-3xl bg-slate-950 px-5 py-5 text-white shadow-[0_18px_50px_rgba(15,23,42,0.18)] sm:px-7 sm:py-6">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_85%_0%,rgba(59,130,246,0.28),transparent_35%),linear-gradient(110deg,transparent_45%,rgba(16,185,129,0.08))]" />
        <div className="relative z-10 flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.3em] text-emerald-300">Operations center / video wall</p>
            <h1 className="mt-2 text-2xl font-black tracking-tight sm:text-3xl">Live Surveillance</h1>
            <p className="mt-1.5 max-w-2xl text-xs leading-relaxed text-slate-300 sm:text-sm">Monitor camera feeds, review detections, and control connected devices from one view.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/25 bg-emerald-400/10 px-3 py-2 text-xs font-bold text-emerald-200">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              {onlineCameraCount + hardwareLiveCount} CONNECTED
            </div>
            <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-xs font-semibold text-slate-200">
              <Radio className="h-3.5 w-3.5 text-blue-300" />
              {cameras.length + hardwareCameras.length} CHANNELS
            </div>
            {activeAlertCount > 0 && (
              <div className="inline-flex items-center gap-2 rounded-full border border-red-400/25 bg-red-400/10 px-3 py-2 text-xs font-bold text-red-200">
                <Bell className="h-3.5 w-3.5" />
                {activeAlertCount} OPEN ALERTS
              </div>
            )}
          </div>
        </div>
      </header>

      <section aria-label="Surveillance summary" className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <div className="glass-metric-card flex items-center gap-3 border-emerald-200 p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600"><Cctv className="h-5 w-5" /></div>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Online feeds</p><p className="mt-1 text-2xl font-black tabular-nums text-slate-900">{onlineCameraCount + hardwareLiveCount}</p></div>
        </div>
        <div className="glass-metric-card flex items-center gap-3 border-blue-200 p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-blue-50 text-blue-600"><Activity className="h-5 w-5" /></div>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Detections</p><p className="mt-1 text-2xl font-black tabular-nums text-slate-900">{detections.length}</p></div>
        </div>
        <div className="glass-metric-card flex items-center gap-3 border-amber-200 p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-amber-50 text-amber-600"><Grid3x3 className="h-5 w-5" /></div>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Grid layout</p><p className="mt-1 text-2xl font-black text-slate-900">{gridSize}</p></div>
        </div>
        <div className="glass-metric-card flex items-center gap-3 border-red-200 p-4">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-red-50 text-red-600"><AlertTriangle className="h-5 w-5" /></div>
          <div><p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Offline cameras</p><p className="mt-1 text-2xl font-black tabular-nums text-slate-900">{offlineCameraCount}</p></div>
        </div>
      </section>

      <section className="glass-panel relative z-10 space-y-3 p-3 sm:p-4" aria-label="Feed filters and controls">
        <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex rounded-xl border border-slate-200 bg-white/80 p-1 shadow-sm" role="group" aria-label="Filter feeds">
              {([
                ['all', 'All feeds', cameras.length + hardwareCameras.length],
                ['online', 'Online', onlineCameraCount + hardwareLiveCount],
                ['offline', 'Offline', offlineCameraCount],
                ['activity', 'With activity', activityScopeCount],
              ] as [FeedScope, string, number][]).map(([scope, label, count]) => (
                <button
                  key={scope}
                  type="button"
                  aria-pressed={feedScope === scope}
                  onClick={() => {
                    setFeedScope(scope);
                    setSelectedLocation('all');
                    setSelectedLiveCameraIds(null);
                    setGridPage(0);
                  }}
                  className={`rounded-lg px-3 py-2 text-[11px] font-bold transition ${feedScope === scope ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'}`}
                >
                  {label}<span className={`ml-1.5 tabular-nums ${feedScope === scope ? 'text-slate-300' : 'text-slate-400'}`}>{count}</span>
                </button>
              ))}
            </div>

            <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white/80 px-3 py-2 shadow-sm">
              <MapPin className="h-3.5 w-3.5 shrink-0 text-slate-400" />
              <span className="sr-only">Filter by camera location</span>
              <select
                value={selectedLocation}
                onChange={event => {
                  setSelectedLocation(event.target.value);
                  setSelectedLiveCameraIds(null);
                  setGridPage(0);
                }}
                className="max-w-[180px] bg-transparent text-[11px] font-semibold text-slate-700 outline-none"
              >
                <option value="all">All locations</option>
                {locations.map(location => <option key={location} value={location}>{location}</option>)}
              </select>
            </label>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => setShowCctvModal(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-3.5 py-2.5 text-[10px] font-bold uppercase tracking-[0.12em] text-white shadow-sm transition hover:bg-blue-700"
            >
              <Cctv className="h-4 w-4" /> Connect IP camera
            </button>
            {liveStream ? (
              <button
                type="button"
                onClick={disconnectPhoneCamera}
                className="inline-flex items-center gap-2 rounded-xl border border-red-200 bg-red-50 px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.12em] text-red-700 transition hover:bg-red-100"
              >
                <X className="h-3.5 w-3.5" /> Disconnect phone
              </button>
            ) : (
              <button
                type="button"
                onClick={connectPhoneCamera}
                disabled={connecting}
                className="inline-flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2.5 text-[10px] font-bold uppercase tracking-[0.12em] text-emerald-800 transition hover:bg-emerald-100 disabled:opacity-50"
              >
                <Smartphone className="h-3.5 w-3.5" /> {connecting ? 'Connecting…' : 'Connect phone'}
              </button>
            )}

            <div className="glass-toggle" role="group" aria-label="Video wall layout">
              {(['2x2', '3x3'] as const).map(size => (
                <button
                  key={size}
                  type="button"
                  aria-pressed={gridSize === size}
                  onClick={() => {
                    setGridSize(size);
                    setGridPage(0);
                  }}
                  className={`rounded-lg px-3 py-2 text-[10px] font-black uppercase tracking-[0.12em] transition ${gridSize === size ? 'bg-slate-900 text-white shadow-sm' : 'text-slate-600 hover:bg-slate-100'}`}
                >
                  {size}
                </button>
              ))}
            </div>
          </div>
        </div>

        {savedFences.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t border-slate-200/70 pt-3">
            <span className="mr-1 text-[10px] font-bold uppercase tracking-[0.16em] text-slate-500">Fence groups</span>
            {savedFences.map(fence => {
              const isSelected = selectedLiveCameraIds?.length === fence.cameras.length && fence.cameras.every(cameraId => selectedLiveCameraIds.includes(cameraId));
              return (
                <button
                  key={fence.id}
                  type="button"
                  aria-pressed={Boolean(isSelected)}
                  onClick={() => {
                    setSelectedLocation('all');
                    setFeedScope('all');
                    setSelectedLiveCameraIds(fence.cameras);
                    setGridPage(0);
                  }}
                  className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1.5 text-[10px] font-semibold transition ${isSelected ? 'border-blue-300 bg-blue-50 text-blue-800' : 'border-slate-200 bg-white/70 text-slate-600 hover:border-slate-300 hover:bg-white'}`}
                >
                  <Layers className="h-3 w-3" /> {fence.name}
                </button>
              );
            })}
          </div>
        )}
      </section>

      {camError && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 shadow-sm">
          <div className="flex items-start gap-2">
            <X className="mt-0.5 h-4 w-4 text-red-500" />
            <div className="flex-1">
              <p className="text-xs font-bold uppercase tracking-[0.2em] text-red-600">Camera access failed</p>
              <p className="mt-1 text-sm text-red-700">{camError}</p>
              <p className="mt-1 text-[11px] text-slate-600">
                Tip: The browser needs camera permission. On phone, allow access over HTTPS and retry.
              </p>
            </div>
            <button onClick={connectPhoneCamera} className="text-[10px] font-bold uppercase tracking-[0.18em] text-red-600 hover:text-red-700">
              Retry
            </button>
          </div>
        </div>
      )}

      {liveStream && (
        <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 shadow-sm">
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4 text-emerald-600" />
            <p className="text-sm text-emerald-700">
              <span className="font-bold">Phone camera connected.</span> Broadcasting live feed to all camera viewports.
            </p>
          </div>
        </div>
      )}

      <section className="overflow-hidden rounded-3xl border border-slate-200 bg-white/75 shadow-sm" aria-label="Camera video wall">
        <div className="flex flex-col gap-3 border-b border-slate-200/80 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-5">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-sm font-extrabold text-slate-900 sm:text-base">Camera video wall</h2>
              <span className="rounded-md border border-slate-200 bg-white px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wider text-slate-500">{gridSize}</span>
            </div>
            <p className="mt-0.5 text-[10px] font-medium text-slate-500">
              {feedItems.length === 0 ? 'No feeds match the current filters' : `Showing ${gridPage * pageSize + 1}–${Math.min((gridPage + 1) * pageSize, feedItems.length)} of ${feedItems.length} feeds`}
            </p>
          </div>
          <div className="flex items-center gap-1.5 self-end sm:self-auto">
            <button
              type="button"
              aria-label="Previous camera page"
              disabled={gridPage === 0}
              onClick={() => setGridPage(page => Math.max(0, page - 1))}
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="min-w-[68px] text-center text-[10px] font-bold tabular-nums text-slate-500">{gridPage + 1} / {pageCount}</span>
            <button
              type="button"
              aria-label="Next camera page"
              disabled={gridPage >= pageCount - 1}
              onClick={() => setGridPage(page => Math.min(pageCount - 1, page + 1))}
              className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-sm transition hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>

        {pageFeedItems.length > 0 ? (
          <div className={`grid gap-3 bg-slate-100/70 p-3 sm:gap-4 sm:p-4 ${gridSize === '2x2' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2 xl:grid-cols-3'}`}>
            {pageFeedItems.map(item => {
              const offline = isOfflineStatus(item.camera.status);
              const cameraDetections = detections.filter(detection => detection.cameraId === item.camera.id);
              const fullscreenKey = item.hardware ? item.key : item.camera.id;
              const statusLabel = offline
                ? 'OFFLINE'
                : item.hardware
                  ? item.stream ? 'LIVE' : 'NO SIGNAL'
                  : item.stream || item.camera.rtsp_url || item.camera.status === 'LIVE'
                    ? 'LIVE'
                    : item.camera.status === 'DEGRADED'
                      ? 'DEGRADED'
                      : 'ONLINE';

              return (
                <article key={item.key} className="group min-w-0 space-y-2.5 rounded-2xl border border-slate-200 bg-white p-2 shadow-[0_4px_16px_rgba(15,23,42,0.07)] transition hover:border-slate-300 hover:shadow-md">
                  <div className="camera-card relative aspect-video overflow-hidden rounded-xl border border-slate-800 bg-slate-950">
                    <CameraFeed
                      camera={item.camera}
                      detections={detections}
                      liveStream={item.stream}
                      compact
                      fullHeight
                    />
                  </div>

                  <div className="flex min-w-0 items-center justify-between gap-2 px-1 pb-1">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <span className={`h-2 w-2 shrink-0 rounded-full ${offline ? 'bg-red-500' : statusLabel === 'LIVE' ? 'animate-pulse bg-emerald-500' : statusLabel === 'NO SIGNAL' ? 'bg-amber-500' : 'bg-blue-500'}`} />
                        <p className="truncate text-xs font-extrabold text-slate-800">{item.camera.id} · {item.camera.name}</p>
                        <span className={`hidden shrink-0 rounded px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-wider sm:inline ${offline ? 'bg-red-50 text-red-700' : statusLabel === 'LIVE' ? 'bg-emerald-50 text-emerald-700' : statusLabel === 'NO SIGNAL' ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'}`}>{statusLabel}</span>
                      </div>
                      <p className="mt-1 flex min-w-0 items-center gap-2 truncate pl-4 text-[10px] text-slate-500">
                        <span className="truncate">{item.camera.bop} <span className="px-1 text-slate-300">/</span> {item.camera.location}</span>
                        <span className="shrink-0 text-slate-300">·</span>
                        <span className="shrink-0 font-semibold text-slate-500">{item.sourceLabel}</span>
                        {cameraDetections.length > 0 && <span className="shrink-0 font-bold text-blue-600">{cameraDetections.length} detections</span>}
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-1.5">
                      <ModeSelector
                        value={item.camera.camera_mode || 'ALL'}
                        onChange={value => setCameraMode(item.camera.id, value)}
                        disabled={offline}
                      />
                      <button
                        type="button"
                        aria-label={`${isExpanded && expandedCameraId === fullscreenKey ? 'Close' : 'Open'} fullscreen for ${item.camera.name}`}
                        onClick={() => setExpandedCameraId(isExpanded && expandedCameraId === fullscreenKey ? null : fullscreenKey)}
                        className="rounded-lg border border-slate-200 bg-white p-2 text-slate-600 shadow-sm transition hover:border-slate-300 hover:bg-slate-50 hover:text-slate-900"
                        title={isExpanded && expandedCameraId === fullscreenKey ? 'Exit fullscreen' : 'Open fullscreen'}
                      >
                        {isExpanded && expandedCameraId === fullscreenKey ? <Minimize className="h-3.5 w-3.5" /> : <Maximize className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <div className="flex min-h-[280px] flex-col items-center justify-center bg-slate-50 px-5 py-10 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-slate-400 shadow-sm"><CameraIcon className="h-6 w-6" /></div>
            <h3 className="mt-3 text-sm font-bold text-slate-700">No feeds to display</h3>
            <p className="mt-1 max-w-sm text-xs text-slate-500">Change the status or location filters to see other cameras.</p>
            <button
              type="button"
              onClick={() => {
                setFeedScope('all');
                setSelectedLocation('all');
                setSelectedLiveCameraIds(null);
                setGridPage(0);
              }}
              className="mt-4 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-bold text-white transition hover:bg-slate-700"
            >
              Clear filters
            </button>
          </div>
        )}
      </section>

      {offlineCameraCount > 0 && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 shadow-sm">
          <div className="flex items-center gap-2">
            <Cctv className="h-4 w-4 text-red-500" />
            <p className="text-sm text-red-700">
              {offlineCameraCount} camera(s) offline: {cameras.filter(camera => isOfflineStatus(camera.status)).map(camera => camera.id).join(', ')}
            </p>
          </div>
        </div>
      )}

      {/* FIXED FULLSCREEN MODAL */}
      {isExpanded && createPortal(
        <div className="fixed inset-0 z-[9999] flex flex-col bg-black/95 backdrop-blur-xl">
          <div className="flex h-16 items-center justify-between px-6 bg-gradient-to-b from-black/80 to-transparent">
            {/* Modal Header content, e.g. camera name */}
            {(() => {
              const hwMatch = visibleHwCameras.find(d => `HW:${d.deviceId}` === expandedCameraId);
              const camMatch = filteredCameras.find(camera => camera.id === expandedCameraId);

              if (hwMatch) {
                return (
                  <div className="flex items-center gap-3">
                    <span className="flex h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500"></span>
                    <span className="text-lg font-black tracking-widest text-emerald-400">HARDWARE FEED</span>
                    <span className="text-sm font-medium text-slate-400">/ {hwMatch.label || 'USB Camera'}</span>
                  </div>
                );
              }
              if (camMatch) {
                const hasVideo = Boolean(liveStream || camMatch.rtsp_url || camMatch.status === 'LIVE');
                return (
                  <div className="flex items-center gap-3">
                    <span className={`flex h-2.5 w-2.5 rounded-full ${hasVideo ? 'animate-pulse bg-emerald-500' : 'bg-blue-400'}`}></span>
                    <span className={`text-lg font-black tracking-widest ${hasVideo ? 'text-emerald-400' : 'text-blue-300'}`}>{hasVideo ? 'LIVE FEED' : 'CAMERA PREVIEW'}</span>
                    <span className="text-sm font-medium text-slate-400">/ {camMatch.id} - {camMatch.name}</span>
                  </div>
                );
              }
              return <div></div>;
            })()}

            <button
              onClick={() => setExpandedCameraId(null)}
              className="flex items-center gap-2 rounded-lg bg-white/10 px-4 py-2 text-sm font-bold tracking-widest text-white shadow-xl transition-all hover:bg-white/20 hover:scale-105"
            >
              <Minimize className="h-4 w-4" />
              CLOSE FULLSCREEN
            </button>
          </div>

          <div className="flex-1 w-full bg-black flex flex-col p-4 md:p-8 pb-8">
            {/* Fullscreen Video Rendering */}
            <div className="w-full flex-1 mx-auto max-w-[1600px] relative">
              {(() => {
                const hwMatch = visibleHwCameras.find(d => `HW:${d.deviceId}` === expandedCameraId);
                if (hwMatch) {
                  const stream = hardwareStreamsRef.current[hwMatch.deviceId];
                  return (
                    <div className="absolute inset-0 border border-emerald-500/30 rounded-xl overflow-hidden shadow-[0_0_50px_rgba(16,185,129,0.1)] bg-black">
                      <HardwareVideoPlayer stream={stream} />
                    </div>
                  );
                }

                const camMatch = filteredCameras.find(camera => camera.id === expandedCameraId);
                if (camMatch) {
                  return (
                    <div className="absolute inset-0 border border-slate-700/50 rounded-xl overflow-hidden shadow-2xl bg-black">
                      <CameraFeed
                        camera={camMatch}
                        detections={detections}
                        liveStream={liveStream}
                        showOverlay={true}
                        fit="cover"
                      />
                    </div>
                  );
                }
                return null;
              })()}
            </div>
          </div>
        </div>,
        document.body
      )}

      {/* Universal CCTV Infrastructure Connection Modal */}
      {showCctvModal && createPortal(
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-md animate-fade-in">
          <div className="relative w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-700 bg-slate-900 shadow-2xl flex flex-col max-h-[90vh]">

            {/* Modal Header */}
            <div className="flex items-center justify-between border-b border-slate-800 bg-slate-950/60 px-6 py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
                  <Cctv className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-wide">Connect CCTV Infrastructure</h3>
                  <p className="text-xs text-slate-400">Universal IP camera, NVR, RTSP & ONVIF stream adapter with continuous AI</p>
                </div>
              </div>
              <button
                onClick={() => setShowCctvModal(false)}
                className="rounded-lg p-2 text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* Modal Scrollable Body */}
            <div className="overflow-y-auto p-6 space-y-5 flex-1">
              <div className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-slate-300 mb-1 block">RTSP / HTTP Stream URL or Device Index</label>
                  <input
                    type="text"
                    value={customRtsp}
                    onChange={e => setCustomRtsp(e.target.value)}
                    placeholder="rtsp://admin:pass@192.168.1.50:554/live or 0 for USB webcam"
                    className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-3.5 py-2.5 text-sm font-mono text-white placeholder-slate-600 focus:border-indigo-500 focus:outline-none"
                  />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-xs font-medium text-slate-300 mb-1 block">Camera Display Name</label>
                    <input
                      type="text"
                      value={cctvName}
                      onChange={e => setCctvName(e.target.value)}
                      placeholder="e.g. Sector 4 East"
                      className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-3.5 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-slate-300 mb-1 block">BOP / Station Code</label>
                    <input
                      type="text"
                      value={cctvBop}
                      onChange={e => setCctvBop(e.target.value)}
                      placeholder="e.g. BOP-04"
                      className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-3.5 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                  <div className="col-span-2">
                    <label className="text-xs font-medium text-slate-300 mb-1 block">Physical Sector / Location</label>
                    <input
                      type="text"
                      value={cctvLocation}
                      onChange={e => setCctvLocation(e.target.value)}
                      placeholder="e.g. Perimeter Fence"
                      className="w-full rounded-xl border border-slate-800 bg-slate-950/80 px-3.5 py-2 text-sm text-white focus:border-indigo-500 focus:outline-none"
                    />
                  </div>
                </div>
              </div>

              {/* Probe / Stream Verification Diagnostic Card */}
              {probeResult && (
                <div className={`rounded-xl border p-4 transition-all ${probeResult.accessible
                    ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-300'
                    : 'border-red-500/40 bg-red-950/20 text-red-300'
                  }`}>
                  <div className="flex items-start justify-between gap-4">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        {probeResult.accessible ? (
                          <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                        ) : (
                          <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0" />
                        )}
                        <span className="font-bold text-sm">
                          {probeResult.accessible ? 'CCTV Handshake Verified' : 'Connection Failed'}
                        </span>
                      </div>
                      {probeResult.accessible ? (
                        <p className="text-xs text-emerald-200/80">
                          Detected resolution: <strong className="font-mono">{probeResult.resolution}</strong> @ <strong className="font-mono">{probeResult.fps} FPS</strong> (Latency: {probeResult.latency_ms}ms)
                        </p>
                      ) : (
                        <p className="text-xs text-red-200/80">{probeResult.error}</p>
                      )}
                    </div>
                    {probeResult.thumbnail && (
                      <img
                        src={probeResult.thumbnail}
                        alt="Probe thumbnail"
                        className="h-16 w-28 rounded-lg border border-emerald-500/30 object-cover shadow-md flex-shrink-0"
                      />
                    )}
                  </div>
                </div>
              )}

            </div>

            {/* Modal Footer Actions */}
            <div className="flex items-center justify-between border-t border-slate-800 bg-slate-950/80 px-6 py-4">
              <button
                type="button"
                onClick={handleProbe}
                disabled={probing}
                className="flex items-center gap-2 rounded-xl border border-slate-700 bg-slate-800 px-4 py-2.5 text-xs font-bold text-slate-200 hover:bg-slate-700 hover:text-white transition-all disabled:opacity-50"
              >
                {probing ? <Loader className="h-4 w-4 animate-spin text-indigo-400" /> : <RefreshCw className="h-4 w-4 text-indigo-400" />}
                {probing ? 'Probing Stream...' : 'Test & Probe Signal'}
              </button>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={() => setShowCctvModal(false)}
                  className="rounded-xl px-4 py-2.5 text-xs font-bold text-slate-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleDeployCctv}
                  disabled={deploying}
                  className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-indigo-600 px-5 py-2.5 text-xs font-bold text-white shadow-lg shadow-indigo-500/20 hover:from-indigo-600 hover:to-indigo-700 transition-all disabled:opacity-50"
                >
                  {deploying ? <Loader className="h-4 w-4 animate-spin text-white" /> : <Play className="h-4 w-4 text-white fill-white" />}
                  {deploying ? 'Deploying AI...' : 'Save & Start AI Surveillance'}
                </button>
              </div>
            </div>

          </div>
        </div>,
        document.body
      )}
    </div>
  );
}
