import { useState, type ReactNode } from 'react';
import {
  Camera,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Radio,
  ScanFace,
  Shield,
  Target,
  TrafficCone,
  TriangleAlert,
  X,
  Database,
} from 'lucide-react';
import { useApp } from '../store';

export type PageId =
  | 'overview'
  | 'live'
  | 'cameras'
  | 'events'
  | 'anpr'
  | 'tracking'
  | 'fences'
  | 'faces'
  | 'suspicious'
  | 'people'
  | 'camera_health'
  | 'vehicles'
  | 'intrusions'
  | 'blockchain';

interface Props {
  current: PageId;
  onNavigate: (page: PageId) => void;
  children: ReactNode;
}

interface NavItem {
  id: PageId;
  label: string;
  icon: typeof LayoutDashboard;
  accent?: string;
}

const NAV_ITEMS: Record<string, NavItem> = {
  overview: { id: 'overview', label: 'Dashboard Overview', icon: LayoutDashboard },
  fences: { id: 'fences', label: 'Virtual Fencing', icon: Shield },
  anpr: { id: 'anpr', label: 'ANPR Detection', icon: TrafficCone },
  live: { id: 'live', label: 'Live Surveillance', icon: Radio, accent: 'text-red-500' },
  events: { id: 'events', label: 'Event Log', icon: FileText },
  blockchain: { id: 'blockchain', label: 'Blockchain Ledger', icon: Database, accent: 'text-emerald-500' },
  cameras: { id: 'cameras', label: 'Recording', icon: Camera },
  faces: { id: 'faces', label: 'Face & Object Detection', icon: ScanFace },
  tracking: { id: 'tracking', label: 'Object Tracking', icon: Target }, // Deprecated but kept in record for safety
};

function NavButton({
  item,
  current,
  onNavigate,
}: {
  item: NavItem;
  current: PageId;
  onNavigate: (page: PageId) => void;
}) {
  const Icon = item.icon;
  const isActive = current === item.id;

  return (
    <button
      type="button"
      onClick={() => onNavigate(item.id)}
      className={`nav-item w-full justify-start ${isActive ? 'nav-item-active' : ''}`}
      aria-current={isActive ? 'page' : undefined}
    >
      <span className={`nav-icon ${isActive ? 'nav-icon-active' : ''}`}>
        <Icon className={`h-4 w-4 ${item.accent ?? ''}`} />
      </span>
      <span className="flex-1 text-left">{item.label}</span>
      {isActive && <span className="h-2 w-2 rounded-full bg-slate-800" />}
    </button>
  );
}

export default function Layout({ current, onNavigate, children }: Props) {
  const { user, logout, toast } = useApp();
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleNavigate = (page: PageId) => {
    setMobileOpen(false);
    onNavigate(page);
  };

  // The user is exclusively an Operator now. No need for complex role logic.
  const PRIMARY_NAV = [
    NAV_ITEMS.overview,
    NAV_ITEMS.live,
    NAV_ITEMS.faces,
    NAV_ITEMS.fences,
    NAV_ITEMS.anpr,
    NAV_ITEMS.cameras,
    NAV_ITEMS.events,
    NAV_ITEMS.blockchain,
  ];

  return (
    <div className="h-screen bg-tactical text-slate-800 font-sans relative overflow-hidden">
      <div className="flex h-screen overflow-hidden">
        <aside
          className={`liquid-sidebar fixed inset-y-0 left-0 z-40 w-[290px] transform transition-transform duration-300 lg:static lg:translate-x-0 ${
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
        >
          <div className="relative flex h-full flex-col overflow-y-auto px-4 py-5">
            <div className="liquid-shell pb-4">
              <div className="brand-row">
                <div className="brand-badge">
                  <Shield className="h-5 w-5" />
                </div>
                <div>
                  <p className="brand-kicker">IBVAP</p>
                  <h1 className="brand-title">Operator Console</h1>
                </div>
              </div>

              <button
                type="button"
                className="close-btn lg:hidden"
                onClick={() => setMobileOpen(false)}
              >
                <X className="h-4 w-4" />
              </button>
            </div>


            <div className="nav-heading-row">
              <p>Navigation</p>
            </div>

            <nav className="mt-3 space-y-2">
              {PRIMARY_NAV.map((item) => (
                <NavButton
                  key={item.id}
                  item={item}
                  current={current}
                  onNavigate={handleNavigate}
                />
              ))}
            </nav>

            {user && (
              <div className="user-card">
                <div className="flex items-center gap-3">
                  <div className="user-icon">
                    <Shield className="h-4 w-4" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-extrabold text-slate-800">{user.name}</p>
                    <p className="user-role">Operator</p>
                  </div>
                </div>

                <button
                  type="button"
                  className="logout-button"
                  onClick={logout}
                >
                  <LogOut className="h-3.5 w-3.5" />
                  Logout
                </button>
              </div>
            )}
          </div>
        </aside>

        {mobileOpen && (
          <button
            type="button"
            className="fixed inset-0 z-30 bg-slate-900/20 backdrop-blur-[2px] lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}

        <div className="flex h-full min-w-0 flex-1 flex-col overflow-y-auto bg-slate-50">
          <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/75 backdrop-blur-md shadow-sm">
            <div className="flex items-center justify-between gap-3 px-4 py-3 sm:px-6">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="rounded-lg border border-slate-200 bg-white/70 p-2 text-slate-600 shadow-sm hover:bg-slate-100 hover:text-slate-800 lg:hidden"
                  onClick={() => setMobileOpen(true)}
                >
                  <Menu className="h-4 w-4" />
                </button>

              </div>
            </div>
          </header>

          <main className="min-w-0 flex-1 px-4 py-5 sm:px-6">{children}</main>

          {toast && (
            <div className="pointer-events-none fixed bottom-4 right-4 z-50 max-w-sm">
              <div
                className={`rounded-2xl border p-4 shadow-2xl backdrop-blur-xl ${
                  toast.type === 'success'
                    ? 'border-emerald-500/30 bg-emerald-500/10'
                    : toast.type === 'warning'
                      ? 'border-amber-500/30 bg-amber-500/10'
                      : toast.type === 'alert'
                        ? 'border-red-500/30 bg-red-500/10'
                        : 'border-accent-500/30 bg-accent-500/10'
                }`}
              >
                <div className="flex items-start gap-3">
                  <TriangleAlert
                    className={`mt-0.5 h-4 w-4 flex-shrink-0 ${
                      toast.type === 'success'
                        ? 'text-emerald-300'
                        : toast.type === 'warning'
                          ? 'text-amber-300'
                          : toast.type === 'alert'
                            ? 'text-red-300'
                            : 'text-accent-300'
                    }`}
                  />
                  <div>
                    <p className="text-sm font-semibold text-slate-900">{toast.title}</p>
                    <p className="mt-1 text-xs text-slate-700">{toast.message}</p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
