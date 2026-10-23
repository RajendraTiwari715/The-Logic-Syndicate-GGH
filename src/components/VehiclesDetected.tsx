import React from 'react';
import { useApp } from '../store';
import { Camera, Car, ShieldAlert } from 'lucide-react';

export default function VehiclesDetected() {
  const { vehicles, watchlistPlates } = useApp();
  
  // Show only the 6 most recent vehicles
  const recentVehicles = vehicles.slice(0, 6);

  return (
    <div className="card p-4 border-slate-200 shadow-sm bg-white h-full flex flex-col">
      <div className="flex items-center justify-between border-b border-slate-200 pb-3 mb-4">
        <h2 className="text-base font-black text-slate-800 flex items-center gap-2">
          <Camera className="h-5 w-5 text-accent-600" />
          Vehicles Detected
        </h2>
        <div className="badge bg-slate-100 text-slate-600 font-mono text-xs">
          Live Feed
        </div>
      </div>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 overflow-y-auto flex-1 pr-2 pb-2">
        {recentVehicles.map((v) => {
          const isWatchlist = v.status === 'WATCHLIST' || watchlistPlates.includes(v.plateNumber.toUpperCase());
          return (
            <div 
              key={v.id} 
              className={`rounded-lg overflow-hidden border transition-all ${
                isWatchlist ? 'border-red-500 bg-red-50' : 'border-slate-200 bg-white hover:border-accent-400 hover:shadow-md'
              }`}
            >
              {/* Photo Area */}
              <div className="h-32 bg-slate-900 relative">
                {v.annotatedImage || v.image ? (
                  <img 
                    src={v.annotatedImage || v.image} 
                    alt="Vehicle" 
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Car className="h-8 w-8 text-slate-600" />
                  </div>
                )}
                
                {isWatchlist && (
                  <div className="absolute top-2 right-2 bg-red-600 text-white p-1 rounded-full shadow-lg animate-pulse">
                    <ShieldAlert className="h-4 w-4" />
                  </div>
                )}
                
                {/* Plate Crop Overlay */}
                {v.plateImage && (
                  <div className="absolute bottom-2 left-2 right-2 bg-black/70 backdrop-blur-md p-1 rounded border border-white/20 flex justify-center">
                    <img src={v.plateImage} alt="Plate" className="h-8 rounded" />
                  </div>
                )}
              </div>
              
              {/* Details Area */}
              <div className="p-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-bold text-sm bg-yellow-100 px-2 py-0.5 rounded border border-yellow-300">
                    {v.plateNumber}
                  </span>
                  <span className="text-[10px] text-slate-500 font-medium">
                    {new Date(v.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                
                <div className="grid grid-cols-2 gap-1 text-[10px] text-slate-600">
                  <div className="flex flex-col">
                    <span className="font-semibold text-slate-400">CLASS</span>
                    <span className="font-bold capitalize">{v.vehicleType}</span>
                  </div>
                  <div className="flex flex-col">
                    <span className="font-semibold text-slate-400">CAMERA</span>
                    <span className="font-bold">{v.cameraId}</span>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
        
        {recentVehicles.length === 0 && (
          <div className="col-span-full h-48 flex flex-col items-center justify-center text-slate-400">
            <Car className="h-10 w-10 mb-2 opacity-50" />
            <p className="text-sm font-medium">No vehicles detected recently</p>
          </div>
        )}
      </div>
    </div>
  );
}
