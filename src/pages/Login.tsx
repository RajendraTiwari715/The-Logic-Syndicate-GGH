import { useState } from 'react';
import { useApp } from '../store';
import { Shield, Lock, User as UserIcon, Eye, EyeOff, CheckCircle2 } from 'lucide-react';

export default function Login() {
  const { login } = useApp();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [showPass, setShowPass] = useState(false);
  const [remember, setRemember] = useState(true);
  // activeRole removed for single role
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    
    // Simulate RSA Key Exchange delay for Cybersecurity SIH Theme
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    try {
      const ok = await login(username, password);
      if (!ok) {
        setError('Unauthorized Access. Invalid credentials.');
      }
    } catch (err: unknown) {
      console.error(err);
      setError('Unauthorized Access. Invalid credentials.');
    } finally {
      setLoading(false);
    }
  };



  return (
    <div className="relative min-h-screen w-full flex flex-col font-sans text-slate-800 bg-slate-50 selection:bg-orange-500/30">
      {/* Background Image Setup */}
      <div 
        className="absolute inset-0 z-0 opacity-[0.2] bg-center bg-cover bg-no-repeat bg-fixed filter saturate-50"
        style={{ backgroundImage: "url('https://images.unsplash.com/photo-1587474260584-136574528ed5?q=80&w=1920&auto=format&fit=crop')" }} 
      />
      
      {/* Top Header */}
      <header className="relative z-10 w-full bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-[1400px] mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <img src="https://upload.wikimedia.org/wikipedia/commons/5/55/Emblem_of_India.svg" alt="Emblem" className="h-[46px] select-none pointer-events-none" />
            <div>
              <p className="text-sm font-bold leading-tight">रक्षा मंत्रालय</p>
              <p className="text-sm font-bold uppercase tracking-wider leading-tight text-slate-800">Ministry of<br/>Defence</p>
            </div>
          </div>
          <div className="flex items-center gap-4 sm:gap-6 opacity-90 select-none pointer-events-none">
            <img src="https://upload.wikimedia.org/wikipedia/commons/3/30/Make_In_India.png" alt="Make in India" className="h-8 object-contain" onError={e => e.currentTarget.style.display='none'} />
            <img src="https://upload.wikimedia.org/wikipedia/en/thumb/4/41/Swachh_Bharat_MISSION_Logo.jpeg/220px-Swachh_Bharat_MISSION_Logo.jpeg" alt="Swachh Bharat" className="h-8 object-contain rounded" onError={e => e.currentTarget.style.display='none'} />
            <img src="https://upload.wikimedia.org/wikipedia/en/thumb/5/56/Digital_India_logo.svg/150px-Digital_India_logo.svg.png" alt="Digital India" className="h-8 object-contain" onError={e => e.currentTarget.style.display='none'} />
          </div>
        </div>
        

      </header>

      {/* Main Content Area */}
      <main className="relative z-10 flex-1 w-full max-w-[1400px] mx-auto p-4 sm:p-6 lg:p-8 flex items-center justify-center">
        <div className="w-full grid grid-cols-1 lg:grid-cols-12 gap-6 lg:gap-8 items-start">
          
          {/* Left Column (Content Grid) */}
          <div className="lg:col-span-8 flex flex-col gap-6 lg:gap-8">
            
            {/* Info Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm hover:shadow-md transition-shadow">
              <h2 className="text-lg sm:text-xl font-bold text-slate-800 uppercase leading-snug mb-4 tracking-wide">
                Intelligence Border Video Analysis Platform (IBVAP) Core
              </h2>
              <p className="text-[13px] sm:text-sm text-slate-600 leading-relaxed font-medium">
                A fully automated, advanced CCTV camera detection system. Designed for use by the Indian Army and Government to detect potential dangers or activities and generate immediate reports to Centralized Defense Command.
              </p>
            </div>

            {/* Live Feed Card */}
            <div className="bg-white rounded-xl border border-slate-200 p-6 sm:p-8 shadow-sm hover:shadow-md transition-shadow mb-4 lg:mb-0">
              <h3 className="text-base sm:text-lg font-bold text-slate-800 uppercase tracking-wide mb-4">Live Feed Preview</h3>
              <div className="grid grid-cols-2 gap-3 aspect-[2/1] sm:aspect-auto sm:h-[180px]">
                <img src="/live_feed.jpg" className="w-full h-full object-cover rounded-lg grayscale brightness-75 contrast-125 border border-slate-200" alt="Feed 1" />
                <img src="/border_patrol.jpg" className="w-full h-full object-cover rounded-lg grayscale brightness-75 contrast-125 border border-slate-200" alt="Feed 2" />
              </div>
            </div>

          </div>

          {/* Right Column (Login Form) */}
          <div className="lg:col-span-4 self-center w-full max-w-sm mx-auto lg:max-w-none">
            <div className="bg-white rounded-2xl border border-slate-200 shadow-[0_8px_30px_rgb(0,0,0,0.08)] overflow-hidden relative group">
              <div className="absolute top-0 left-0 right-0 h-[5px] bg-gradient-to-r from-orange-500 via-green-500 to-green-600 opacity-90"></div>
              
              <div className="p-8 sm:p-10">
                <div className="text-center mb-10">
                  <div className="mx-auto w-14 h-14 flex items-center justify-center rounded-2xl border border-slate-100 bg-slate-50 shadow-inner mb-5 group-hover:scale-105 transition-transform duration-300">
                    <Shield className="w-7 h-7 text-slate-800" strokeWidth={1.5} />
                  </div>
                  <h2 className="text-2xl font-black text-slate-900 uppercase tracking-widest leading-none mb-1">IBVAP Core</h2>
                  <p className="text-[11px] font-bold text-slate-600 uppercase tracking-widest mb-4">Border Security Force</p>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-green-50 text-green-700 rounded-full border border-green-200">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span className="text-[10px] font-bold uppercase tracking-wider">Secure Gateway</span>
                  </div>
                </div>

                <form onSubmit={handleSubmit} className="space-y-5">
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1.5 ml-0.5">Username</label>
                    <div className="relative group">
                      <UserIcon className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600 group-focus-within:text-orange-500 transition-colors" />
                      <input
                        type="text"
                        className="w-full pl-10 pr-4 py-3 bg-white border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 text-slate-800 font-semibold placeholder-slate-400 shadow-sm transition-all"
                        placeholder="Enter authorized ID"
                        value={username}
                        onChange={e => setUsername(e.target.value)}
                        required
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1.5 ml-0.5">Password</label>
                    <div className="relative group">
                      <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-slate-600 group-focus-within:text-orange-500 transition-colors" />
                      <input
                        type={showPass ? 'text' : 'password'}
                        className="w-full pl-10 pr-10 py-3 bg-white border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 focus:border-orange-500 text-slate-800 font-semibold placeholder-slate-400 shadow-sm transition-all"
                        placeholder="Enter secure password"
                        value={password}
                        onChange={e => setPassword(e.target.value)}
                        required
                      />
                      <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-600 focus:outline-none">
                        {showPass ? <EyeOff className="w-[18px] h-[18px]" /> : <Eye className="w-[18px] h-[18px]" />}
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center gap-2.5 pt-1">
                    <input
                      type="checkbox"
                      id="remember"
                      className="w-4 h-4 rounded text-orange-500 border-slate-300 focus:ring-orange-500 focus:ring-offset-1"
                      checked={remember}
                      onChange={e => setRemember(e.target.checked)}
                    />
                    <label htmlFor="remember" className="text-[13px] font-semibold text-slate-700 cursor-pointer select-none">
                      Remember user session
                    </label>
                  </div>

                  {error && (
                    <p className="text-xs text-red-600 font-semibold text-center bg-red-50 py-2 rounded-lg border border-red-100">{error}</p>
                  )}

                  <div className="pt-2">
                    <button
                      type="submit"
                      disabled={loading}
                      className="w-full py-3.5 bg-orange-600 hover:bg-orange-700 text-white rounded-xl flex items-center justify-center gap-2.5 text-[13px] font-extrabold tracking-widest uppercase transition-all hover:shadow-[0_4px_12px_rgba(234,88,12,0.3)] min-h-[52px]"
                    >
                      <Shield className="w-[18px] h-[18px]" strokeWidth={2.5} />
                      {loading ? 'Verifying RSA Keys...' : 'Secure Login'}
                    </button>
                  </div>
                </form>

                {/* Fast Login removed for strict single-role system */}

              </div>
            </div>
          </div>

        </div>
      </main>
      
      {/* Footer Details */}
      <div className="fixed bottom-0 left-0 right-0 bg-white/70 backdrop-blur-sm border-t border-slate-200/50 py-2.5 text-center flex justify-center items-center gap-8 text-[10px] sm:text-xs font-semibold text-slate-600 uppercase tracking-widest">
        <span>Feedback</span>
        <span>Website Policies</span>
        <span>Help</span>
        <span>Contact Us</span>
        <span>Web Information Manager</span>
      </div>
    </div>
  );
}
