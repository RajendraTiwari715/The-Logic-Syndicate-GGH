import { useState } from 'react';
import { useApp } from '../store';
import { Search, CalendarDays, Clock, PlayCircle, Download, Camera as CameraIcon, Filter } from 'lucide-react';

// Generate mock dates for the past 7 days
const generatePastDays = (days: number) => {
  const result = [];
  for (let i = 0; i < days; i++) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    result.push(d);
  }
  return result;
};

const PAST_DAYS = generatePastDays(7);

// Mock video clips for a selected camera and day
const generateMockClips = () => {
  return [
    { id: 'clip-1', time: '08:00 AM - 12:00 PM', size: '2.4 GB', events: 12 },
    { id: 'clip-2', time: '12:00 PM - 04:00 PM', size: '2.6 GB', events: 5 },
    { id: 'clip-3', time: '04:00 PM - 08:00 PM', size: '1.9 GB', events: 18 },
    { id: 'clip-4', time: '08:00 PM - 12:00 AM', size: '1.5 GB', events: 3 },
  ];
};

export default function Cameras() {
  const { cameras } = useApp();
  const [search, setSearch] = useState('');
  const [selectedDate, setSelectedDate] = useState<Date>(PAST_DAYS[0]);
  const [selectedCam, setSelectedCam] = useState<string | null>(null);

  const filtered = cameras.filter(c =>
    !search || c.id.toLowerCase().includes(search.toLowerCase()) || c.name.toLowerCase().includes(search.toLowerCase()) || c.bop.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="space-y-4 animate-fade-in flex flex-col h-[calc(100vh-100px)]">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Day-Wise Video Archive</h1>
          <p className="text-xs text-slate-600">Access and review recorded surveillance footage organized by day.</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-600" />
            <input type="text" placeholder="Search cameras..." value={search} onChange={e => setSearch(e.target.value)} className="input pl-10 w-48 lg:w-64" />
          </div>
          <button className="btn-ghost px-3">
            <Filter className="h-4 w-4" /> Filter
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 flex-1 min-h-0">
        
        {/* Date Selector Sidebar */}
        <div className="card p-4 overflow-y-auto hidden lg:block">
           <h3 className="text-sm font-bold text-slate-900 mb-4 uppercase tracking-wider text-accent-400 flex items-center gap-2">
             <CalendarDays className="h-4 w-4" /> Select Date
           </h3>
           <div className="space-y-2">
             {PAST_DAYS.map((date, i) => {
               const isSelected = selectedDate.toDateString() === date.toDateString();
               const isToday = i === 0;
               return (
                 <button
                   key={date.toISOString()}
                   onClick={() => { setSelectedDate(date); setSelectedCam(null); }}
                   className={`w-full text-left p-3 rounded-lg border transition-colors ${
                     isSelected 
                      ? 'bg-slate-100 border-accent-500/50 text-accent-300' 
                      : 'bg-white border-slate-200 hover:bg-white/10 text-slate-700'
                   }`}
                 >
                   <div className="font-bold text-sm">
                     {isToday ? 'Today' : date.toLocaleDateString('en-US', { weekday: 'long' })}
                   </div>
                   <div className="text-[10px] text-slate-600 mt-1">
                     {date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
                   </div>
                 </button>
               )
             })}
           </div>
        </div>

        {/* Camera/Archive Viewer */}
        <div className="lg:col-span-3 card p-4 overflow-y-auto flex flex-col">
          <div className="flex items-center gap-3 mb-6 pb-4 border-b border-slate-200">
            <CalendarDays className="h-6 w-6 text-accent-400" />
            <div>
              <h2 className="text-lg font-bold text-slate-900">
                Archive for {selectedDate.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
              </h2>
              <p className="text-xs text-slate-600">Select a camera to view its recorded segments.</p>
            </div>
          </div>

          {!selectedCam ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
              {filtered.map(cam => (
                <div 
                  key={cam.id} 
                  className="card card-hover p-4 cursor-pointer border border-slate-200 hover:border-accent-500/30 flex items-center gap-3"
                  onClick={() => setSelectedCam(cam.id)}
                >
                  <div className="h-10 w-10 rounded-full bg-slate-100 flex items-center justify-center border border-slate-200 flex-shrink-0">
                    <CameraIcon className="h-4 w-4 text-slate-600" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-slate-800 truncate">{cam.name}</p>
                    <p className="text-[10px] text-slate-600 truncate">{cam.id} • {cam.bop}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col h-full animate-fade-in">
              <div className="flex items-center justify-between mb-4">
                <button onClick={() => setSelectedCam(null)} className="text-xs text-accent-400 hover:text-accent-300 font-bold tracking-wider uppercase">
                  ← Back to Cameras
                </button>
                <div className="text-sm font-bold text-slate-700 border border-slate-200 px-3 py-1 rounded bg-white">
                  {cameras.find(c => c.id === selectedCam)?.name}
                </div>
              </div>

              {/* Video Player Placeholder */}
              <div className="relative w-full aspect-video bg-black rounded-lg border border-slate-200 overflow-hidden flex items-center justify-center mb-4">
                <div className="absolute inset-0 bg-gradient-to-b from-slate-900/40 to-slate-950/80" />
                <div className="absolute inset-0 grid-overlay opacity-30" />
                <div className="relative text-center">
                  <PlayCircle className="h-16 w-16 text-slate-600 hover:text-accent-400 transition-colors cursor-pointer mx-auto mb-2" />
                  <p className="text-xs font-mono text-slate-600">Select a segment below to play</p>
                </div>
              </div>

              {/* Clips List */}
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-600 mb-3">Recorded Segments</h3>
              <div className="space-y-2">
                {generateMockClips().map(clip => (
                  <div key={clip.id} className="flex items-center justify-between p-3 rounded-lg bg-white border border-slate-200 hover:bg-slate-100/50 transition-colors group cursor-pointer">
                    <div className="flex items-center gap-4">
                      <div className="h-8 w-8 rounded bg-accent-500/10 flex items-center justify-center border border-accent-500/20 text-accent-400">
                        <Clock className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-sm font-bold text-slate-800">{clip.time}</p>
                        <p className="text-[10px] text-slate-600">{clip.events} AI Events detected</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-xs font-mono text-slate-600 bg-white px-2 py-1 rounded">{clip.size}</span>
                      <button className="p-2 text-slate-600 hover:text-emerald-400 transition-colors opacity-0 group-hover:opacity-100">
                        <Download className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
