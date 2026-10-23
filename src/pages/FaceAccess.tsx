import { useState } from 'react';
import { useApp } from '../store';
import CameraFeed from '../components/CameraFeed';
import { ScanFace, UserCheck, UserX, AlertTriangle, Clock, MapPin, ArrowRightLeft } from 'lucide-react';
import type { FaceRecord } from '../types';

export default function FaceAccess() {
  const { cameras, faces } = useApp();
  
  // Filter for only entry/exit cameras
  const entryCameras = cameras.filter(c => c.id === 'CAM-01' || c.id === 'CAM-05');
  
  // Filter faces
  const sortedFaces = [...faces].sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

  const getStatusBadge = (status: FaceRecord['status']) => {
    switch (status) {
      case 'AUTHORIZED': return <span className="px-2 py-1 bg-emerald-50 text-emerald-600 rounded text-xs font-bold uppercase tracking-widest border border-emerald-100 flex items-center gap-1"><UserCheck className="w-3 h-3" /> Authorized</span>;
      case 'FLAGGED': return <span className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs font-bold uppercase tracking-widest border border-red-100 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Flagged</span>;
      case 'UNKNOWN': return <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs font-bold uppercase tracking-widest border border-slate-200 flex items-center gap-1"><UserX className="w-3 h-3" /> Unknown</span>;
    }
  };

  const getDirectionBadge = (dir: FaceRecord['direction']) => {
    return (
      <span className={`px-2 py-1 rounded text-xs font-bold uppercase tracking-widest border ${dir === 'Inbound' ? 'bg-blue-50 text-blue-600 border-blue-100' : 'bg-purple-50 text-purple-600 border-purple-100'}`}>
        {dir}
      </span>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
            <ScanFace className="h-8 w-8 text-indigo-600" />
            Entry/Exit Access Control
          </h1>
          <p className="text-slate-500 font-medium mt-1">Facial recognition access logs restricted to perimeter entry points.</p>
        </div>
      </div>

      {/* Live Feeds of Entry Points */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {entryCameras.map(cam => (
          <div key={cam.id} className="bg-white p-4 rounded-2xl shadow-sm border border-slate-200">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2 text-indigo-700 font-bold tracking-widest uppercase text-sm">
                <MapPin className="w-4 h-4" />
                {cam.name} ({cam.location})
              </div>
              <div className="px-2 py-1 bg-indigo-50 text-indigo-600 text-xs font-bold rounded uppercase">
                Access Node
              </div>
            </div>
            <div className="aspect-video bg-black rounded-xl overflow-hidden shadow-inner relative">
              <CameraFeed camera={cam} />
              <div className="absolute top-4 left-4 bg-black/60 backdrop-blur-sm text-white px-2 py-1 rounded text-xs font-mono border border-white/10">
                LIVENESS CHECK: ACTIVE
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Access Logs Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-5 border-b border-slate-100 flex items-center gap-3">
          <ArrowRightLeft className="w-5 h-5 text-indigo-500" />
          <h2 className="text-lg font-bold text-slate-800">Recent Entry/Exit Logs</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-50 text-xs uppercase tracking-wider text-slate-500 font-bold">
              <tr>
                <th className="px-6 py-4">Identity</th>
                <th className="px-6 py-4">Snapshot</th>
                <th className="px-6 py-4">Location</th>
                <th className="px-6 py-4">Direction</th>
                <th className="px-6 py-4">Confidence</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {sortedFaces.map(face => {
                const cam = cameras.find(c => c.id === face.cameraId);
                return (
                  <tr key={face.id} className="hover:bg-indigo-50/50 transition-colors">
                    <td className="px-6 py-4">
                      <div className="font-bold text-slate-800">{face.identity}</div>
                      <div className="text-xs text-slate-500 font-medium">DB: {face.database}</div>
                    </td>
                    <td className="px-6 py-4">
                      {face.image ? (
                        <div className="w-10 h-10 rounded-lg overflow-hidden border border-slate-200 bg-slate-100">
                          <img src={face.image} alt="Face" className="w-full h-full object-cover" />
                        </div>
                      ) : (
                        <div className="w-10 h-10 rounded-lg border border-slate-200 bg-slate-100 flex items-center justify-center">
                          <ScanFace className="w-5 h-5 text-slate-300" />
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 font-medium text-slate-700">
                        {cam?.name || face.cameraId}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getDirectionBadge(face.direction)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-2 bg-slate-100 rounded-full overflow-hidden">
                          <div 
                            className={`h-full rounded-full ${face.confidence > 90 ? 'bg-emerald-500' : 'bg-amber-500'}`}
                            style={{ width: `${face.confidence}%` }}
                          />
                        </div>
                        <span className="text-xs font-bold text-slate-600">{face.confidence}%</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getStatusBadge(face.status)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-slate-500 font-medium">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(face.timestamp).toLocaleTimeString()}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
