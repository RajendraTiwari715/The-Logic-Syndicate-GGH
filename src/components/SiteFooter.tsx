import { Shield } from 'lucide-react';

export default function SiteFooter() {
  return (
    <footer className="relative z-10 w-full border-t border-slate-200 bg-white/85 backdrop-blur-md">
      <div className="mx-auto flex w-full max-w-[1400px] flex-col items-center justify-between gap-3 px-4 py-4 text-center sm:flex-row sm:px-6 sm:text-left lg:px-8">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl border border-slate-200 bg-slate-50 text-slate-700 shadow-sm">
            <Shield className="h-4 w-4" aria-hidden="true" />
          </span>
          <div>
            <p className="text-[10px] font-black uppercase tracking-[0.24em] text-slate-800">
              IBVAP Core
            </p>
            <p className="mt-0.5 text-[10px] text-slate-500 sm:text-xs">
              Intelligent Border Video Analytics Platform
            </p>
          </div>
        </div>

        <p className="text-[10px] font-semibold tracking-[0.08em] text-slate-500 sm:text-xs">
          © {new Date().getFullYear()} IBVAP <span className="mx-1.5 text-slate-300">·</span> Operator Console
        </p>
      </div>
    </footer>
  );
}
