import { useState, useRef, useMemo, useEffect } from 'react';
import { useApp } from '../store';
import { 
  Search, ShieldAlert, CheckCircle, HelpCircle, Plus, Camera, Car, 
  Loader2, Upload, FileVideo, Image as ImageIcon, Download, Eye, 
  X, Sparkles, Filter, Check, AlertTriangle, Clock
} from 'lucide-react';
import { api } from '../lib/api';
import type { VehicleRecord } from '../types';
import CameraFeed from '../components/CameraFeed';

export default function ANPR() {
  const { vehicles, showToast, addToWatchlist, watchlistPlates, refreshData, cameras, addVehicle, updateVehicleStatus } = useApp();
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [typeFilter, setTypeFilter] = useState('ALL');
  const [selectedVehicle, setSelectedVehicle] = useState<VehicleRecord | null>(null);
  const [inspectorTab, setInspectorTab] = useState<'annotated' | 'crop'>('annotated');

  const fileInputRef = useRef<HTMLInputElement>(null);
  const vehicleImageInputRef = useRef<HTMLInputElement>(null);
  const recordedVideoInputRef = useRef<HTMLInputElement>(null);
  
  // Registration Form State
  const [regPlate, setRegPlate] = useState('');
  const [regReason, setRegReason] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [analysisBusy, setAnalysisBusy] = useState<'image' | 'video' | null>(null);
  const [lastAnalysis, setLastAnalysis] = useState<{ count: number; firstPlate: string; mode: string } | null>(null);

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!regPlate) return;

    await addToWatchlist(regPlate, regReason);
    setRegPlate('');
    setRegReason('');
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const res = await api.analytics.uploadWatchlistPhoto(file);
      if (res.ok) {
        setRegPlate(res.plate_number);
        showToast({ type: 'success', title: 'OCR Successful', message: `Extracted plate ${res.plate_number} from image.` });
        await addToWatchlist(res.plate_number, 'Extracted from uploaded reference photo');
        await refreshData();
      }
    } catch (err: any) {
      showToast({ type: 'alert', title: 'OCR Failed', message: err.message || 'Failed to extract text from photo.' });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleAnalyzeMedia = async (e: React.ChangeEvent<HTMLInputElement>, mode: 'image' | 'video') => {
    const file = e.target.files?.[0];
    if (!file) return;

    setAnalysisBusy(mode);
    try {
      const res = mode === 'image'
        ? await api.analytics.analyzeAnprImage(file)
        : await api.analytics.analyzeAnprVideo(file);

      const captures = res.captures || [];
      const count = Number(res.count ?? captures.length);
      const firstPlate = captures[0]?.plateNumber || '';
      
      setLastAnalysis({ count, firstPlate, mode });

      if (count > 0) {
        showToast({ 
          type: 'success', 
          title: 'ANPR Complete', 
          message: `${count} vehicle capture${count === 1 ? '' : 's'} recorded.${firstPlate ? ` First: ${firstPlate}` : ''}` 
        });
        if (captures[0]) {
          setSelectedVehicle(captures[0]);
        }
      } else {
        showToast({ type: 'warning', title: 'No Plate Found', message: res.message || 'No readable number plate was found in the media.' });
      }
      await refreshData();
    } catch (err: any) {
      showToast({ type: 'alert', title: 'ANPR Failed', message: err.message || 'Failed to analyze media.' });
    } finally {
      setAnalysisBusy(null);
      if (mode === 'image' && vehicleImageInputRef.current) vehicleImageInputRef.current.value = '';
      if (mode === 'video' && recordedVideoInputRef.current) recordedVideoInputRef.current.value = '';
    }
  };

  // Unique state codes and vehicle types from vehicles
  const availableStates = useMemo(() => {
    const states = new Set<string>();
    vehicles.forEach(v => {
      const code = v.stateCode || (v.plateNumber ? v.plateNumber.substring(0, 2).toUpperCase() : '');
      if (code && code.length === 2 && /^[A-Z]{2}$/.test(code)) {
        states.add(code);
      }
    });
    return Array.from(states).sort();
  }, [vehicles]);

  const availableTypes = useMemo(() => {
    const types = new Set<string>();
    vehicles.forEach(v => {
      if (v.vehicleType) types.add(v.vehicleType);
    });
    return Array.from(types).sort();
  }, [vehicles]);

  const filtered = useMemo(() => {
    return vehicles.filter(v => {
      if (search && !v.plateNumber.toLowerCase().includes(search.toLowerCase()) && !v.cameraId.toLowerCase().includes(search.toLowerCase())) {
        return false;
      }
      if (statusFilter !== 'ALL' && v.status !== statusFilter) return false;
      if (stateFilter !== 'ALL') {
        const code = v.stateCode || v.plateNumber.substring(0, 2).toUpperCase();
        if (code !== stateFilter) return false;
      }
      if (typeFilter !== 'ALL' && v.vehicleType !== typeFilter) return false;
      return true;
    });
  }, [vehicles, search, statusFilter, stateFilter, typeFilter]);

  const watchlisted = vehicles.filter(v => watchlistPlates.includes(v.plateNumber.toUpperCase()) || v.status === 'WATCHLIST');

  const exportCSV = () => {
    if (filtered.length === 0) {
      showToast({ type: 'warning', title: 'No Data', message: 'No vehicle records to export.' });
      return;
    }
    const headers = ['ID', 'Plate Number', 'Status', 'Vehicle Type', 'Camera ID', 'Direction', 'Confidence', 'Timestamp', 'Image URL'];
    const rows = filtered.map(v => [
      v.id,
      `"${v.plateNumber}"`,
      v.status,
      v.vehicleType,
      v.cameraId,
      v.direction,
      `${v.confidence}%`,
      `"${v.timestamp}"`,
      `"${v.image || ''}"`
    ]);
    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `IBVAP_ANPR_Logs_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast({ type: 'success', title: 'Export Complete', message: `Exported ${filtered.length} records to CSV.` });
  };

  return (
    <div className="space-y-4 animate-fade-in pb-10">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <Car className="h-6 w-6 text-accent-600" /> ANPR Detection
          </h1>
          <p className="text-xs text-slate-600">High-precision vehicle localization, Indian HSRP/BH-series OCR, and real-time watchlist triage.</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={exportCSV} 
            className="btn-ghost border border-slate-200 text-xs px-3 py-1.5 flex items-center gap-1.5 bg-white shadow-sm hover:bg-slate-50"
          >
            <Download className="h-3.5 w-3.5 text-slate-600" /> Export CSV
          </button>
          <div className="badge bg-slate-100 text-slate-700 border border-slate-200 text-xs font-mono">
            {vehicles.length} captures | {watchlistPlates.length} watchlist
          </div>
        </div>
      </div>

      {/* Watchlist Alert Banner */}
      {watchlisted.length > 0 && (
        <div className="card p-4 border-red-500/40 bg-red-500/10 border-l-4 border-l-red-600">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <ShieldAlert className="h-6 w-6 text-red-600 animate-pulse" />
              <div>
                <p className="text-sm font-bold text-red-800">High Risk: Watchlist Vehicle Detected</p>
                <p className="text-xs text-red-700">Plate <span className="font-mono font-bold uppercase">{watchlisted[0].plateNumber}</span> flagged at camera {watchlisted[0].cameraId}</p>
              </div>
            </div>
            <button 
              onClick={() => setSelectedVehicle(watchlisted[0])}
              className="btn-primary text-xs py-1 px-3 bg-red-600 hover:bg-red-700"
            >
              Inspect Vehicle
            </button>
          </div>
        </div>
      )}

      {/* Last Analysis Preview Banner */}
      {lastAnalysis && (
        <div className="card p-3 border-accent-300 bg-accent-50/60 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-accent-900">
            <Sparkles className="h-4 w-4 text-accent-600" />
            <span>Latest <strong>{lastAnalysis.mode.toUpperCase()}</strong> analysis processed: <strong>{lastAnalysis.count}</strong> vehicle(s) recognized.</span>
            {lastAnalysis.firstPlate && (
              <span className="font-mono bg-white px-2 py-0.5 rounded border border-accent-200 font-bold text-slate-800">
                {lastAnalysis.firstPlate}
              </span>
            )}
          </div>
          <button onClick={() => setLastAnalysis(null)} className="text-slate-400 hover:text-slate-600">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Register, Upload & Live Feed */}
        <div className="lg:col-span-4 space-y-4">
          {/* Analytics Placeholder overriding Camera source view */}
          <div className="card p-6 border-slate-200 shadow-sm bg-white">
             <h2 className="text-base font-black text-slate-800 border-b border-slate-200 pb-3 mb-4 flex items-center gap-2">
                <Car className="h-4 w-4 text-emerald-600" /> ANPR Metrics
             </h2>
             <div className="space-y-4">
                 <div className="grid grid-cols-2 gap-3">
                   <div className="p-3 bg-slate-50 border border-slate-200 rounded">
                     <p className="text-[10px] font-bold text-slate-500 uppercase">Authorized</p>
                     <p className="text-xl font-black text-emerald-600">{vehicles.filter(v => v.status === 'AUTHORIZED').length}</p>
                   </div>
                   <div className="p-3 bg-slate-50 border border-slate-200 rounded">
                     <p className="text-[10px] font-bold text-slate-500 uppercase">Watchlist</p>
                     <p className="text-xl font-black text-red-600">{vehicles.filter(v => v.status === 'WATCHLIST').length}</p>
                   </div>
                 </div>
             </div>
          </div>

          <div className="card p-6 border-slate-200 shadow-sm bg-white">
             <h2 className="text-base font-black text-slate-800 border-b border-slate-200 pb-3 mb-4 flex items-center gap-2">
                <Plus className="h-4 w-4 text-accent-600" /> Register Watchlist Plate
             </h2>
             <form onSubmit={handleRegister} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">Target Plate Number</label>
                  <div className="relative">
                    <Car className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                    <input 
                      type="text" 
                      required
                      placeholder="e.g. DL 01 AB 1234 / 22 BH 1234 AA" 
                      value={regPlate}
                      onChange={e => setRegPlate(e.target.value)}
                      className="input pl-10 font-mono font-bold text-slate-800 uppercase"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">Suspicion Details / Reason</label>
                  <textarea 
                    rows={2}
                    placeholder="Provide reason for watchlist..." 
                    value={regReason}
                    onChange={e => setRegReason(e.target.value)}
                    className="input font-medium text-sm text-slate-800 resize-none"
                  ></textarea>
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-slate-600 mb-1">Upload Reference Photo (Auto-OCR)</label>
                  <div 
                    onClick={() => !isUploading && fileInputRef.current?.click()}
                    className={`border-2 border-dashed ${isUploading ? 'border-accent-200 bg-accent-50 text-accent-500' : 'border-slate-300 hover:border-accent-400 hover:bg-slate-50 text-slate-500'} rounded-lg p-4 flex flex-col items-center justify-center transition-colors cursor-pointer`}
                  >
                    {isUploading ? <Loader2 className="h-5 w-5 mb-1.5 animate-spin text-accent-600" /> : <Camera className="h-5 w-5 mb-1.5 text-slate-400" />}
                    <span className="text-xs font-semibold">{isUploading ? 'Extracting Plate...' : 'Click to upload photo for Auto-OCR'}</span>
                  </div>
                  <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleFileChange} />
                </div>
                <button type="submit" disabled={isUploading || !regPlate.trim()} className="btn-primary w-full p-2.5 uppercase tracking-wider text-xs font-bold disabled:opacity-50">
                  Add to Watchlist
                </button>
             </form>
          </div>

          <div className="card p-6 border-slate-200 shadow-sm bg-white">
             <h2 className="text-base font-black text-slate-800 border-b border-slate-200 pb-3 mb-4 flex items-center gap-2">
                <Upload className="h-4 w-4 text-blue-600" /> Analyze Uploaded Media
             </h2>
             <p className="text-xs text-slate-500 mb-3">Upload camera images or surveillance video footage to run localized ANPR processing.</p>
             <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => !analysisBusy && vehicleImageInputRef.current?.click()}
                  disabled={!!analysisBusy}
                  className="btn-ghost border border-slate-200 p-3 justify-center text-xs font-bold gap-2 disabled:opacity-50 hover:border-accent-400 hover:bg-accent-50"
                >
                  {analysisBusy === 'image' ? <Loader2 className="h-4 w-4 animate-spin text-accent-600" /> : <ImageIcon className="h-4 w-4 text-accent-600" />}
                  Image Photo
                </button>
                <button
                  type="button"
                  onClick={() => !analysisBusy && recordedVideoInputRef.current?.click()}
                  disabled={!!analysisBusy}
                  className="btn-ghost border border-slate-200 p-3 justify-center text-xs font-bold gap-2 disabled:opacity-50 hover:border-blue-400 hover:bg-blue-50"
                >
                  {analysisBusy === 'video' ? <Loader2 className="h-4 w-4 animate-spin text-blue-600" /> : <FileVideo className="h-4 w-4 text-blue-600" />}
                  Video Feed
                </button>
             </div>
             <input type="file" ref={vehicleImageInputRef} className="hidden" accept="image/*" onChange={e => handleAnalyzeMedia(e, 'image')} />
             <input type="file" ref={recordedVideoInputRef} className="hidden" accept="video/*" onChange={e => handleAnalyzeMedia(e, 'video')} />
          </div>
        </div>

        {/* Right Column: Live Detections Grid */}
        <div className="lg:col-span-8 space-y-4">
          
          {/* Multi-Filters */}
          <div className="card p-3 space-y-2.5 bg-white border-slate-200 shadow-sm">
            <div className="flex items-center gap-2 flex-wrap">
              <div className="relative flex-1 min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
                <input 
                  type="text" 
                  placeholder="Search license plate, camera ID..." 
                  value={search} 
                  onChange={e => setSearch(e.target.value)} 
                  className="input pl-9 text-xs bg-slate-50 border-slate-200 h-9" 
                />
              </div>
              <div className="flex items-center gap-1">
                {['ALL', 'AUTHORIZED', 'WATCHLIST', 'UNKNOWN'].map(s => (
                  <button 
                    key={s} 
                    onClick={() => setStatusFilter(s)} 
                    className={`badge text-[10px] py-1 px-2.5 font-bold cursor-pointer transition-colors ${statusFilter === s ? 'bg-slate-800 text-white shadow-sm' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'}`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* State & Type Filters */}
            <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-100 flex-wrap gap-2">
              <div className="flex items-center gap-1.5 flex-wrap">
                <span className="text-[11px] font-semibold text-slate-400">State:</span>
                <button 
                  onClick={() => setStateFilter('ALL')} 
                  className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${stateFilter === 'ALL' ? 'bg-accent-100 text-accent-800' : 'text-slate-600 hover:bg-slate-100'}`}
                >
                  All
                </button>
                {availableStates.map(st => (
                  <button 
                    key={st} 
                    onClick={() => setStateFilter(st)} 
                    className={`px-1.5 py-0.5 rounded text-[10px] font-bold font-mono ${stateFilter === st ? 'bg-accent-600 text-white' : 'text-slate-600 hover:bg-slate-100'}`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              {availableTypes.length > 0 && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[11px] font-semibold text-slate-400">Type:</span>
                  <select 
                    value={typeFilter} 
                    onChange={e => setTypeFilter(e.target.value)}
                    className="text-[11px] bg-slate-50 border border-slate-200 rounded px-1.5 py-0.5 text-slate-700"
                  >
                    <option value="ALL">All Types</option>
                    {availableTypes.map(t => <option key={t} value={t}>{t}</option>)}
                  </select>
                </div>
              )}
            </div>
          </div>

          {/* Plate Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {filtered.slice(0, 40).map(v => {
              const isWatchlist = v.status === 'WATCHLIST' || watchlistPlates.includes(v.plateNumber.toUpperCase());
              return (
                <div 
                  key={v.id} 
                  onClick={() => setSelectedVehicle(v)}
                  className={`card p-4 transition-all hover:shadow-md cursor-pointer border ${isWatchlist ? 'border-red-500/40 bg-red-50/20' : 'border-slate-200 bg-white hover:border-accent-300'}`}
                >
                  <div className="relative h-32 rounded-lg bg-slate-900 mb-3 overflow-hidden border border-slate-200 group">
                    {v.annotatedImage || v.image ? (
                      <img 
                        src={v.annotatedImage || v.image} 
                        alt={`${v.vehicleType} ${v.plateNumber}`} 
                        className="absolute inset-0 h-full w-full object-cover transition-transform group-hover:scale-105" 
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-slate-800 text-slate-500">
                        <Car className="h-10 w-10 opacity-40" />
                      </div>
                    )}
                    
                    {/* Floating HUD Badge */}
                    <div className="absolute top-2 left-2 bg-black/75 backdrop-blur-md rounded px-2 py-0.5 border border-white/10">
                      <span className="text-[10px] font-mono text-white font-bold">{v.cameraId}</span>
                    </div>

                    <div className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-md rounded px-2 py-0.5 border border-amber-400/40 flex items-center gap-1">
                      <Eye className="h-3 w-3 text-amber-400" />
                      <span className="text-[10px] font-mono text-amber-300 font-bold">{v.confidence}% OCR</span>
                    </div>
                  </div>

                  {/* Plate display */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="px-2.5 py-1 rounded bg-yellow-400 text-black font-mono font-extrabold text-sm tracking-wider shadow-sm flex items-center gap-1.5 border border-yellow-500">
                      <span className="text-[9px] bg-blue-700 text-white px-1 py-0.5 rounded font-sans font-bold">IND</span>
                      {v.plateNumber}
                    </div>
                    <StatusBadge status={v.status} />
                  </div>

                  {/* Details table */}
                  <div className="space-y-1 text-xs">
                    <Row label="Vehicle Class" value={v.vehicleType || 'Vehicle'} />
                    <Row label="Detections (Session)" value={v.entryCount?.toString() || '1'} />
                    <Row label="Camera Source" value={v.cameraId} />
                    <Row label="Travel Direction" value={v.direction || 'Unknown'} />
                    {v.stateCode && <Row label="State Jurisdiction" value={v.stateCode} />}
                    <Row label="Timestamp" value={new Date(v.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: true })} />
                  </div>

                  <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between text-[11px] text-accent-700 font-semibold">
                    <span>Click for Precision HUD & Inspector</span>
                    <Eye className="h-3.5 w-3.5" />
                  </div>
                </div>
              );
            })}
          </div>

          {filtered.length === 0 && (
            <div className="card p-12 text-center text-slate-500 bg-white">
              <Car className="h-10 w-10 mx-auto mb-2 text-slate-300" />
              <p className="font-bold text-slate-700">No vehicle captures found</p>
              <p className="text-xs text-slate-400 mt-1">Try changing your search keywords or upload a new photo / video feed.</p>
            </div>
          )}
        </div>
      </div>

      {/* Vehicle Inspector Modal */}
      {selectedVehicle && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-2xl border border-slate-200">
            {/* Modal Header */}
            <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
              <div className="flex items-center gap-2.5">
                <div className="px-2.5 py-1 rounded bg-yellow-400 text-black font-mono font-extrabold text-base tracking-wider shadow-sm flex items-center gap-1 border border-yellow-500">
                  <span className="text-[9px] bg-blue-700 text-white px-1 py-0.5 rounded font-sans font-bold">IND</span>
                  {selectedVehicle.plateNumber}
                </div>
                <StatusBadge status={selectedVehicle.status} />
              </div>
              <button 
                onClick={() => setSelectedVehicle(null)} 
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="p-5 space-y-4">
              {/* Tab Selector: Annotated vs Clean Crop */}
              <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
                <button
                  onClick={() => setInspectorTab('annotated')}
                  className={`text-xs font-bold pb-1.5 px-2 border-b-2 transition-colors ${inspectorTab === 'annotated' ? 'border-accent-600 text-accent-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                >
                  Annotated HUD Detection
                </button>
                <button
                  onClick={() => setInspectorTab('crop')}
                  className={`text-xs font-bold pb-1.5 px-2 border-b-2 transition-colors ${inspectorTab === 'crop' ? 'border-accent-600 text-accent-600' : 'border-transparent text-slate-500 hover:text-slate-700'}`}
                >
                  Clean Full Image
                </button>
              </div>

              {/* Main Image Frame */}
              <div className="relative h-64 rounded-xl bg-slate-950 overflow-hidden border border-slate-200 flex items-center justify-center">
                <img 
                  src={(inspectorTab === 'annotated' ? selectedVehicle.annotatedImage : selectedVehicle.image) || selectedVehicle.image} 
                  alt="Vehicle View" 
                  className="max-h-full max-w-full object-contain cursor-pointer" 
                  title="Full clean image"
                  onClick={() => {
                    const win = window.open();
                    if (win) {
                       win.document.write(`<img src="${(inspectorTab === 'annotated' ? selectedVehicle.annotatedImage : selectedVehicle.image) || selectedVehicle.image}" style="max-width: 100%;" />`);
                    }
                  }}
                />
              </div>

              {/* Cropped Zoom Plate if available */}
              {selectedVehicle.plateImage && (
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-200 flex items-center justify-between">
                  <div>
                    <p className="text-[11px] font-bold uppercase text-slate-500">Cropped License Plate Region</p>
                    <p className="text-xs font-mono text-slate-700 font-bold">{selectedVehicle.rawText || selectedVehicle.plateNumber}</p>
                  </div>
                  <img src={selectedVehicle.plateImage} alt="Tight Plate" className="h-10 rounded border border-slate-300 shadow-sm" />
                </div>
              )}

              {/* Metric Breakdown */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">OCR Confidence</span>
                  <p className="text-lg font-black text-slate-800">{selectedVehicle.confidence}%</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Vehicle Type</span>
                  <p className="text-lg font-black text-slate-800">{selectedVehicle.vehicleType}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Camera Node</span>
                  <p className="text-lg font-black text-slate-800">{selectedVehicle.cameraId}</p>
                </div>
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
                  <span className="text-[10px] font-bold text-slate-500 uppercase">Focus Sharpness</span>
                  <p className="text-lg font-black text-slate-800">{selectedVehicle.sharpness ?? 'Optimal'}</p>
                </div>
              </div>

              {/* Vehicle History Timeline */}
              {selectedVehicle.history && selectedVehicle.history.length > 0 && (
                <div className="pt-4 border-t border-slate-200">
                  <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-2">
                    <Clock className="h-4 w-4 text-blue-500" /> Detection History
                  </h3>
                  <div className="space-y-3 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                    {selectedVehicle.history.map((h, i) => (
                      <div key={i} className="flex gap-3 items-start bg-slate-50 p-2 rounded-lg border border-slate-100">
                        {h.image ? (
                          <img src={h.image} className="w-16 h-12 object-cover rounded shadow-sm border border-slate-200" alt="History frame" />
                        ) : (
                          <div className="w-16 h-12 bg-slate-200 rounded flex items-center justify-center">
                            <Car className="w-5 h-5 text-slate-400" />
                          </div>
                        )}
                        <div>
                          <div className="text-xs font-bold text-slate-800">
                            {new Date(h.timestamp).toLocaleString('en-IN', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: true })}
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                            Camera: {h.cameraId} | Conf: {h.confidence}%
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex flex-wrap items-center gap-3 pt-3 border-t border-slate-200">
                {selectedVehicle.status !== 'AUTHORIZED' && (
                  <button 
                    onClick={() => {
                      updateVehicleStatus(selectedVehicle.plateNumber, 'AUTHORIZED');
                      setSelectedVehicle(prev => prev ? { ...prev, status: 'AUTHORIZED' } : null);
                    }} 
                    className="flex-1 btn-primary py-2.5 text-xs bg-emerald-600 hover:bg-emerald-700 flex items-center justify-center gap-1.5 min-w-[120px]"
                  >
                    <CheckCircle className="h-4 w-4" /> Mark Authorized
                  </button>
                )}

                {selectedVehicle.status !== 'WATCHLIST' && !watchlistPlates.includes(selectedVehicle.plateNumber.toUpperCase()) ? (
                  <button 
                    onClick={async () => {
                      await addToWatchlist(selectedVehicle.plateNumber, "Flagged via Inspector");
                      updateVehicleStatus(selectedVehicle.plateNumber, 'WATCHLIST');
                      setSelectedVehicle(prev => prev ? { ...prev, status: 'WATCHLIST' } : null);
                    }} 
                    className="flex-1 btn-primary py-2.5 text-xs bg-red-600 hover:bg-red-700 flex items-center justify-center gap-1.5 min-w-[120px]"
                  >
                    <ShieldAlert className="h-4 w-4" /> Add to Watchlist
                  </button>
                ) : (
                  <div className="flex-1 py-2.5 px-3 rounded bg-red-100 text-red-700 text-xs font-bold flex items-center gap-1.5 justify-center min-w-[120px]">
                    <AlertTriangle className="h-4 w-4" /> On Watchlist
                  </div>
                )}

                <a 
                  href={(selectedVehicle.annotatedImage || selectedVehicle.image)} 
                  target="_blank" 
                  rel="noreferrer" 
                  download 
                  className="btn-ghost border border-slate-200 py-2.5 px-4 text-xs font-bold text-slate-700 hover:bg-slate-50"
                >
                  Download Evidence
                </a>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'WATCHLIST') return <span className="badge bg-red-100 text-red-700 border border-red-300 font-bold flex items-center gap-1"><ShieldAlert className="h-3 w-3" /> WATCHLIST</span>;
  if (status === 'AUTHORIZED') return <span className="badge bg-emerald-100 text-emerald-700 border border-emerald-300 font-bold flex items-center gap-1"><CheckCircle className="h-3 w-3" /> AUTHORIZED</span>;
  return <span className="badge bg-slate-100 text-slate-700 border border-slate-300 font-bold flex items-center gap-1"><HelpCircle className="h-3 w-3" /> UNKNOWN</span>;
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-slate-500 font-medium">{label}:</span>
      <span className="text-slate-800 font-semibold">{value}</span>
    </div>
  );
}
