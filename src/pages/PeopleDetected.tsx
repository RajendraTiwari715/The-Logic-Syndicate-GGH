import { useState } from 'react';
import { Search, Calendar, Users, MapPin, Clock, X, ScanFace } from 'lucide-react';
import { useApp } from '../store';
import type { FaceRecord } from '../types';

export default function PeopleDetected() {
  const [search, setSearch] = useState('');
  const [selectedPerson, setSelectedPerson] = useState<FaceRecord | null>(null);
  const { faces } = useApp();

  const filtered = faces.filter(f => 
    f.cameraId.toLowerCase().includes(search.toLowerCase()) || 
    f.identity.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Users className="h-6 w-6 text-accent-500" /> People Detected Log
          </h1>
          <p className="text-xs text-slate-600 mt-1">Comprehensive log of all human detections across the perimeter.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-4 bg-white border border-slate-200">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search by location, camera..." 
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
      </div>

      {/* List View */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
         <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
               <thead className="bg-slate-50 border-b border-slate-200">
                 <tr>
                    <th className="px-6 py-4 font-bold text-slate-600 text-xs uppercase tracking-wider">Snapshot</th>
                    <th className="px-6 py-4 font-bold text-slate-600 text-xs uppercase tracking-wider">Location & Camera</th>
                    <th className="px-6 py-4 font-bold text-slate-600 text-xs uppercase tracking-wider">Timestamp</th>
                    <th className="px-6 py-4 font-bold text-slate-600 text-xs uppercase tracking-wider">AI Details</th>
                 </tr>
               </thead>
               <tbody className="divide-y divide-slate-100">
                 {filtered.map(person => {
                   const d = new Date(person.timestamp);
                   const screenshot = person.image || person.thumbnail || '/border_patrol_1788078522989.jpg';
                   const notes = person.identity === 'Unknown' ? 'Unknown individual detected. Logged for review.' : `Matched with ${person.identity}.`;
                   
                   return (
                     <tr 
                       key={person.id} 
                       onClick={() => setSelectedPerson(person)}
                       className="hover:bg-slate-50 transition-colors cursor-pointer"
                     >
                        <td className="px-6 py-4">
                          <div className="w-24 h-16 rounded overflow-hidden relative bg-slate-900 border border-slate-200 shadow-sm">
                             <img src={screenshot} alt="Person Detected" className="absolute inset-0 w-full h-full object-cover" />
                             {/* Faux bounding box */}
                             <div className="absolute inset-2 border border-green-500 rounded-sm"></div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-start gap-2">
                             <MapPin className="w-4 h-4 text-slate-400 mt-0.5" />
                             <div>
                                <p className="font-bold text-slate-800 flex items-center gap-2">
                                  {person.identity}
                                  {person.type && (
                                    <span className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200">
                                      {person.type}
                                    </span>
                                  )}
                                </p>
                                <p className="text-xs text-slate-500 mt-1">Node: {person.cameraId}</p>
                             </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-2 text-slate-700 font-medium">
                             <Clock className="w-4 h-4 text-slate-400" />
                             {d.toLocaleDateString()} <br/> {d.toLocaleTimeString()}
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="space-y-1">
                             <span className="badge bg-green-500/10 text-green-700 border border-green-500/20 text-[10px]">
                                {person.confidence}% CONFIDENCE
                             </span>
                             <p className="text-xs text-slate-600 max-w-[200px] truncate">{notes}</p>
                          </div>
                        </td>
                     </tr>
                   );
                 })}
               </tbody>
            </table>
         </div>
      </div>

      {/* Person History Modal */}
      {selectedPerson && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200 p-5">
            <div className="flex items-start justify-between mb-4 border-b border-slate-100 pb-4">
              <div className="flex gap-4">
                <img 
                  src={selectedPerson.image || selectedPerson.thumbnail || '/border_patrol_1788078522989.jpg'} 
                  className="w-16 h-16 rounded-xl object-cover border border-slate-200 shadow-sm"
                  alt="Profile"
                />
                <div>
                  <h2 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                    {selectedPerson.identity}
                    {selectedPerson.type && (
                       <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-slate-100 text-slate-500 border border-slate-200 mt-1">
                          {selectedPerson.type}
                       </span>
                    )}
                  </h2>
                  <p className="text-sm text-slate-500 font-medium mt-1">Last seen: {new Date(selectedPerson.timestamp).toLocaleString('en-IN')}</p>
                  <p className="text-xs text-slate-400 mt-1">Total Detections: {1 + (selectedPerson.history?.length || 0)}</p>
                </div>
              </div>
              <button 
                onClick={() => setSelectedPerson(null)} 
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-bold text-slate-700 flex items-center gap-2">
                <Clock className="w-4 h-4 text-accent-500" /> Detection Timeline
              </h3>
              
              <div className="space-y-3 pl-2 border-l-2 border-slate-100 ml-2">
                {/* Current (latest) detection */}
                <div className="relative pl-6">
                  <div className="absolute left-[-29px] top-1 w-3 h-3 bg-accent-500 rounded-full border-4 border-white shadow-sm" />
                  <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex gap-3 shadow-sm">
                    <img 
                      src={selectedPerson.image || selectedPerson.thumbnail || '/border_patrol_1788078522989.jpg'} 
                      className="w-12 h-12 rounded object-cover border border-slate-200" 
                      alt="capture" 
                    />
                    <div>
                      <div className="text-sm font-bold text-slate-800">{new Date(selectedPerson.timestamp).toLocaleString('en-IN')}</div>
                      <div className="text-xs text-slate-500 mt-0.5 font-mono">Cam: {selectedPerson.cameraId} | Conf: {selectedPerson.confidence}%</div>
                    </div>
                  </div>
                </div>

                {/* History detections */}
                {selectedPerson.history?.map((h, i) => (
                  <div key={i} className="relative pl-6">
                    <div className="absolute left-[-29px] top-1 w-3 h-3 bg-slate-300 rounded-full border-4 border-white shadow-sm" />
                    <div className="bg-white p-3 rounded-lg border border-slate-100 flex gap-3 shadow-sm opacity-80 hover:opacity-100 transition-opacity">
                      {h.image ? (
                        <img src={h.image} className="w-12 h-12 rounded object-cover border border-slate-200" alt="capture" />
                      ) : (
                        <div className="w-12 h-12 rounded bg-slate-100 flex items-center justify-center border border-slate-200">
                          <ScanFace className="w-4 h-4 text-slate-400" />
                        </div>
                      )}
                      <div>
                        <div className="text-sm font-bold text-slate-700">{new Date(h.timestamp).toLocaleString('en-IN')}</div>
                        <div className="text-xs text-slate-400 mt-0.5 font-mono">Cam: {h.cameraId} | Conf: {h.confidence}%</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
