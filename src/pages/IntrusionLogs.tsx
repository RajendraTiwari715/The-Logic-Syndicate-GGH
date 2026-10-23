import { useState } from 'react';
import { Search, Calendar, Fence, MapPin, Clock, PlayCircle } from 'lucide-react';

export default function IntrusionLogs() {
  const [search, setSearch] = useState('');
  
  // Realistic Mock Data for Intrusions
  const mockIntrusions = [
    {
      id: 'INTR-001',
      date: '2026-09-04',
      time: '14:23:10',
      fenceName: 'Virtual Fence Alpha',
      location: 'Sector B - East Wall',
      camera: 'Cam-12 Border Sector B',
      photo: '/border_fence_1788078549503.jpg',
      videoUrl: '#', // Using a mock play button over the image to simulate video
      status: 'VERIFIED',
      type: 'HUMAN_CROSSING',
      objectDetails: '1x Human (Adult Male, Dark Clothing)'
    },
    {
      id: 'INTR-002',
      date: '2026-09-04',
      time: '11:05:42',
      fenceName: 'Perimeter Checkpoint',
      location: 'Checkpoint Alpha - Entry Gate',
      camera: 'Cam-03 Checkpoint Alpha',
      photo: '/border_patrol_1788078522989.jpg',
      videoUrl: '#',
      status: 'INVESTIGATING',
      type: 'VEHICLE_BREACH',
      objectDetails: '1x SUV (Unknown Plate, Speed: 45km/h)'
    },
    {
      id: 'INTR-003',
      date: '2026-09-03',
      time: '23:45:11',
      fenceName: 'Night Vision Zone',
      location: 'Sector C - Outer Perimeter',
      camera: 'Cam-08 Night Vision Perimeter',
      photo: '/special_forces_1788078536486.jpg',
      videoUrl: '#',
      status: 'RESOLVED',
      type: 'MULTIPLE_TARGETS',
      objectDetails: '3x Human (Night Vision Thermal Signature)'
    },
  ];

  const filtered = mockIntrusions.filter(i => 
    i.fenceName.toLowerCase().includes(search.toLowerCase()) || 
    i.location.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Fence className="h-6 w-6 text-orange-500" /> Virtual Fence Intrusions
          </h1>
          <p className="text-xs text-slate-600 mt-1">Daily logs of all breaches detected across virtual fencing perimeters.</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 flex flex-wrap items-center gap-4 bg-white border border-slate-200">
        <div className="relative flex-1 min-w-[250px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <input 
            type="text" 
            placeholder="Search by fence name, location..." 
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
      <div className="space-y-4">
        {filtered.map(intrusion => (
          <div key={intrusion.id} className="card p-0 flex flex-col xl:flex-row overflow-hidden border border-slate-200 hover:border-orange-300 hover:shadow-md transition-all">
            
            {/* Media Section: Photo & Video Mock */}
            <div className="w-full xl:w-[500px] flex flex-col sm:flex-row bg-slate-900 flex-shrink-0">
               {/* Snapshot */}
               <div className="w-full sm:w-1/2 h-48 sm:h-auto relative border-b sm:border-b-0 sm:border-r border-slate-700">
                  <img src={intrusion.photo} alt="Intrusion Snapshot" className="absolute inset-0 w-full h-full object-cover opacity-80" />
                  <div className="absolute top-2 left-2 badge bg-black/60 text-white backdrop-blur-sm border-none text-[10px]">
                    SNAPSHOT
                  </div>
               </div>
               
               {/* Video Clip Simulation */}
               <div className="w-full sm:w-1/2 h-48 sm:h-auto relative flex items-center justify-center group cursor-pointer hover:bg-slate-800 transition-colors">
                  <img src={intrusion.photo} alt="Intrusion Video" className="absolute inset-0 w-full h-full object-cover opacity-40 grayscale group-hover:grayscale-0 transition-all" />
                  <PlayCircle className="w-12 h-12 text-white opacity-80 group-hover:scale-110 group-hover:text-orange-500 transition-transform relative z-10" />
                  <div className="absolute top-2 left-2 badge bg-red-600 text-white border-none text-[10px] animate-pulse">
                    PLAY CLIP
                  </div>
               </div>
            </div>
            
            {/* Details */}
            <div className="p-5 xl:p-6 flex-1 flex flex-col justify-between bg-white min-w-0">
               <div>
                 <div className="flex flex-wrap justify-between items-start gap-4 mb-3">
                   <h3 className="font-bold text-slate-800 text-lg xl:text-xl">{intrusion.fenceName}</h3>
                   <span className={`badge whitespace-nowrap ${
                     intrusion.status === 'VERIFIED' ? 'bg-red-500/10 text-red-600 border-red-500/20' : 
                     intrusion.status === 'INVESTIGATING' ? 'bg-orange-500/10 text-orange-600 border-orange-500/20' : 
                     'bg-emerald-500/10 text-emerald-600 border-emerald-500/20'
                   }`}>
                     {intrusion.status}
                   </span>
                 </div>
                 
                 <div className="space-y-3 mt-4">
                   <div className="flex items-start gap-3 text-sm text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                      <MapPin className="w-4 h-4 text-slate-400 mt-0.5 flex-shrink-0" />
                      <div>
                         <p className="font-bold text-slate-700">{intrusion.location}</p>
                         <p className="text-xs text-slate-500">{intrusion.camera}</p>
                      </div>
                   </div>
                   <div className="flex items-center gap-3 text-sm text-slate-600 bg-slate-50 p-3 rounded-lg border border-slate-100">
                      <Clock className="w-4 h-4 text-slate-400 flex-shrink-0" />
                      <span className="font-medium text-slate-700">{intrusion.date} at {intrusion.time}</span>
                   </div>
                   
                   {/* Object Details */}
                   <div className="mt-4 p-3 bg-orange-50/50 border border-orange-100 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="badge bg-orange-100 text-orange-700 border-orange-200 text-xs font-bold">
                          TYPE: {intrusion.type}
                        </span>
                      </div>
                      <p className="text-sm font-semibold text-slate-700">Detected Object: <span className="text-orange-700">{intrusion.objectDetails}</span></p>
                   </div>
                 </div>
               </div>
               
               <div className="flex flex-wrap gap-3 mt-6 pt-5 border-t border-slate-100">
                 <button className="flex-1 min-w-[150px] btn-primary bg-orange-600 hover:bg-orange-700 text-xs py-2.5">
                   Dispatch Response Team
                 </button>
                 <button className="flex-1 min-w-[150px] btn-ghost border border-slate-200 text-xs py-2.5">
                   Mark False Positive
                 </button>
               </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
