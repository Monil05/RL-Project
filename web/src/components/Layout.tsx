import { NavLink, Outlet } from "react-router-dom";
import { useState } from "react";
import {
  Activity,
  Clapperboard,
  GitCompare,
  LayoutDashboard,
  Menu,
  Settings,
  Table2,
  Brain,
  X,
} from "lucide-react";
import { useSimulation } from "../context/SimulationContext";

const LINKS = [
  { to: "/", label: "Overview", icon: LayoutDashboard },
  { to: "/simulation", label: "Simulation", icon: Activity },
  { to: "/training", label: "Training", icon: Brain },
  { to: "/comparison", label: "Comparison", icon: GitCompare },
  { to: "/results", label: "Results", icon: Table2 },
  { to: "/video", label: "Video", icon: Clapperboard },
  { to: "/settings", label: "Settings", icon: Settings },
];

export function Layout() {
  const [open, setOpen] = useState(false);
  const { connection, refresh } = useSimulation();
  return (
    <div className="min-h-screen bg-slate-100 text-slate-900">
      {open ? <button className="fixed inset-0 z-20 bg-slate-900/40 md:hidden" aria-label="Close menu" onClick={() => setOpen(false)} /> : null}
      <aside className={`fixed inset-y-0 left-0 z-30 flex w-64 flex-col bg-slate-900 text-slate-100 transition-transform md:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}>
        <div className="flex items-start justify-between px-5 py-5">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-indigo-300">Traffic control</div>
            <div className="mt-1 text-lg font-semibold leading-tight">Adaptive signals</div>
          </div>
          <button className="rounded-md p-1 text-slate-300 md:hidden" aria-label="Close navigation" onClick={() => setOpen(false)}>
            <X className="h-5 w-5" />
          </button>
        </div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Primary">
          {LINKS.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                end={link.to === "/"}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium ${isActive ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800 hover:text-white"}`
                }
              >
                <Icon className="h-4 w-4" aria-hidden="true" />
                {link.label}
              </NavLink>
            );
          })}
        </nav>
        <div className="border-t border-slate-800 px-5 py-4 text-xs text-slate-400">
          API {connection === "online" ? "connected" : "unreachable"}
        </div>
      </aside>
      <div className="md:pl-64">
        <header className="sticky top-0 z-10 flex items-center justify-between border-b border-slate-200 bg-white/95 px-4 py-3 backdrop-blur md:px-8">
          <button className="rounded-md p-2 text-slate-700 md:hidden" aria-label="Open navigation" onClick={() => setOpen(true)}>
            <Menu className="h-5 w-5" />
          </button>
          <div className="text-sm text-slate-500">Q-Learning and SARSA stay in the existing Python core.</div>
          {connection === "offline" ? (
            <button className="rounded-lg bg-rose-600 px-3 py-1.5 text-sm font-semibold text-white" onClick={() => void refresh()}>
              Retry connection
            </button>
          ) : (
            <span className="text-xs font-medium text-emerald-700">Live data</span>
          )}
        </header>
        <main className="mx-auto max-w-7xl space-y-4 p-4 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
