import { useState } from 'react';
import { Search, Calendar, ShieldAlert, Filter } from 'lucide-react';
import { useApp } from '../store';

export default function SuspiciousActivity() {
  const { showToast } = useApp();
  const [search, setSearch] = useState('');
  
  // Realistic Mock Data for Suspicious Activities
  const mockActivities = [
    {
      id: 'SA-001',
      date: '2026-09-04',
      time: '14:23:10',
      camera: 'Cam-12 Border Sector B',
      reason: 'Loitering detected near Restricted Zone for > 5 mins.',
      screenshot: '/special_forces_1788078536486.jpg', // Using available mock image
      status: 'INVESTIGATING',
      severity: 'HIGH'
    },
    {
      id: 'SA-002',
      date: '2026-09-04',
      time: '11:05:42',
      camera: 'Cam-03 Checkpoint Alpha',
      reason: 'Unattended baggage left near the perimeter wall.',
      screenshot: '/border_patrol_1788078522989.jpg',
      status: 'RESOLVED',
      severity: 'MEDIUM'
    },
    {
      id: 'SA-003',
      date: '2026-09-03',
      time: '23:45:11',
      camera: 'Cam-08 Night Vision Perimeter',
      reason: 'Multiple individuals approaching fence during curfew hours.',
      screenshot: '/border_fence_1788078549503.jpg',
      status: 'ESCALATED',
      severity: 'CRITICAL'
    },
  ];

  const filtered = mockActivities.filter(a => 
    a.reason.toLowerCase().includes(search.toLowerCase()) || 
    a.camera.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <ShieldAlert className="h-6 w-6 text-purple-500" /> Suspicious Activity Logs
          </h1>
          <p className="text-xs text-slate-600 mt-1">Detailed view of all flagged behavioral anomalies and alerts.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-4 bg-white border border-slate-200">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search by reason, camera..." 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="input pl-10 w-full"
          />
        </div>
        <div className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-lg px-3 py-2">
          <Calendar className="h-4 w-4 text-slate-500" />
          <select className="bg-transparent text-sm font-medium outline-none text-slate-700">
             <option>Today (Sep 4)</option>
             <option>Yesterday (Sep 3)</option>
             <option>Last 7 Days</option>
          </select>
        </div>
        <button className="btn-ghost flex items-center gap-2 text-slate-600">
          <Filter className="h-4 w-4" /> Filters
        </button>
      </div>

      {/* Grid of Activities */}
      <div className="space-y-4">
        {filtered.map(activity => (
          <div key={activity.id} className="card flex flex-col md:flex-row overflow-hidden border border-slate-200 hover:border-purple-300 hover:shadow-md transition-all">
            {/* Screenshot */}
            <div className="w-full md:w-72 h-48 relative bg-slate-900 flex-shrink-0">
               <img src={activity.screenshot} alt="Surveillance" className="absolute inset-0 w-full h-full object-cover opacity-90" />
               <div className="absolute top-2 left-2 badge bg-black/60 text-white backdrop-blur-sm border-slate-700">
                 {activity.date} • {activity.time}
               </div>
               {/* Faux bounding box / highlight */}
               <div className="absolute top-1/4 left-1/4 w-1/2 h-1/2 border-2 border-purple-500 rounded-sm bg-purple-500/10"></div>
            </div>
            
            {/* Details */}
            <div className="p-5 flex-1 flex flex-col justify-between bg-white">
               <div>
                 <div className="flex justify-between items-start mb-2">
                   <h3 className="font-bold text-slate-800 text-lg">{activity.camera}</h3>
                   <span className={`badge ${
                     activity.severity === 'CRITICAL' ? 'bg-red-500/10 text-red-600 border-red-500/20' : 
                     activity.severity === 'HIGH' ? 'bg-orange-500/10 text-orange-600 border-orange-500/20' : 
                     'bg-amber-500/10 text-amber-600 border-amber-500/20'
                   }`}>
                     {activity.severity} SEVERITY
                   </span>
                 </div>
                 <p className="text-sm font-medium text-purple-700 bg-purple-50 border border-purple-100 p-3 rounded-lg mb-4">
                   <strong>Flagged Reason:</strong> {activity.reason}
                 </p>
               </div>
               
               <div className="flex items-center justify-between border-t border-slate-100 pt-4 mt-auto">
                 <span className="text-xs font-bold uppercase tracking-widest text-slate-500">
                   Status: <span className={activity.status === 'RESOLVED' ? 'text-emerald-500' : 'text-slate-800'}>{activity.status}</span>
                 </span>
                 <div className="flex gap-2">
                   <button 
                     onClick={() => showToast({type: 'success', title: 'Marked as False Alarm', message: 'Activity logged.'})}
                     className="btn-ghost text-xs py-1.5"
                   >
                     False Alarm
                   </button>
                   <button 
                     onClick={() => showToast({type: 'alert', title: 'Escalated', message: 'Patrol dispatched.'})}
                     className="btn-primary text-xs py-1.5 bg-purple-600 hover:bg-purple-700"
                   >
                     Escalate & Dispatch
                   </button>
                 </div>
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
