import { useState, useRef, useEffect } from 'react';
import { Activity, Shield, ScanLine, ChevronDown } from 'lucide-react';
import type { CameraMode } from '../types';

interface ModeSelectorProps {
  value: CameraMode;
  onChange: (value: CameraMode) => void;
  disabled?: boolean;
}

const MODES: { value: CameraMode; label: string; icon: any; colorClass: string; bgClass: string }[] = [
  { value: 'ALL', label: 'ALL', icon: Activity, colorClass: 'text-emerald-400', bgClass: 'bg-emerald-500/10' },
  { value: 'FACE & OBJECT', label: 'FACE & OBJECT', icon: Shield, colorClass: 'text-purple-400', bgClass: 'bg-purple-500/10' },
  { value: 'ANPR', label: 'ANPR', icon: ScanLine, colorClass: 'text-blue-400', bgClass: 'bg-blue-500/10' },
];

export default function ModeSelector({ value, onChange, disabled }: ModeSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const selectedMode = MODES.find((m) => m.value === value) || MODES[0];
  const Icon = selectedMode.icon;

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div className="relative z-[100]" ref={containerRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 backdrop-blur-md transition-all hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 ${
          disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'
        }`}
      >
        <div className={`rounded p-1 ${selectedMode.bgClass}`}>
          <Icon className={`h-3 w-3 ${selectedMode.colorClass}`} />
        </div>
        <span className="text-[10px] font-black uppercase tracking-wider text-slate-200">
          {selectedMode.label}
        </span>
        <ChevronDown
          className={`ml-1 h-3 w-3 text-slate-400 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-48 origin-top-right animate-in fade-in slide-in-from-top-2 rounded-xl border border-slate-700 bg-slate-950/95 p-1 shadow-2xl backdrop-blur-xl">
          {MODES.map((mode) => {
            const ModeIcon = mode.icon;
            const isSelected = mode.value === value;
            return (
              <button
                key={mode.value}
                type="button"
                onClick={() => {
                  onChange(mode.value);
                  setIsOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left transition-all ${
                  isSelected
                    ? 'bg-slate-800'
                    : 'hover:bg-slate-800/60'
                }`}
              >
                <div className={`rounded p-1.5 ${isSelected ? mode.bgClass : 'bg-slate-800'}`}>
                  <ModeIcon
                    className={`h-3.5 w-3.5 ${
                      isSelected ? mode.colorClass : 'text-slate-400'
                    }`}
                  />
                </div>
                <div className="flex-1">
                  <span
                    className={`block text-[11px] font-bold uppercase tracking-wider ${
                      isSelected ? 'text-white' : 'text-slate-400'
                    }`}
                  >
                    {mode.label}
                  </span>
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
