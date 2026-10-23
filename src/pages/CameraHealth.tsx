import { useState } from 'react';
import { Search, Cctv, Activity, AlertCircle, CheckCircle2, Wrench, Cpu, Loader2 } from 'lucide-react';
import { useApp } from '../store';

export default function CameraHealth() {
  const { showToast } = useApp();
  const [search, setSearch] = useState('');
  
  // Local state to simulate AI fixing issues
  const [resolvingIds, setResolvingIds] = useState<Record<string, boolean>>({});
  const [resolvedIds, setResolvedIds] = useState<Record<string, boolean>>({});

  // Realistic Mock Data for 20 Live Surveillance Cameras
  const mockCameras = Array.from({ length: 20 }, (_, i) => {
    const id = `CAM-${100 + i}`;
    
    // Simulate some specific faults for realism
    if (i === 4) {
      return {
        id,
        name: `Border Sector A - Node ${i}`,
        location: `Sector A, Watchtower ${i}`,
        status: 'WARNING',
        health: 65,
        lastMaintenance: '2026-08-10',
        aiDiagnostic: {
          since: '2026-09-04 10:30 AM',
          issue: 'High latency and packet loss. Frame rate dropped to 5 FPS.',
          rootCause: 'Radio frequency interference detected on 5GHz band.',
          tips: '1. Switch channel to 149.\n2. Reboot local wireless bridge.\n3. Clear cache of streaming buffer.',
          autoFixAvailable: true
        }
      };
    }
    
    if (i === 12) {
      return {
        id,
        name: `Checkpoint Alpha - Node ${i}`,
        location: `Checkpoint Alpha`,
        status: 'OFFLINE',
        health: 0,
        lastMaintenance: '2026-07-22',
        aiDiagnostic: {
          since: '2026-09-03 23:15 PM',
          issue: 'No video feed received. API timeout.',
          rootCause: 'PoE Switch Port 4 power failure. Hardware unreachable.',
          tips: '1. Dispatch technician to Checkpoint Alpha.\n2. Hard reset PoE switch.\n3. Inspect ethernet cable for physical damage.',
          autoFixAvailable: false
        }
      };
    }
    
    // Default online cameras
    return {
      id,
      name: `Surveillance Node ${i}`,
      location: `Zone ${Math.floor(i / 5) + 1} Perimeter`,
      status: 'ONLINE',
      health: 95 + Math.floor(Math.random() * 5),
      lastMaintenance: `2026-0${8 + Math.floor(Math.random() * 2)}-1${Math.floor(Math.random() * 9)}`,
      aiDiagnostic: null
    };
  });

  const handleAiFix = (id: string) => {
    setResolvingIds(prev => ({ ...prev, [id]: true }));
    showToast({ type: 'warning', title: 'AI Protocol Initiated', message: `Running automated diagnostics and fix for ${id}...` });
    
    setTimeout(() => {
      setResolvingIds(prev => ({ ...prev, [id]: false }));
      setResolvedIds(prev => ({ ...prev, [id]: true }));
      showToast({ type: 'success', title: 'Issue Resolved', message: `AI successfully restored ${id} to normal operations.` });
    }, 4000);
  };

  const filtered = mockCameras.filter(c => 
    c.name.toLowerCase().includes(search.toLowerCase()) || 
    c.id.toLowerCase().includes(search.toLowerCase())
  );

  const onlineCount = mockCameras.filter(c => c.status === 'ONLINE' || resolvedIds[c.id]).length;
  const offlineCount = mockCameras.length - onlineCount;

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Cpu className="h-6 w-6 text-emerald-500" /> System & Surveillance Health
          </h1>
          <p className="text-xs text-slate-600 mt-1">Live status of all surveillance nodes with AI-driven diagnostics and auto-healing.</p>
        </div>
      </div>

      {/* Search & Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
         <div className="md:col-span-2 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search by camera ID, name..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input pl-10 w-full h-full"
            />
         </div>
         <div className="card p-3 flex items-center gap-3 border-emerald-500/30 bg-emerald-50">
            <div className="p-2 bg-emerald-100 rounded-lg"><CheckCircle2 className="w-5 h-5 text-emerald-600" /></div>
            <div>
               <p className="text-xs font-bold text-slate-600 uppercase">Operational</p>
               <p className="text-xl font-black text-emerald-700">{onlineCount}</p>
            </div>
         </div>
         <div className="card p-3 flex items-center gap-3 border-red-500/30 bg-red-50">
            <div className="p-2 bg-red-100 rounded-lg"><AlertCircle className="w-5 h-5 text-red-600" /></div>
            <div>
               <p className="text-xs font-bold text-slate-600 uppercase">Faulty / Offline</p>
               <p className="text-xl font-black text-red-700">{offlineCount}</p>
            </div>
         </div>
      </div>

      {/* Camera List */}
      <div className="grid grid-cols-1 gap-4">
        {filtered.map(cam => {
          const isResolved = resolvedIds[cam.id];
          const isResolving = resolvingIds[cam.id];
          const currentStatus = isResolved ? 'ONLINE' : cam.status;
          const currentHealth = isResolved ? 100 : cam.health;
          
          return (
            <div key={cam.id} className={`card p-5 border-l-4 transition-all duration-500 ${
               currentStatus === 'ONLINE' ? 'border-l-emerald-500 bg-white' : 
               currentStatus === 'WARNING' ? 'border-l-amber-500 bg-amber-50/30' : 
               'border-l-red-500 bg-red-50/30'
            }`}>
               <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                  
                  {/* Info */}
                  <div className="flex-1">
                     <div className="flex items-center gap-3 mb-2">
                       <h3 className="font-bold text-lg text-slate-800">{cam.name}</h3>
                       <span className="text-xs font-mono bg-slate-100 text-slate-600 px-2 py-0.5 rounded border border-slate-200">
                         {cam.id}
                       </span>
                       
                       <span className={`badge text-[10px] font-bold ${
                          currentStatus === 'ONLINE' ? 'bg-emerald-100 text-emerald-700' : 
                          currentStatus === 'WARNING' ? 'bg-amber-100 text-amber-700 animate-pulse' : 
                          'bg-red-100 text-red-700 animate-pulse'
                       }`}>
                         {currentStatus}
                       </span>

                       {isResolved && (
                         <span className="badge bg-emerald-500 text-white text-[10px] font-bold flex items-center gap-1 shadow-sm">
                           <CheckCircle2 className="w-3 h-3" /> RESOLVED BY AI
                         </span>
                       )}
                     </div>
                     <p className="text-sm text-slate-600 mb-1"><strong>Location:</strong> {cam.location}</p>
                     
                     <div className="flex items-center gap-4 mt-3">
                       <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <Activity className="w-4 h-4" /> Health: <strong className={currentHealth > 80 ? 'text-emerald-600' : 'text-red-500'}>{currentHealth}%</strong>
                       </div>
                       <div className="flex items-center gap-1.5 text-xs text-slate-500">
                          <Wrench className="w-4 h-4" /> Last Maint: {cam.lastMaintenance}
                       </div>
                     </div>
                  </div>

                  {/* AI Diagnostics Panel (Only show if faulty and not resolved) */}
                  {cam.aiDiagnostic && !isResolved && (
                     <div className="md:w-[45%] bg-white p-4 rounded-xl border border-slate-200 shadow-md relative overflow-hidden">
                        {/* Animated overlay while resolving */}
                        {isResolving && (
                          <div className="absolute inset-0 bg-white/80 backdrop-blur-sm z-10 flex flex-col items-center justify-center">
                            <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-2" />
                            <p className="text-xs font-bold text-slate-700 tracking-widest uppercase">AI Auto-Healing in progress...</p>
                          </div>
                        )}

                        <div className="flex items-center gap-2 mb-3 border-b border-slate-100 pb-2">
                           <Cpu className="w-4 h-4 text-blue-500" />
                           <h4 className="text-xs font-black text-slate-800 uppercase tracking-widest">AI Diagnostic Report</h4>
                        </div>
                        
                        <div className="space-y-3">
                          <div>
                            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Detected Issue (Since {cam.aiDiagnostic.since})</p>
                            <p className="text-xs text-slate-800 font-medium">{cam.aiDiagnostic.issue}</p>
                          </div>
                          
                          <div className="bg-slate-50 p-2 rounded border border-slate-100">
                            <p className="text-[10px] font-bold text-red-500 uppercase tracking-widest mb-1">Root Cause Analysis</p>
                            <p className="text-xs text-slate-700 font-mono">{cam.aiDiagnostic.rootCause}</p>
                          </div>

                          <div>
                            <p className="text-[10px] font-bold text-emerald-600 uppercase tracking-widest mb-1">Recommended Fix / Tips</p>
                            <ul className="text-xs text-slate-600 list-none space-y-1">
                              {cam.aiDiagnostic.tips.split('\n').map((tip, i) => (
                                <li key={i} className="flex gap-1.5"><span className="text-emerald-500">✓</span> {tip}</li>
                              ))}
                            </ul>
                          </div>

                          {/* Action Button */}
                          <div className="pt-2 mt-2 border-t border-slate-100">
                            {cam.aiDiagnostic.autoFixAvailable ? (
                              <button 
                                onClick={() => handleAiFix(cam.id)}
                                className="w-full btn-primary bg-blue-600 hover:bg-blue-700 text-xs py-2 uppercase tracking-widest font-bold flex justify-center items-center gap-2 shadow-lg shadow-blue-500/30"
                              >
                                <Cpu className="w-4 h-4" /> Execute AI Auto-Fix
                              </button>
                            ) : (
                              <button disabled className="w-full btn-ghost text-xs py-2 uppercase tracking-widest font-bold border border-slate-200 text-slate-400 cursor-not-allowed">
                                Manual Intervention Required
                              </button>
                            )}
                          </div>

                        </div>
                     </div>
                  )}
               </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
