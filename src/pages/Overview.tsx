import { useApp } from '../store';
import {
  Cctv, Bell, Users, Car, Fence, Activity,
  ShieldAlert, ArrowUpRight, Database, Shield,
  RadioTower, Clock3, ChevronRight
} from 'lucide-react';

import type { PageId } from '../components/Layout';

export default function Overview({ onNavigate }: { onNavigate: (p: PageId) => void }) {
  const { cameras, alerts, events, vehicles, tracks, faces } = useApp();

  const onlineCameras = cameras.filter(c => c.status === 'ONLINE').length;
  const activeAlerts = alerts.filter(a => a.status !== 'RESOLVED').length;
  const peopleDetected = faces.length > 0 ? faces.length : tracks.filter(t => t.objectType === 'person').length;
  const vehiclesDetected = vehicles.length;
  const intrusionsToday = events.filter(e => e.eventType.includes('Intrusion') || e.eventType.includes('Fence')).length;
  const suspiciousActivities = events.filter(e => e.eventType.includes('Suspicious') || e.eventType.includes('Loitering')).length;
  const avgHealth = Math.round(cameras.reduce((s, c) => s + c.health, 0) / (cameras.length || 1));

  const kpis: { label: string; value: number | string; icon: React.ElementType; color: string; bg: string; border: string; page: PageId }[] = [
    { label: 'Activity Alerts', value: activeAlerts, icon: Bell, color: 'text-red-500', bg: 'bg-red-500/10', border: 'border-red-200', page: 'events' },
    { label: 'Vehicles Detected', value: vehiclesDetected, icon: Car, color: 'text-blue-500', bg: 'bg-blue-500/10', border: 'border-blue-200', page: 'vehicles' },
    { label: 'Intrusions Today', value: intrusionsToday, icon: Fence, color: 'text-orange-500', bg: 'bg-orange-500/10', border: 'border-orange-200', page: 'intrusions' },
    { label: 'Suspicious Activities', value: suspiciousActivities, icon: ShieldAlert, color: 'text-purple-500', bg: 'bg-purple-500/10', border: 'border-purple-200', page: 'suspicious' },
    { label: 'People Detected', value: peopleDetected, icon: Users, color: 'text-amber-500', bg: 'bg-amber-500/10', border: 'border-amber-200', page: 'faces' },
    { label: 'System Health', value: `${avgHealth}%`, icon: Activity, color: 'text-emerald-500', bg: 'bg-emerald-500/10', border: 'border-emerald-200', page: 'camera_health' },
  ];

  const perimeterPulse = [72, 88, 79, 92, 85, 94, 80, 90];

  const alertsList = [
    { title: 'Fence breach near Gate 13', time: '2 mins ago', level: 'High', tone: 'bg-red-500/10 text-red-600 border-red-200' },
    { title: 'Suspicious loitering detected', time: '12 mins ago', level: 'Medium', tone: 'bg-amber-500/10 text-amber-600 border-amber-200' },
    { title: 'Vehicle mismatch flagged', time: '22 mins ago', level: 'Low', tone: 'bg-emerald-500/10 text-emerald-600 border-emerald-200' },
  ];

  return (
    <div className="dashboard-shell space-y-6 animate-fade-in pb-10">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="text-2xl font-black tracking-tight text-slate-800">Command Overview</h2>
        </div>


      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-7">
        {kpis.map(kpi => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.label}
              onClick={() => onNavigate(kpi.page)}
              className={`relative cursor-pointer overflow-hidden rounded-xl border bg-white p-3 shadow-sm transition-all duration-200 hover:border-slate-300 hover:bg-slate-50 ${kpi.border}`}
            >
              <div className="relative z-10 flex items-start justify-between">
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg border ${kpi.bg} shadow-sm border-white/50`}>
                  <Icon className={`h-4 w-4 ${kpi.color}`} />
                </div>
                <ArrowUpRight className="h-3 w-3 text-slate-400" />
              </div>
              <div className="relative z-10 mt-3">
                <p className="text-xl font-black tracking-tight text-slate-800">{kpi.value}</p>
                <p className="mt-0.5 text-[9px] font-bold uppercase tracking-widest text-slate-500">{kpi.label}</p>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.5fr_0.9fr]">
        <section className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="relative z-10 flex items-center justify-between gap-3">
            <div>
              <p className="text-[9px] font-black uppercase tracking-widest text-slate-500">Perimeter watch</p>
              <h3 className="text-base font-black text-slate-800">Sector health map</h3>
            </div>
            <button type="button" className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-indigo-600">
              View all
            </button>
          </div>

          <div className="relative z-10 mt-4 grid gap-2 md:grid-cols-8">
            {perimeterPulse.map((value, index) => (
              <div key={index} className="flex flex-col items-center gap-1.5">
                <div className="w-full rounded bg-slate-100 p-0.5">
                  <div
                    className="rounded bg-slate-600"
                    style={{ height: `${value}%` }}
                  />
                </div>
                <span className="text-[9px] font-bold uppercase tracking-wider text-slate-500">
                  S{index + 1}
                </span>
              </div>
            ))}
          </div>

          <div className="relative z-10 mt-5 grid gap-3 md:grid-cols-3">
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 shadow-sm">
              <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Camera uptime</p>
              <p className="mt-1 text-lg font-black tracking-tight text-slate-800">96.4%</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-2 shadow-sm">
              <p className="text-[9px] font-bold uppercase tracking-widest text-slate-500">Manual checks</p>
              <p className="mt-1 text-lg font-black tracking-tight text-slate-800">08</p>
            </div>
          </div>
        </section>

        <section className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className="relative z-10 flex items-center justify-between gap-3">
            <div>
              <p className="text-[9px] font-black uppercase tracking-widest text-slate-500">Alerts</p>
              <h3 className="text-base font-black text-slate-800">Latest events</h3>
            </div>
            <button type="button" className="text-[10px] font-bold uppercase tracking-wider text-slate-500 hover:text-indigo-600">
              Live Feed
            </button>
          </div>

          <div className="relative z-10 mt-3 space-y-2">
            {alertsList.map((alert) => (
              <div key={alert.title} className="flex items-center justify-between gap-2 rounded-lg border border-slate-100 bg-slate-50/50 p-2">
                <div className="flex items-start gap-2">
                  <div className="mt-1.5 h-1.5 w-1.5 rounded-full bg-slate-500" />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-bold text-slate-800">{alert.title}</p>
                    <p className="mt-0.5 text-[9px] font-semibold uppercase tracking-wider text-slate-500">{alert.time}</p>
                  </div>
                </div>
                <span className={`inline-flex items-center rounded border px-1.5 py-0.5 text-[8px] font-bold uppercase tracking-[0.1em] ${alert.tone}`}>{alert.level}</span>
              </div>
            ))}
          </div>

          <button type="button" className="relative z-10 mt-4 flex w-full items-center justify-center gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-2 py-2 text-[10px] font-bold uppercase tracking-widest text-slate-700 transition-colors hover:bg-slate-100">
            View alert log
            <ChevronRight className="h-3.5 w-3.5" />
          </button>
        </section>
        

      </div>
    </div>
  );
}
