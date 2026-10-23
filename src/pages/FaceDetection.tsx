import { useState, useRef, useEffect } from 'react';
import { useApp } from '../store';
import CameraFeed from '../components/CameraFeed';
import { ScanFace, UserCheck, UserX, AlertTriangle, Clock, MapPin, ArrowRightLeft, Camera as CameraIcon, Maximize2, Minimize2, ShieldAlert, Route } from 'lucide-react';
import type { FaceRecord, Detection } from '../types';
import { WS_BASE_URL, api } from '../lib/api';

export default function FaceDetection() {
  const { cameras, addFace, detections } = useApp();
  const [paginatedFaces, setPaginatedFaces] = useState<FaceRecord[]>([]);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [fullscreenCam, setFullscreenCam] = useState<string | null>(null);

  const entryCameras = cameras.filter(c => c.id === 'CAM-01');
  
  const fetchHistory = async (pageNum: number) => {
    try {
      setLoading(true);
      const data = await api.analytics.faces(pageNum * 20, 20);
      setPaginatedFaces(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory(page);
  }, [page]);

  const getStatusBadge = (status: FaceRecord['status']) => {
    switch (status) {
      case 'AUTHORIZED': return <span className="px-2 py-1 bg-emerald-50 text-emerald-600 rounded text-xs font-bold uppercase tracking-widest border border-emerald-100 flex items-center gap-1"><UserCheck className="w-3 h-3" /> Authorized</span>;
      case 'FLAGGED': return <span className="px-2 py-1 bg-red-50 text-red-600 rounded text-xs font-bold uppercase tracking-widest border border-red-100 flex items-center gap-1"><AlertTriangle className="w-3 h-3" /> Flagged</span>;
      case 'UNKNOWN': return <span className="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs font-bold uppercase tracking-widest border border-slate-200 flex items-center gap-1"><UserX className="w-3 h-3" /> Unknown</span>;
    }
  };

  const getDirectionBadge = (dir: FaceRecord['direction']) => {
    return (
      <span className="px-2 py-1 rounded text-xs font-bold uppercase tracking-widest border bg-slate-50 text-slate-600 border-slate-200">
        {dir}
      </span>
    );
  };



  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-slate-800 tracking-tight flex items-center gap-3">
            <ScanFace className="h-8 w-8 text-indigo-600" />
            Face & Object Detection
          </h1>
          <p className="text-slate-500 font-medium mt-1">Autonomous identity tracking and object logs across all zones.</p>
        </div>
      </div>

      {/* Fullscreen Overlay */}
      {fullscreenCam && (
        <div className="fixed inset-0 z-[100] bg-black/95 backdrop-blur-sm flex flex-col p-4 animate-in fade-in duration-200">
          <div className="flex justify-end mb-4">
            <button onClick={() => setFullscreenCam(null)} className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors font-bold tracking-wider text-sm">
              <Minimize2 className="w-5 h-5" /> CLOSE FULLSCREEN
            </button>
          </div>
          <div className="flex-1 w-full relative">
            <CameraFeed 
               camera={entryCameras.find(c => c.id === fullscreenCam)!} 
               liveStream={null} 
               detections={[]}
               fullHeight={true} 
            />
            <div className="absolute top-6 left-6 flex items-center gap-3">
              <div className="bg-red-600 animate-pulse w-3 h-3 rounded-full shadow-[0_0_10px_red]"></div>
              <span className="text-white font-mono font-bold tracking-widest text-lg drop-shadow-md">LIVE / {fullscreenCam}</span>
            </div>
          </div>
        </div>
      )}

      {/* Identity Summary Stats - real counts from backend data */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Total Records</h3>
          <p className="text-2xl font-black text-indigo-900">{paginatedFaces.length}</p>
          <p className="text-xs text-slate-400 mt-1">This page</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-emerald-200">
          <h3 className="text-xs font-bold text-emerald-600 uppercase tracking-wider mb-2">Authorized</h3>
          <p className="text-2xl font-black text-emerald-700">{paginatedFaces.filter((f: any) => f.status === 'AUTHORIZED').length}</p>
          <p className="text-xs text-slate-400 mt-1">Verified identities</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Unknown</h3>
          <p className="text-2xl font-black text-slate-700">{paginatedFaces.filter((f: any) => f.status === 'UNKNOWN').length}</p>
          <p className="text-xs text-slate-400 mt-1">Unmatched faces</p>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-sm border border-red-200">
          <h3 className="text-xs font-bold text-red-600 uppercase tracking-wider mb-2">Red Flag</h3>
          <p className="text-2xl font-black text-red-700">{paginatedFaces.filter((f: any) => f.status === 'FLAGGED' || f.status === 'WATCHLIST').length}</p>
          <p className="text-xs text-slate-400 mt-1">Watchlist matches</p>
        </div>
      </div>

      {/* Access Logs Table */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-800 font-bold text-lg">
            <ArrowRightLeft className="w-5 h-5 text-indigo-500" />
            Detection Logs
          </div>
          <div className="text-xs font-bold text-slate-500 bg-slate-100 px-3 py-1 rounded-full flex gap-3">
             <button disabled={page === 0} onClick={() => setPage(page-1)} className="hover:text-indigo-600 disabled:opacity-50">PREV</button>
             <span>PAGE {page + 1}</span>
             <button disabled={paginatedFaces.length < 20} onClick={() => setPage(page+1)} className="hover:text-indigo-600 disabled:opacity-50">NEXT</button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm whitespace-nowrap">
            <thead className="bg-slate-50 text-xs uppercase tracking-widest text-slate-500 font-bold">
              <tr>
                <th className="px-6 py-4">Subject</th>
                <th className="px-6 py-4">Snapshot</th>
                <th className="px-6 py-4">Node</th>
                <th className="px-6 py-4">Flow</th>
                <th className="px-6 py-4">Match Score</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={7} className="text-center py-10 font-bold text-slate-400">Loading History...</td></tr>
              ) : paginatedFaces.map(face => {
                const cam = cameras.find(c => c.id === face.cameraId);
                return (
                  <tr key={face.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4">
                      <div className={`font-bold text-base ${face.status === 'FLAGGED' ? 'text-red-600' : 'text-slate-800'}`}>
                        {face.identity}
                      </div>
                      <div className="flex gap-2 items-center mt-1">
                        <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                          {face.type === 'object' ? 'OBJECT' : 'HUMAN'}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500 font-medium mt-1">DB: {face.database}</div>
                    </td>
                    <td className="px-6 py-4">
                      {face.image ? (
                        <img 
                           src={face.image} 
                           alt="Detection" 
                           className="w-10 h-10 rounded-lg object-cover border border-slate-200 shadow-sm cursor-pointer hover:scale-105 transition-transform" 
                           onClick={() => {
                             const viewer = document.createElement('div');
                             viewer.className = 'fixed inset-0 z-[200] bg-black/90 flex items-center justify-center p-4 cursor-pointer';
                             viewer.onclick = () => viewer.remove();
                             const img = document.createElement('img');
                             img.src = face.image || '';
                             img.className = 'max-w-full max-h-full object-contain rounded-xl shadow-2xl';
                             viewer.appendChild(img);
                             document.body.appendChild(viewer);
                           }}
                        />
                      ) : (
                        <div className="w-10 h-10 rounded-lg bg-slate-100 border border-slate-200 flex items-center justify-center">
                          <ScanFace className="w-5 h-5 text-slate-400" />
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="font-semibold text-slate-700">
                        {cam?.name || face.cameraId}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {getDirectionBadge(face.direction)}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
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
                    <td className="px-6 py-4 text-slate-500 font-medium">
                      <div className="flex items-center gap-1.5">
                        <Clock className="w-3.5 h-3.5" />
                        {new Date(face.timestamp).toLocaleTimeString()}
                      </div>
                    </td>
                  </tr>
                );
              })}
              {!loading && paginatedFaces.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-slate-500 font-medium">
                    No access records available.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
