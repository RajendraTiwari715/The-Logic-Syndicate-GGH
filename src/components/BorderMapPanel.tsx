import { CircleMarker, MapContainer, Polyline, TileLayer, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { MapPin, Maximize2 } from 'lucide-react';
import type { Camera } from '../types';

interface Props {
  cameras: Camera[];
  onOpen: () => void;
}

export default function BorderMapPanel({ cameras, onOpen }: Props) {
  const locations = cameras.flatMap(camera => {
    const lat = Number(camera.mapCoord?.lat);
    const lng = Number(camera.mapCoord?.lng);
    return Number.isFinite(lat) && Number.isFinite(lng) ? [{ camera, position: [lat, lng] as [number, number] }] : [];
  });
  const center = locations[0]?.position ?? [31.605, 74.58] as [number, number];
  const mapKey = locations.map(location => location.position.join(',')).join('|') || 'empty-map';

  return (
    <section className="flex h-full min-h-[360px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-[#f9fcff] shadow-[0_2px_8px_rgba(71,103,141,0.08)]">
      <div className="flex items-center justify-between gap-3 px-3.5 py-3">
        <h2 className="text-base font-extrabold text-slate-800">Border Map</h2>
        <button
          type="button"
          onClick={onOpen}
          aria-label="Open virtual fence map"
          className="rounded-lg p-1.5 text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
        >
          <Maximize2 className="h-4 w-4" />
        </button>
      </div>
      <div className="relative min-h-[300px] flex-1 overflow-hidden border-t border-slate-100 bg-slate-100">
        <MapContainer
          key={mapKey}
          center={center}
          zoom={locations.length > 0 ? 11 : 8}
          scrollWheelZoom={false}
          zoomControl={false}
          className="h-full min-h-[300px] w-full"
        >
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {locations.length > 1 && (
            <Polyline positions={locations.map(location => location.position)} pathOptions={{ color: '#f97316', weight: 3, opacity: 0.8, dashArray: '7 7' }} />
          )}
          {locations.map(({ camera, position }) => {
            const offline = ['OFFLINE', 'DISCONNECTED', 'ERROR'].includes(camera.status);
            return (
              <CircleMarker
                key={camera.id}
                center={position}
                radius={offline ? 6 : 5}
                pathOptions={{ color: '#ffffff', weight: 2, fillColor: offline ? '#ef4444' : '#22c55e', fillOpacity: 1 }}
              >
                <Tooltip direction="top" offset={[0, -5]}>{camera.id} · {camera.name}</Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>
        {locations.length === 0 && (
          <div className="pointer-events-none absolute bottom-3 left-3 inline-flex items-center gap-1.5 rounded-lg border border-white/80 bg-white/90 px-2.5 py-1.5 text-[10px] font-semibold text-slate-600 shadow-sm">
            <MapPin className="h-3.5 w-3.5 text-orange-600" /> Add cameras to plot positions
          </div>
        )}
      </div>
    </section>
  );
}
