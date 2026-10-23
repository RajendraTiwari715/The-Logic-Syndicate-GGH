import { useState, useEffect, useRef } from 'react';
import { db } from '../lib/firebase';
import { collection, query, orderBy, limit, onSnapshot } from 'firebase/firestore';
import { Radio, ScanFace, Clock, AlertTriangle, ShieldCheck, Camera } from 'lucide-react';

interface FaceLog {
  id: string;
  name: string;
  status: 'Known' | 'Unknown';
  cameraId: string;
  timestamp: unknown;
  imageUrl: string;
}

export default function Tracking() {
  const [logs, setLogs] = useState<FaceLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [, setError] = useState<string | null>(null);
  const [selectedLog, setSelectedLog] = useState<FaceLog | null>(null);
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const currentVideo = videoRef.current;
    async function startCam() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (currentVideo) {
          currentVideo.srcObject = stream;
        }
      } catch (err) {
        console.error("Camera access denied or unavailable", err);
      }
    }
    startCam();

    return () => {
      if (currentVideo && currentVideo.srcObject) {
        const tracks = (currentVideo.srcObject as MediaStream).getTracks();
        tracks.forEach(t => t.stop());
      }
    };
  }, []);

  useEffect(() => {
    if (!db) {
      setError("Firebase DB is not initialized. Please configure firebase.ts with valid credentials.");
      setLoading(false);
      return;
    }

    try {
      const q = query(collection(db as any, 'face_logs'), orderBy('timestamp', 'desc'), limit(50));
      const unsubscribe = onSnapshot(q, (snapshot) => {
        const fetchedLogs: FaceLog[] = [];
        snapshot.forEach((doc) => {
          fetchedLogs.push({ id: doc.id, ...doc.data() } as FaceLog);
        });
        setLogs(fetchedLogs);
        setLoading(false);
      }, (err) => {
        console.error("Firestore listener error:", err);
        setError("Failed to listen to face_logs. Ensure Firestore rules allow read access.");
        setLoading(false);
      });

      return () => unsubscribe();
    } catch (err: unknown) {
      console.error(err);
      setError("Error setting up Firestore listener.");
      setLoading(false);
    }
  }, []);

  return (
    <div className="space-y-4 animate-fade-in h-full flex flex-col pb-10">
      <div>
        <h1 className="text-xl font-bold text-slate-900">AI Face Recognition & Logging</h1>
        <p className="text-xs text-slate-600">Real-time CCTV face detection and verification dashboard</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 flex-1">
        
        {/* Left Col: Live Webcam Feed & Status */}
        <div className="lg:col-span-4 flex flex-col gap-4 h-[calc(100vh-180px)]">
          <div className="card border-slate-200 bg-white p-4 flex flex-col flex-1">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wide flex items-center gap-2">
                <Radio className="h-4 w-4 text-orange-500 animate-pulse" />
                Live Feed (Operator Cam)
              </h3>
            </div>
            
            <div className="flex-1 rounded-lg border-2 border-slate-200 bg-slate-900 flex items-center justify-center relative overflow-hidden group">
              <video ref={videoRef} autoPlay playsInline muted className="absolute inset-0 w-full h-full object-cover" />
              {!videoRef.current?.srcObject && (
                <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500">
                  <Camera className="w-10 h-10 mb-2 opacity-50" />
                  <span className="text-xs">Requesting Camera...</span>
                </div>
              )}
            </div>
          </div>

          <div className="card p-4 bg-slate-800 text-white shadow-lg border-slate-700">
             <h4 className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-3">System Status</h4>
             <div className="space-y-2">
               <div className="flex justify-between items-center text-sm">
                 <span className="text-slate-300">AI Model</span>
                 <span className="font-semibold text-emerald-400 flex items-center gap-1"><ShieldCheck className="w-4 h-4"/> Active</span>
               </div>
               <div className="flex justify-between items-center text-sm">
                 <span className="text-slate-300">Faces Logged</span>
                 <span className="font-semibold text-white">{logs.length}</span>
               </div>
             </div>
          </div>
        </div>

        {/* Middle Col: Real-Time Logs List */}
        <div className="lg:col-span-4 flex flex-col h-[calc(100vh-180px)]">
          <div className="card bg-white border-slate-200 flex-1 flex flex-col overflow-hidden">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide flex items-center gap-2">
                <Clock className="w-4 h-4 text-slate-500" />
                Detection Logs
              </h2>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-2">
              {loading ? (
                <div className="flex justify-center items-center h-40">
                  <span className="animate-spin rounded-full h-8 w-8 border-b-2 border-orange-500"></span>
                </div>
              ) : logs.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-60 text-slate-500">
                  <ScanFace className="w-10 h-10 mb-2 opacity-50" />
                  <p className="text-sm font-medium">No faces detected yet.</p>
                </div>
              ) : (
                logs.map((log) => {
                  const isKnown = log.status === 'Known';
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  const logDate = (log.timestamp as any)?.toDate ? (log.timestamp as any).toDate() : new Date();

                  return (
                    <div 
                      key={log.id} 
                      onClick={() => setSelectedLog(log)}
                      className={`flex items-center gap-3 p-3 rounded-xl border transition-all cursor-pointer group ${selectedLog?.id === log.id ? 'bg-orange-50 border-orange-300 shadow-sm' : 'bg-white border-slate-100 hover:border-slate-200 hover:shadow-sm'}`}
                    >
                      
                      <div className="w-12 h-12 rounded-lg overflow-hidden border border-slate-200 flex-shrink-0 bg-slate-100">
                        {log.imageUrl ? (
                          <img src={log.imageUrl} alt="Face" className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center">
                            <ScanFace className="w-5 h-5 text-slate-300" />
                          </div>
                        )}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <h3 className="text-sm font-extrabold text-slate-900 truncate">
                            {isKnown ? log.name : "Unknown"}
                          </h3>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] font-medium text-slate-500">
                          <span>{logDate.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}</span>
                        </div>
                      </div>

                      <span className={`w-2 h-2 rounded-full ${isKnown ? 'bg-emerald-500' : 'bg-red-500 animate-pulse'}`} />
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Right Col: Full Details Pane */}
        <div className="lg:col-span-4 flex flex-col h-[calc(100vh-180px)]">
          <div className="card bg-white border-slate-200 flex-1 flex flex-col overflow-hidden relative">
            <div className="p-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <h2 className="text-sm font-bold text-slate-800 uppercase tracking-wide flex items-center gap-2">
                Detailed Verification
              </h2>
            </div>
            
            {selectedLog ? (
              <div className="p-6 flex flex-col h-full overflow-y-auto animate-fade-in">
                <div className="flex justify-center mb-6">
                  <div className={`relative w-48 h-48 rounded-2xl overflow-hidden border-4 shadow-lg ${selectedLog.status === 'Known' ? 'border-emerald-400 shadow-emerald-500/20' : 'border-red-400 shadow-red-500/20'}`}>
                    {selectedLog.imageUrl ? (
                      <img src={selectedLog.imageUrl} alt="Full Face" className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full bg-slate-100 flex items-center justify-center"><ScanFace className="w-12 h-12 text-slate-300"/></div>
                    )}
                  </div>
                </div>
                
                <div className="text-center mb-6">
                  <h2 className="text-2xl font-black text-slate-900 uppercase tracking-tight">{selectedLog.status === 'Known' ? selectedLog.name : 'Unknown Person'}</h2>
                  <div className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider mt-2 border ${selectedLog.status === 'Known' ? 'bg-emerald-50 text-emerald-600 border-emerald-200' : 'bg-red-50 text-red-600 border-red-200'}`}>
                    {selectedLog.status === 'Known' ? <ShieldCheck className="w-3.5 h-3.5" /> : <AlertTriangle className="w-3.5 h-3.5" />}
                    {selectedLog.status === 'Known' ? 'AUTHORIZED PERSONNEL' : 'UNAUTHORIZED'}
                  </div>
                </div>

                <div className="space-y-4">
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Time of Entry</p>
                    <p className="text-sm font-semibold text-slate-800 font-mono">
                      {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
                      {(selectedLog.timestamp as any)?.toDate ? (selectedLog.timestamp as any).toDate().toLocaleString('en-IN') : 'Unknown'}
                    </p>
                  </div>
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Source Camera ID</p>
                    <p className="text-sm font-semibold text-slate-800 font-mono">
                      {selectedLog.cameraId}
                    </p>
                  </div>
                  <div className="bg-slate-50 border border-slate-100 rounded-xl p-4">
                    <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-1">Log ID</p>
                    <p className="text-xs font-semibold text-slate-800 font-mono break-all">
                      {selectedLog.id}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-6 text-center">
                <ScanFace className="w-16 h-16 mb-4 opacity-30" />
                <p className="text-sm font-bold uppercase tracking-widest text-slate-500 mb-2">No Subject Selected</p>
                <p className="text-xs">Click on a person from the Detection Logs list to view their full identification profile.</p>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
