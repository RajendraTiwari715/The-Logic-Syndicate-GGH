import { useState, useEffect } from 'react';
import { useApp } from '../store';
import { ShieldAlert } from 'lucide-react';

export default function GlobalAlarm() {
  const { activeAlarm, setActiveAlarm, escalateAlert, addAlert, showToast } = useApp();
  const [timeLeft, setTimeLeft] = useState(30);

  useEffect(() => {
    let audio: HTMLAudioElement;
    let timer: number;
    if (activeAlarm) {
       // Play loud siren
       audio = new Audio('https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg');
       audio.loop = true;
       audio.play().catch(e => console.log('Autoplay blocked', e));
       
       setTimeLeft(30);
       timer = window.setInterval(() => {
          setTimeLeft(t => {
             if (t <= 1) {
                // ESCALATE!
                addAlert(activeAlarm);
                escalateAlert(activeAlarm.id);
                showToast({ type: 'warning', title: 'ALARM ESCALATED', message: 'Operator failed to respond. Escalated to Sub-Admin.' });
                setActiveAlarm(null);
                return 0;
             }
             return t - 1;
          });
       }, 1000);
    }
    return () => {
       if (audio) { audio.pause(); audio.currentTime = 0; }
       if (timer) clearInterval(timer);
    }
  }, [activeAlarm, addAlert, escalateAlert, setActiveAlarm, showToast]);

  const handleDismissAlarm = () => {
     setActiveAlarm(null);
     showToast({ type: 'info', title: 'Alarm Cancelled', message: 'You have cancelled the alarm.' });
  };

  if (!activeAlarm) return null;

  return (
    <div className="fixed inset-0 z-[100] pointer-events-none flex items-center justify-center">
      <div className="absolute inset-0 bg-red-600/20 animate-pulse pointer-events-auto backdrop-blur-[2px]"></div>
      <div className="relative z-10 bg-white border-4 border-red-600 rounded-2xl p-8 max-w-2xl w-full mx-4 shadow-2xl shadow-red-600/50 pointer-events-auto flex flex-col items-center text-center animate-bounce-slow">
         <ShieldAlert className="h-24 w-24 text-red-600 mb-6 animate-pulse" />
         <h2 className="text-4xl font-black text-red-700 tracking-widest uppercase mb-2">
            {activeAlarm.title}
         </h2>
         <p className="text-xl font-bold text-slate-800 mb-4">{activeAlarm.what} at {activeAlarm.where}</p>
         <div className="w-full bg-slate-100 p-4 rounded-xl border border-slate-200 mb-8 text-left">
            {activeAlarm.image && (
               <div className="mb-4 rounded-lg overflow-hidden border border-slate-300">
                 <img src={activeAlarm.image} alt="Detection Evidence" className="w-full h-auto object-cover max-h-48" />
               </div>
            )}
            <p className="text-sm font-bold text-red-600 mb-1 tracking-wider uppercase">Detection Confidence: {activeAlarm.confidence}%</p>
            <p className="text-sm font-medium text-slate-600 mb-1">Reason: {activeAlarm.reason}</p>
            <div className="mt-4 flex items-center justify-between bg-red-50 p-3 rounded-lg border border-red-200">
               <span className="text-xs font-bold text-red-800 uppercase tracking-widest">Escalation Timer</span>
               <span className="text-2xl font-black text-red-700 font-mono">00:{timeLeft.toString().padStart(2, '0')}</span>
            </div>
         </div>
         
         <div className="flex gap-4 w-full">
           <button onClick={handleDismissAlarm} className="flex-1 bg-slate-200 hover:bg-slate-300 text-slate-800 font-bold py-4 rounded-xl uppercase tracking-widest transition-colors cursor-pointer">
              Acknowledge & Cancel
           </button>
         </div>
      </div>
    </div>
  );
}
