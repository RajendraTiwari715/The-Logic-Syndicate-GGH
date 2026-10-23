import React from 'react';
import RecentVehicleLog from '../components/RecentVehicleLog';
import VehiclesDetected from '../components/VehiclesDetected';
import { Car } from 'lucide-react';

export default function VehicleDetection() {
  return (
    <div className="space-y-6 animate-fade-in pb-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <Car className="h-6 w-6 text-blue-500" /> ANPR Vehicle Detection Pipeline
          </h1>
          <p className="text-xs text-slate-600 mt-1">
            Strict real-time vehicle logging and plate extraction dashboard.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[600px]">
        {/* Vehicles Detected (Photos) - 7 columns wide */}
        <div className="lg:col-span-7 h-full">
          <VehiclesDetected />
        </div>

        {/* Recent Vehicle Log (Table) - 5 columns wide */}
        <div className="lg:col-span-5 h-full">
          <RecentVehicleLog />
        </div>
      </div>
    </div>
  );
}
