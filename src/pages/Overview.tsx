import { useMemo, useState, type ReactNode } from 'react';
import {
  Activity,
  Bell,
  Camera as CameraIcon,
  CarFront,
  CheckCircle2,
  Clock3,
  MapPin,
  Shield,
  TriangleAlert,
  UserRound,
  type LucideIcon,
} from 'lucide-react';
import type { Alert, Camera, RiskLevel } from '../types';
import { useApp } from '../store';
import type { PageId } from '../components/Layout';
import BorderMapPanel from '../components/BorderMapPanel';
import DashboardCameraCard from '../components/DashboardCameraCard';

const DAY_MS = 24 * 60 * 60 * 1000;
const CHART_BUCKETS = 8;

interface Metric {
  label: string;
  value: number;
  note: string;
  icon: LucideIcon;
  iconTone: string;
  page: PageId;
}

function formatClock(timestamp: string) {
  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

function countLastDay(timestamps: string[], now: number) {
  const buckets = Array.from({ length: CHART_BUCKETS }, () => 0);
  timestamps.forEach(timestamp => {
    const time = new Date(timestamp).getTime();
    const age = now - time;
    if (!Number.isFinite(time) || age < 0 || age > DAY_MS) return;
    const index = Math.min(CHART_BUCKETS - 1, Math.floor((DAY_MS - age) / (DAY_MS / CHART_BUCKETS)));
    buckets[index] += 1;
  });
  return buckets;
}

function severityTone(severity: RiskLevel) {
  if (severity === 'CRITICAL' || severity === 'HIGH') return 'bg-red-50 text-red-600 border-red-200';
  if (severity === 'MEDIUM') return 'bg-amber-50 text-amber-700 border-amber-200';
  return 'bg-emerald-50 text-emerald-700 border-emerald-200';
}

function PanelHeading({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-3 px-3.5 py-3">
      <h2 className="truncate text-lg font-extrabold text-slate-800">{title}</h2>
      {action}
    </div>
  );
}

function IncidentRow({
  alert,
  image,
  selected,
  onClick,
}: {
  alert: Alert;
  image?: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      className={`flex w-full items-center gap-2.5 rounded-xl border p-2 text-left transition ${selected ? 'border-orange-200 bg-orange-50/70' : 'border-transparent hover:border-slate-200 hover:bg-slate-50'}`}
    >
      {image ? (
        <img src={image} alt="" className="h-11 w-12 shrink-0 rounded-lg object-cover" />
      ) : (
        <span aria-hidden="true" className="flex h-11 w-12 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-400">
          <CameraIcon className="h-5 w-5" />
        </span>
      )}
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5">
          <span className={`h-2 w-2 shrink-0 rounded-full ${alert.severity === 'HIGH' || alert.severity === 'CRITICAL' ? 'bg-red-500' : alert.severity === 'MEDIUM' ? 'bg-amber-500' : 'bg-emerald-500'}`} />
          <span className="truncate text-xs font-bold text-slate-800">{alert.title}</span>
        </span>
        <span className="mt-1 block truncate text-[10px] text-slate-500">{alert.where || alert.cameraId}</span>
      </span>
      <span className="shrink-0 text-[10px] font-medium tabular-nums text-slate-400">{formatClock(alert.createdAt)}</span>
    </button>
  );
}

function ActivityChart({ series }: { series: { label: string; color: string; values: number[] }[] }) {
  const maxValue = Math.max(1, ...series.flatMap(item => item.values));
  const chartTop = 10;
  const chartBottom = 92;
  const chartLeft = 24;
  const chartRight = 296;
  const xForIndex = (index: number) => chartLeft + (index / (CHART_BUCKETS - 1)) * (chartRight - chartLeft);
  const yForValue = (value: number) => chartBottom - (value / maxValue) * (chartBottom - chartTop);

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1 px-4">
        {series.map(item => (
          <span key={item.label} className="inline-flex items-center gap-1.5 text-[10px] font-semibold text-slate-500">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: item.color }} />
            {item.label}
          </span>
        ))}
      </div>
      <div className="px-3">
        <svg viewBox="0 0 320 118" className="h-[150px] w-full" role="img" aria-label="Activity counts over the last 24 hours">
          {[0, 1, 2, 3].map(line => {
            const y = chartTop + (line / 3) * (chartBottom - chartTop);
            return <line key={line} x1={chartLeft} y1={y} x2={chartRight} y2={y} stroke="#e2e8f0" strokeDasharray="3 4" />;
          })}
          {series.map(item => {
            const points = item.values.map((value, index) => `${xForIndex(index)},${yForValue(value)}`).join(' ');
            return <polyline key={item.label} points={points} fill="none" stroke={item.color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />;
          })}
          {['24h ago', '18h', '12h', '6h', 'Now'].map((label, index) => {
            const x = chartLeft + (index / 4) * (chartRight - chartLeft);
            return <text key={label} x={x} y="112" textAnchor={index === 0 ? 'start' : index === 4 ? 'end' : 'middle'} fill="#94a3b8" fontSize="8">{label}</text>;
          })}
        </svg>
      </div>
    </div>
  );
}

function CameraStatus({ cameras }: { cameras: Camera[] }) {
  const online = cameras.filter(camera => camera.status === 'ONLINE' || camera.status === 'LIVE').length;
  const offline = cameras.filter(camera => ['OFFLINE', 'DISCONNECTED', 'ERROR'].includes(camera.status)).length;
  const other = Math.max(0, cameras.length - online - offline);
  const total = cameras.length;
  const onlineEnd = total ? (online / total) * 100 : 0;
  const offlineEnd = total ? onlineEnd + (offline / total) * 100 : 0;
  const donut = total
    ? `conic-gradient(#34d399 0 ${onlineEnd}%, #fb7185 ${onlineEnd}% ${offlineEnd}%, #94a3b8 ${offlineEnd}% 100%)`
    : 'conic-gradient(#e2e8f0 0 100%)';

  const rows = [
    { label: 'Online', count: online, color: 'bg-emerald-400' },
    { label: 'Offline', count: offline, color: 'bg-rose-400' },
    { label: 'Degraded / maintenance', count: other, color: 'bg-slate-400' },
  ];

  return (
    <div className="border-t border-slate-100 px-4 pb-4 pt-3">
      <h3 className="text-xs font-extrabold text-slate-800">Camera Status</h3>
      <div className="mt-3 flex items-center justify-center gap-5 sm:justify-around">
        <div className="flex h-24 w-24 shrink-0 items-center justify-center rounded-full" style={{ background: donut }}>
          <div className="flex h-[68px] w-[68px] flex-col items-center justify-center rounded-full bg-white text-center shadow-inner">
            <span className="text-lg font-black leading-none text-slate-800">{total}</span>
            <span className="mt-1 text-[9px] font-semibold uppercase tracking-wider text-slate-400">Total</span>
          </div>
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          {rows.map(row => (
            <div key={row.label} className="flex items-center gap-2 text-[10px]">
              <span className={`h-2 w-2 shrink-0 rounded-full ${row.color}`} />
              <span className="min-w-0 flex-1 truncate text-slate-500">{row.label}</span>
              <span className="font-bold tabular-nums text-slate-700">{row.count}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default function Overview({ onNavigate }: { onNavigate: (page: PageId) => void }) {
  const {
    cameras,
    alerts,
    events,
    vehicles,
    tracks,
    faces,
    zones,
    detections,
    resolveAlert,
    setSelectedLiveCameraIds,
  } = useApp();
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const now = Date.now();

  const activeAlerts = useMemo(
    () => alerts.filter(alert => alert.status !== 'RESOLVED').sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)),
    [alerts],
  );
  const selectedAlert = activeAlerts.find(alert => alert.id === selectedAlertId) ?? activeAlerts[0] ?? null;
  const onlineCameras = cameras.filter(camera => camera.status === 'ONLINE' || camera.status === 'LIVE').length;
  const detectedPeople = detections.filter(detection => detection.objectType === 'person').length
    || tracks.filter(track => track.objectType === 'person' && track.status === 'Active').length
    || faces.filter(face => now - Date.parse(face.timestamp) <= DAY_MS).length;
  const detectedVehicles = detections.filter(detection => detection.objectType === 'vehicle').length || vehicles.length;
  const visibleCameras = cameras.slice(0, 7);
  const orderedIncidents = activeAlerts.slice(0, 4);

  const metrics: Metric[] = [
    { label: 'Total Cameras', value: cameras.length, note: `${onlineCameras} online`, icon: CameraIcon, iconTone: 'bg-emerald-50 text-emerald-600', page: 'cameras' },
    { label: 'Active Zones', value: zones.length, note: 'Configured zones', icon: Shield, iconTone: 'bg-blue-50 text-blue-600', page: 'fences' },
    { label: 'Detected Persons', value: detectedPeople, note: 'Last 24 hours', icon: UserRound, iconTone: 'bg-rose-50 text-rose-600', page: 'people' },
    { label: 'Detected Vehicles', value: detectedVehicles, note: 'Vehicle records', icon: CarFront, iconTone: 'bg-sky-50 text-sky-600', page: 'vehicles' },
    { label: 'Active Alerts', value: activeAlerts.length, note: 'Awaiting review', icon: TriangleAlert, iconTone: 'bg-red-50 text-red-600', page: 'events' },
  ];

  const chartSeries = useMemo(() => {
    const people = events.filter(event => /person|face|people/i.test(event.eventType)).map(event => event.timestamp);
    const vehicleEvents = events.filter(event => /vehicle|anpr|plate/i.test(event.eventType)).map(event => event.timestamp);
    return [
      { label: 'Persons', color: '#f43f5e', values: countLastDay(people, now) },
      { label: 'Vehicles', color: '#2563eb', values: countLastDay(vehicleEvents, now) },
      { label: 'Alerts', color: '#f59e0b', values: countLastDay(alerts.map(alert => alert.createdAt), now) },
    ];
  }, [events, alerts, now]);

  const openCamera = (cameraId: string) => {
    setSelectedLiveCameraIds([cameraId]);
    onNavigate('live');
  };

  const selectedCamera = selectedAlert ? cameras.find(camera => camera.id === selectedAlert.cameraId) : undefined;
  const previewImage = selectedAlert?.image;

  return (
    <div className="dashboard-shell animate-fade-in space-y-2 p-2 pb-3">
      <section aria-label="Operational summary" className="grid grid-cols-2 gap-2 md:grid-cols-3 2xl:grid-cols-5">
        {metrics.map(metric => {
          const Icon = metric.icon;
          return (
            <button
              key={metric.label}
              type="button"
              onClick={() => onNavigate(metric.page)}
              className="group flex min-h-[110px] items-center gap-3 rounded-xl border border-slate-200 bg-[#f9fcff] p-3.5 text-left shadow-[0_2px_8px_rgba(71,103,141,0.08)] transition hover:border-blue-200 hover:shadow-md sm:p-4"
            >
              <span className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${metric.iconTone}`}>
                <Icon className="h-6 w-6" aria-hidden="true" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-semibold text-slate-600">{metric.label}</span>
                <span className="mt-1 flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                  <span className="text-3xl font-black leading-none tabular-nums text-slate-900">{metric.value.toLocaleString('en-IN')}</span>
                  <span className="truncate text-[10px] font-semibold text-slate-400">{metric.note}</span>
                </span>
              </span>
            </button>
          );
        })}
      </section>

      <section aria-label="Surveillance cameras">
        {visibleCameras.length > 0 ? (
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 xl:grid-cols-12">
            {visibleCameras.map((camera, index) => {
              const spanClass = cameras.length === 1
                ? 'xl:col-span-12'
                : cameras.length === 2
                  ? 'xl:col-span-6'
                  : index < 3
                    ? 'xl:col-span-4'
                    : 'xl:col-span-3';
              return (
                <DashboardCameraCard
                  key={camera.id}
                  camera={camera}
                  detections={detections}
                  onOpen={() => openCamera(camera.id)}
                  spanClass={spanClass}
                />
              );
            })}
          </div>
        ) : (
          <div className="flex min-h-[210px] flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-slate-50 px-5 py-8 text-center">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white text-slate-400 shadow-sm"><CameraIcon className="h-6 w-6" /></span>
            <h3 className="mt-3 text-sm font-bold text-slate-700">No cameras connected</h3>
            <p className="mt-1 max-w-sm text-xs text-slate-500">Register a camera to see its feed and activity here.</p>
            <button type="button" onClick={() => onNavigate('cameras')} className="mt-4 rounded-lg bg-slate-900 px-3.5 py-2 text-xs font-bold text-white transition hover:bg-slate-700">Manage cameras</button>
          </div>
        )}
      </section>

      <section className="grid items-stretch gap-2 xl:grid-cols-2 2xl:grid-cols-4" aria-label="Incident and activity details">
        <BorderMapPanel cameras={cameras} onOpen={() => onNavigate('fences')} />

        <section className="flex min-h-[380px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-[#f9fcff] shadow-[0_2px_8px_rgba(71,103,141,0.08)]">
          <PanelHeading
            title="Active Incidents"
            action={<button type="button" onClick={() => onNavigate('events')} className="text-[10px] font-bold text-blue-600 hover:text-blue-800">View all</button>}
          />
          <div className="flex-1 border-t border-slate-100 px-2 py-2">
            {orderedIncidents.length > 0 ? orderedIncidents.map(alert => (
              <IncidentRow
                key={alert.id}
                alert={alert}
                image={alert.image}
                selected={alert.id === selectedAlert?.id}
                onClick={() => setSelectedAlertId(alert.id)}
              />
            )) : (
              <div className="flex h-[210px] flex-col items-center justify-center text-center">
                <CheckCircle2 className="h-8 w-8 text-emerald-500" />
                <p className="mt-2 text-xs font-bold text-slate-700">No active incidents</p>
                <p className="mt-1 text-[10px] text-slate-400">New alerts will appear here.</p>
              </div>
            )}
          </div>
        </section>

        <section className="flex min-h-[380px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-[#f9fcff] shadow-[0_2px_8px_rgba(71,103,141,0.08)]">
          <PanelHeading title="Incident Preview" />
          {selectedAlert ? (
            <div className="flex-1 border-t border-slate-100 p-3">
              <div className="relative aspect-[1.8/1] overflow-hidden rounded-xl bg-slate-900">
                {previewImage ? (
                  <img src={previewImage} alt="Incident evidence" className="absolute inset-0 h-full w-full object-cover" />
                ) : (
                  <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 bg-[radial-gradient(ellipse_at_center,_#1e293b_0%,_#0f172a_70%)] text-slate-400">
                    <CameraIcon className="h-8 w-8" />
                    <span className="text-[10px] font-semibold uppercase tracking-[0.14em]">No evidence image available</span>
                  </div>
                )}
                <div className="absolute inset-x-0 top-0 flex items-start justify-between gap-2 bg-gradient-to-b from-slate-950/70 to-transparent p-2.5">
                  <span className="rounded-md border border-white/20 bg-slate-950/50 px-2 py-1 text-[9px] font-bold uppercase tracking-wider text-white">{previewImage ? 'Evidence frame' : 'No image attached'}</span>
                  <span className={`rounded-md border px-2 py-1 text-[9px] font-bold uppercase tracking-wider ${severityTone(selectedAlert.severity)}`}>{selectedAlert.severity}</span>
                </div>
                <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-slate-950/75 to-transparent px-3 pb-2.5 pt-8">
                  <p className="truncate text-xs font-bold text-white">{selectedAlert.title}</p>
                  <p className="mt-0.5 truncate text-[10px] text-white/75">{selectedAlert.cameraId} · {formatClock(selectedAlert.createdAt)}</p>
                </div>
              </div>
              <div className="mt-3 space-y-2 text-[10px] text-slate-500">
                <p className="flex items-start gap-2"><MapPin className="mt-0.5 h-3.5 w-3.5 shrink-0 text-blue-600" /><span className="line-clamp-2">{selectedAlert.where || selectedCamera?.location || selectedAlert.cameraId}</span></p>
                <p className="flex items-center gap-2"><Clock3 className="h-3.5 w-3.5 shrink-0 text-slate-400" />{new Date(selectedAlert.createdAt).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</p>
                <p className="flex items-center gap-2"><Activity className="h-3.5 w-3.5 shrink-0 text-slate-400" />Confidence {selectedAlert.confidence}% <span className="text-slate-300">·</span> {selectedAlert.object}</p>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2">
                <button type="button" onClick={() => openCamera(selectedAlert.cameraId)} className="rounded-lg bg-blue-600 px-2.5 py-2 text-[10px] font-bold text-white transition hover:bg-blue-700">View camera</button>
                <button type="button" onClick={() => resolveAlert(selectedAlert.id)} className="rounded-lg border border-slate-200 bg-white px-2.5 py-2 text-[10px] font-bold text-slate-600 transition hover:bg-slate-50">Mark false alarm</button>
              </div>
            </div>
          ) : (
            <div className="flex min-h-[300px] flex-col items-center justify-center border-t border-slate-100 px-5 text-center">
              <Bell className="h-8 w-8 text-slate-300" />
              <p className="mt-2 text-xs font-bold text-slate-700">No incident selected</p>
              <p className="mt-1 text-[10px] text-slate-400">Incident evidence will appear here when an alert is selected.</p>
            </div>
          )}
        </section>

        <section className="flex min-h-[380px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-[#f9fcff] shadow-[0_2px_8px_rgba(71,103,141,0.08)]">
          <PanelHeading title="Live Statistics" action={<span className="rounded-lg border border-blue-100 bg-white px-2 py-1 text-[9px] font-semibold text-slate-500">Last 24 hours</span>} />
          <div className="border-t border-slate-100 py-3">
            <ActivityChart series={chartSeries} />
          </div>
          <CameraStatus cameras={cameras} />
        </section>
      </section>
    </div>
  );
}
