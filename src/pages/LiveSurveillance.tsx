import { useState, useRef, useCallback, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { useApp } from '../store';
import { api } from '../lib/api';
import CameraFeed from '../components/CameraFeed';
import ModeSelector from '../components/ModeSelector';
import { Video, Camera as CameraIcon, Shield, AlertTriangle, AlertCircle, Phone, WifiOff, Smartphone, X, Layers, Grid3x3, Activity, Loader, Maximize, Minimize, Cctv, Radio, CheckCircle2, Play, Settings, RefreshCw } from 'lucide-react';
import type { Camera, CameraMode } from '../types';

// Remove SCENARIOS as it is now in ModeSelector

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
  const { cameras, setCameraMode, detections, selectedLiveCameraIds, setSelectedLiveCameraIds, savedFences, showToast, refreshData } = useApp();
  const [gridSize, setGridSize] = useState<'2x2' | '3x3'>('2x2');
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

  const visibleCameras = selectedLiveCameraIds && selectedLiveCameraIds.length > 0
    ? cameras.filter(c => selectedLiveCameraIds.includes(c.id))
    : cameras;

  const [hardwareCameras, setHardwareCameras] = useState<MediaDeviceInfo[]>([]);
  const hardwareStreamsRef = useRef<{ [deviceId: string]: MediaStream }>({});

  const visibleHwCameras = hardwareCameras.filter(device =>
    !selectedLiveCameraIds || selectedLiveCameraIds.length === 0 || selectedLiveCameraIds.includes(`HW:${device.deviceId}`)
  );

  const isSingleCamera = (visibleCameras.length + visibleHwCameras.length) === 1;

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
    <div className="live-shell space-y-5 animate-fade-in relative pb-8">
      <div className="glass-panel live-hero p-5 sm:p-6">
        <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h1 className="text-2xl font-black tracking-tight text-slate-800">Live Surveillance</h1>
            <p className="mt-2 text-sm text-slate-600">Real-time CCTV monitoring with AI detection overlay and tactical response cues.</p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <div className="glass-chip glass-chip-success">
              <span className="status-dot bg-emerald-500 animate-pulse" />
              <span>LIVE</span>
            </div>
            <div className="glass-chip glass-chip-slate">
              <Radio className="h-3.5 w-3.5 text-red-500" />
              <span>12 channels active</span>
            </div>
            <div className="glass-chip glass-chip-slate">
              <Shield className="h-3.5 w-3.5 text-emerald-500" />
              <span>Encrypted</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="glass-metric-card border-orange-200">
          <div className="metric-top">
            <div className="metric-icon bg-orange-500/10">
              <Cctv className="h-5 w-5 text-orange-500" />
            </div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">Feeds</span>
          </div>
          <p className="metric-value mt-5">{visibleCameras.length}</p>
          <p className="metric-label">Active monitored</p>
        </div>

        <div className="glass-metric-card border-emerald-200">
          <div className="metric-top">
            <div className="metric-icon bg-emerald-500/10">
              <Shield className="h-5 w-5 text-emerald-500" />
            </div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">Status</span>
          </div>
          <p className="metric-value mt-5">{cameras.filter(c => c.status === 'ONLINE').length}</p>
          <p className="metric-label">Online cameras</p>
        </div>

        <div className="glass-metric-card border-indigo-200">
          <div className="metric-top">
            <div className="metric-icon bg-indigo-500/10">
              <Grid3x3 className="h-5 w-5 text-indigo-500" />
            </div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">Layout</span>
          </div>
          <p className="metric-value mt-5">{gridSize}</p>
          <p className="metric-label">Current grid</p>
        </div>

        <div className="glass-metric-card border-red-200">
          <div className="metric-top">
            <div className="metric-icon bg-red-500/10">
              <Radio className="h-5 w-5 text-red-500" />
            </div>
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">Signal</span>
          </div>
          <p className="metric-value mt-5">{liveStream ? 'Phone' : 'Network'}</p>
          <p className="metric-label">Input source</p>
        </div>
      </div>

      <div className="glass-panel live-toolbar p-4 sm:p-5">
        <div className="relative z-10 flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap items-center gap-2 overflow-x-auto pb-1 w-full">
            <button
              onClick={() => setSelectedLiveCameraIds(null)}
              className={`glass-chip whitespace-nowrap ${!selectedLiveCameraIds || selectedLiveCameraIds.length === 0 ? 'glass-chip-active' : 'glass-chip-slate'}`}
            >
              All Cameras
            </button>

            {/* Face & Object Detection Group */}
            <button
              onClick={() => setSelectedLiveCameraIds(['CAM-01'])}
              className={`glass-chip whitespace-nowrap flex items-center gap-1.5 ${selectedLiveCameraIds?.length === 1 && selectedLiveCameraIds.includes('CAM-01')
                  ? 'glass-chip-active border-indigo-500 text-indigo-400'
                  : 'glass-chip-slate border-indigo-500/30'
                }`}
            >
              <span className={`status-dot ${selectedLiveCameraIds?.length === 1 && selectedLiveCameraIds.includes('CAM-01') ? 'bg-indigo-400' : 'bg-slate-500'}`} />
              Face & Object Detection
            </button>

            {/* ANPR Group */}
            <button
              onClick={() => setSelectedLiveCameraIds(['CAM-05'])}
              className={`glass-chip whitespace-nowrap flex items-center gap-1.5 ${selectedLiveCameraIds?.length === 1 && selectedLiveCameraIds.includes('CAM-05')
                  ? 'glass-chip-active border-orange-500 text-orange-400'
                  : 'glass-chip-slate border-orange-500/30'
                }`}
            >
              <span className={`status-dot ${selectedLiveCameraIds?.length === 1 && selectedLiveCameraIds.includes('CAM-05') ? 'bg-orange-400' : 'bg-slate-500'}`} />
              ANPR (Gates)
            </button>

            {/* Fencing Group Chips */}
            {savedFences.map(fence => {
              const isSelected = selectedLiveCameraIds?.length === fence.cameras.length && fence.cameras.every(c => selectedLiveCameraIds?.includes(c));
              return (
                <button
                  key={fence.id}
                  onClick={() => setSelectedLiveCameraIds(fence.cameras)}
                  className={`glass-chip whitespace-nowrap ${isSelected ? 'glass-chip-active border-blue-500 text-blue-400' : 'glass-chip-slate border-blue-500/30'} flex items-center gap-1.5`}
                >
                  <Layers className="w-3.5 h-3.5 text-blue-500" />
                  {fence.name}
                </button>
              );
            })}

            {/* Location Group Chips */}
            {Array.from(new Set(cameras.map(c => c.location))).sort().map(loc => {
              const locCameras = cameras.filter(c => c.location === loc).map(c => c.id);
              const isSelected = selectedLiveCameraIds && selectedLiveCameraIds.length === locCameras.length && locCameras.every(c => selectedLiveCameraIds.includes(c));

              return (
                <button
                  key={loc}
                  onClick={() => setSelectedLiveCameraIds(locCameras)}
                  className={`glass-chip whitespace-nowrap flex items-center gap-1.5 ${isSelected ? 'glass-chip-active' : 'glass-chip-slate'}`}
                >
                  <span className={`status-dot ${isSelected ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                  {loc}
                </button>
              );
            })}

            {/* Hardware Cameras */}
            {hardwareCameras.map((device, index) => {
              const hwId = `HW:${device.deviceId}`;
              const isSelected = selectedLiveCameraIds?.length === 1 && selectedLiveCameraIds.includes(hwId);
              return (
                <button
                  key={device.deviceId}
                  onClick={() => setSelectedLiveCameraIds([hwId])}
                  className={`glass-chip whitespace-nowrap flex items-center gap-1.5 ${isSelected ? 'glass-chip-active border-emerald-500 text-emerald-400' : 'glass-chip-slate border-emerald-500/30'}`}
                >
                  <span className={`status-dot ${isSelected ? 'bg-emerald-400' : 'bg-emerald-400/50'}`} />
                  {device.label || `USB Camera ${index + 1}`}
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2 self-end lg:self-auto">
            <button
              onClick={() => setShowCctvModal(true)}
              className="flex items-center gap-1.5 rounded-xl border border-indigo-300 bg-indigo-50 px-3.5 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-indigo-700 shadow-sm transition-all hover:bg-indigo-100 hover:border-indigo-400"
            >
              <Cctv className="h-3.5 w-3.5 text-indigo-600" />
              Connect CCTV (RTSP/IP)
            </button>

            {liveStream ? (
              <button
                onClick={disconnectPhoneCamera}
                className="flex items-center gap-1.5 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-red-600 transition-colors hover:bg-red-100"
              >
                <X className="h-3.5 w-3.5" />
                Disconnect phone
              </button>
            ) : (
              <button
                onClick={connectPhoneCamera}
                disabled={connecting}
                className="flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.2em] text-emerald-700 transition-colors hover:bg-emerald-100 disabled:opacity-50"
              >
                <Smartphone className="h-3.5 w-3.5" />
                {connecting ? 'Connecting...' : 'Connect phone'}
              </button>
            )}

            <div className="glass-toggle">
              <button
                onClick={() => setGridSize('2x2')}
                className={`rounded-lg p-2 ${gridSize === '2x2' ? 'bg-orange-50 text-orange-600' : 'text-slate-600 hover:bg-slate-100'}`}
                aria-label="2x2 grid"
              >
                <Grid3x3 className="h-4 w-4" />
              </button>
              <button
                onClick={() => setGridSize('3x3')}
                className={`rounded-lg px-2.5 py-2 text-[10px] font-black uppercase tracking-[0.2em] ${gridSize === '3x3' ? 'bg-orange-50 text-orange-600' : 'text-slate-600 hover:bg-slate-100'}`}
              >
                3×3
              </button>
            </div>
          </div>
        </div>
      </div>

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

      <div className={`grid gap-4 ${gridSize === '2x2' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'} [&_.camera-card]:h-56`}>
        {visibleHwCameras.map((device, index) => {
          const hwStream = hardwareStreamsRef.current[device.deviceId];
          const hwId = `HW-${index + 1}`;
          const existingCam = cameras.find(c => c.id === hwId);
          const mockHwCam = existingCam || {
            id: hwId,
            name: device.label || `USB Camera ${index + 1}`,
            location: 'Local System',
            bop: 'Command Center',
            status: 'ONLINE' as const,
            fps: 30,
            camera_mode: 'ALL' as const,
            recording: false,
          };

          return (
            <div key={device.deviceId} className="space-y-2 relative hover:z-50 focus-within:z-50">
              <div className="camera-card relative">
                <CameraFeed
                  camera={mockHwCam as unknown as Camera}
                  detections={detections}
                  liveStream={hwStream || null}
                />
                <div className="absolute right-2 top-2 z-20 flex items-center gap-1 rounded-full border border-emerald-500/30 bg-emerald-950/80 px-2 py-1 text-[9px] font-bold uppercase tracking-[0.12em] text-emerald-300 backdrop-blur-md">
                  <Shield className="h-3 w-3" />
                  AES-256
                </div>
              </div>

              <div className="camera-meta flex items-center justify-between">
                <div className="min-w-0 flex-1">
                  <p className="truncate text-xs font-bold text-slate-800">
                    {mockHwCam.id} — {mockHwCam.name}
                    <span className="ml-1 text-blue-500">(Hardware)</span>
                  </p>
                  <p className="truncate text-[10px] text-slate-600">{mockHwCam.bop} • {mockHwCam.location}</p>
                </div>
                <div className="flex items-center gap-2">
                  <ModeSelector
                    value={mockHwCam.camera_mode}
                    onChange={(val) => setCameraMode(mockHwCam.id, val)}
                  />
                  <button
                    onClick={() => setExpandedCameraId(isExpanded ? null : mockHwCam.id)}
                    className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded"
                    title={isExpanded ? "Exit Full Screen" : "Full Screen"}
                  >
                    {isExpanded ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                  </button>
                </div>
              </div>
            </div>
          );
        })}

        {visibleCameras.map(cam => (
          <div key={cam.id} className="space-y-2 relative hover:z-50 focus-within:z-50">
            <div className="camera-card relative">
              <CameraFeed
                camera={cam}
                detections={detections}
                liveStream={liveStream}
              />
            </div>

            <div className="camera-meta flex items-center justify-between">
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-bold text-slate-800">
                  {cam.id} — {cam.name}
                  {liveStream && <span className="ml-1 text-emerald-500">(Phone)</span>}
                </p>
                <p className="truncate text-[10px] text-slate-600">{cam.bop} • {cam.location}</p>
              </div>
              <div className="flex items-center gap-2">
                <ModeSelector
                  value={cam.camera_mode || 'ALL'}
                  onChange={(val) => setCameraMode(cam.id, val)}
                  disabled={cam.status === 'OFFLINE'}
                />
                <button
                  onClick={() => setExpandedCameraId(isExpanded ? null : cam.id)}
                  className="p-1.5 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded"
                  title={isExpanded ? "Exit Full Screen" : "Full Screen"}
                >
                  {isExpanded ? <Minimize className="h-4 w-4" /> : <Maximize className="h-4 w-4" />}
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {cameras.some(c => c.status === 'OFFLINE') && (
        <div className="rounded-2xl border border-red-200 bg-red-50 p-3 shadow-sm">
          <div className="flex items-center gap-2">
            <Cctv className="h-4 w-4 text-red-500" />
            <p className="text-sm text-red-700">
              {cameras.filter(c => c.status === 'OFFLINE').length} camera(s) offline: {cameras.filter(c => c.status === 'OFFLINE').map(c => c.id).join(', ')}
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
              const camMatch = visibleCameras.find(c => c.id === expandedCameraId);

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
                return (
                  <div className="flex items-center gap-3">
                    <span className="flex h-2.5 w-2.5 animate-pulse rounded-full bg-red-500"></span>
                    <span className="text-lg font-black tracking-widest text-red-500">LIVE FEED</span>
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

                const camMatch = visibleCameras.find(c => c.id === expandedCameraId);
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
