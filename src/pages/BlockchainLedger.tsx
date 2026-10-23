import { useState, useEffect } from 'react';
import { useApp } from '../store';
import { Database, Link2, ShieldCheck, Lock, Activity, Search, Server, Shield, Fingerprint } from 'lucide-react';

interface Block {
  height: number;
  hash: string;
  previousHash: string;
  timestamp: string;
  eventType: string;
  evidenceId: string;
  cameraId: string;
  verified: boolean;
  image?: string;
}

export default function BlockchainLedger() {
  const { alerts, vehicles } = useApp();
  const [blocks, setBlocks] = useState<Block[]>([]);
  const [search, setSearch] = useState('');

  // Generate simulated blockchain data based on real alerts and vehicles
  useEffect(() => {
    let currentHeight = 104294;
    let prevHash = '000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f'; // Genesis-like
    
    const newBlocks: Block[] = [];
    
    const allEvents = [
      ...alerts.map(a => ({ type: 'Intrusion Alert', id: a.id, cam: a.cameraId, time: a.createdAt, image: a.image })),
      ...vehicles.map(v => ({ type: 'ANPR Log', id: v.id, cam: v.cameraId, time: v.timestamp, image: v.image }))
    ].sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

    allEvents.forEach((ev, i) => {
      // Simulate SHA-256 hash generation for demo
      const hash = Array.from({length: 64}, () => Math.floor(Math.random()*16).toString(16)).join('');
      
      newBlocks.push({
        height: currentHeight + allEvents.length - i,
        hash: '0000' + hash.substring(4),
        previousHash: prevHash,
        timestamp: ev.time,
        eventType: ev.type,
        evidenceId: ev.id,
        cameraId: ev.cam,
        verified: true,
        image: ev.image
      });
      prevHash = hash;
    });

    setBlocks(newBlocks);
  }, [alerts, vehicles]);

  const filtered = blocks.filter(b => b.hash.includes(search) || b.evidenceId.includes(search) || b.cameraId.includes(search));

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Database className="w-6 h-6 text-emerald-600" />
            Blockchain Evidence Ledger
          </h1>
          <p className="text-xs text-slate-600 mt-1">Cryptographic Chain of Custody for AI Detections</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-50 text-emerald-700 rounded-lg border border-emerald-200 shadow-sm">
            <Server className="w-4 h-4" />
            <span className="text-xs font-bold uppercase tracking-widest">3 Nodes Active</span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg border border-blue-200 shadow-sm">
            <Activity className="w-4 h-4 animate-pulse" />
            <span className="text-xs font-bold uppercase tracking-widest">Network Syncing</span>
          </div>
        </div>
      </div>

      {/* Network Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard title="Total Blocks" value={blocks.length > 0 ? blocks[0].height.toLocaleString() : '0'} icon={Database} color="bg-emerald-500" />
        <StatCard title="Avg Block Time" value="1.2s" icon={Activity} color="bg-blue-500" />
        <StatCard title="Secured Events" value={blocks.length.toString()} icon={ShieldCheck} color="bg-indigo-500" />
        <StatCard title="Tamper Attempts" value="0" icon={Lock} color="bg-orange-500" />
      </div>

      <div className="card bg-white border border-slate-200 shadow-sm overflow-hidden">
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <h2 className="text-sm font-bold text-slate-800 uppercase tracking-widest flex items-center gap-2">
            <Link2 className="w-4 h-4 text-slate-500" /> Block Explorer
          </h2>
          <div className="relative w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search Hash or ID..." 
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-1.5 text-sm border border-slate-300 rounded bg-white focus:outline-none focus:ring-1 focus:ring-emerald-500"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-100/50 text-xs uppercase tracking-wider text-slate-500 font-bold border-b border-slate-200">
              <tr>
                <th className="px-6 py-3">Block Height</th>
                <th className="px-6 py-3">Event Type</th>
                <th className="px-6 py-3">Camera Node</th>
                <th className="px-6 py-3">Evidence Hash (SHA-256)</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.map(block => (
                <tr key={block.height} className="hover:bg-slate-50 transition-colors">
                  <td className="px-6 py-4 font-mono font-bold text-slate-700">#{block.height}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded text-[10px] font-bold uppercase tracking-wider ${
                      block.eventType === 'Intrusion Alert' ? 'bg-red-50 text-red-600 border border-red-100' : 'bg-blue-50 text-blue-600 border border-blue-100'
                    }`}>
                      {block.eventType}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-600 font-medium flex items-center gap-2">
                    <Server className="w-3.5 h-3.5 text-slate-400" /> {block.cameraId}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <Fingerprint className="w-4 h-4 text-emerald-500" />
                      <span className="font-mono text-xs text-slate-500 bg-slate-100 px-2 py-1 rounded border border-slate-200">
                        {block.hash.substring(0, 16)}...{block.hash.substring(block.hash.length - 8)}
                      </span>
                      {block.image && (
                        <div className="relative group cursor-pointer ml-2">
                          <div className="w-6 h-6 rounded bg-emerald-100 border border-emerald-300 flex items-center justify-center overflow-hidden">
                            <img src={block.image} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                          </div>
                          <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 w-48 bg-white border border-slate-200 shadow-xl rounded-lg p-1 opacity-0 group-hover:opacity-100 pointer-events-none transition-all z-50">
                            <img src={block.image} className="w-full h-auto rounded" />
                            <p className="text-[10px] text-center font-bold text-slate-600 mt-1 uppercase tracking-widest">Evidence Snapshot</p>
                          </div>
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-1.5 text-emerald-600 text-xs font-bold uppercase tracking-wider">
                      <Shield className="w-3.5 h-3.5" /> Immutable
                    </div>
                  </td>
                  <td className="px-6 py-4 text-slate-500 text-xs">
                    {new Date(block.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-slate-500">No blocks found matching query.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function StatCard({ title, value, icon: Icon, color }: any) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex items-center gap-4 relative overflow-hidden group">
      <div className={`absolute right-0 top-0 bottom-0 w-1 ${color}`} />
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${color} bg-opacity-10`}>
        <Icon className={`w-5 h-5 ${color.replace('bg-', 'text-')}`} />
      </div>
      <div>
        <p className="text-[11px] font-bold text-slate-500 uppercase tracking-widest">{title}</p>
        <p className="text-xl font-black text-slate-800">{value}</p>
      </div>
    </div>
  );
}
