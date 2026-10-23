import React from 'react';
import { useApp } from '../store';
import { Clock, ShieldAlert, CheckCircle, HelpCircle } from 'lucide-react';

export default function RecentVehicleLog() {
  const { vehicles, watchlistPlates } = useApp();

  const getStatusIcon = (status: string) => {
    if (status === 'WATCHLIST') return <ShieldAlert className="h-4 w-4 text-red-600" />;
    if (status === 'AUTHORIZED') return <CheckCircle className="h-4 w-4 text-emerald-600" />;
    return <HelpCircle className="h-4 w-4 text-slate-400" />;
  };

  return (
    <div className="card p-4 border-slate-200 shadow-sm bg-white overflow-hidden flex flex-col h-full max-h-[600px]">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-3">
        <h2 className="text-base font-black text-slate-800 flex items-center gap-2">
          <Clock className="h-5 w-5 text-accent-600" />
          Recent Vehicle Log
        </h2>
        <div className="badge bg-slate-100 text-slate-600 font-mono text-xs">
          {vehicles.length} Total
        </div>
      </div>
      
      <div className="overflow-y-auto flex-1 pr-2">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 sticky top-0 z-10">
            <tr>
              <th className="py-2 px-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Time</th>
              <th className="py-2 px-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Plate Number</th>
              <th className="py-2 px-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Type</th>
              <th className="py-2 px-3 font-semibold text-slate-600 text-xs uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {vehicles.map((v) => {
              const isWatchlist = v.status === 'WATCHLIST' || watchlistPlates.includes(v.plateNumber.toUpperCase());
              return (
                <tr key={v.id} className={`transition-colors hover:bg-slate-50 ${isWatchlist ? 'bg-red-50/50' : ''}`}>
                  <td className="py-2.5 px-3 text-slate-600 text-xs font-mono whitespace-nowrap">
                    {new Date(v.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="py-2.5 px-3">
                    <span className="font-mono font-bold text-slate-900 bg-yellow-100 px-2 py-0.5 rounded border border-yellow-300 shadow-sm">
                      {v.plateNumber}
                    </span>
                  </td>
                  <td className="py-2.5 px-3 text-slate-700 capitalize text-xs">
                    {v.vehicleType}
                  </td>
                  <td className="py-2.5 px-3">
                    <div className="flex items-center gap-1.5">
                      {getStatusIcon(isWatchlist ? 'WATCHLIST' : v.status)}
                      <span className={`text-[10px] font-bold ${isWatchlist ? 'text-red-600' : 'text-slate-500'}`}>
                        {isWatchlist ? 'WATCHLIST' : v.status}
                      </span>
                    </div>
                  </td>
                </tr>
              );
            })}
            {vehicles.length === 0 && (
              <tr>
                <td colSpan={4} className="py-8 text-center text-slate-400 text-sm">
                  No vehicles detected yet. Waiting for live stream...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
