import { NavLink, Outlet } from "react-router-dom";

const items = [
  { to: "/", label: "Overview", end: true },
  { to: "/pitch-deck", label: "Pitch deck" },
  { to: "/demo", label: "Judge demo" },
  { to: "/strategy", label: "Strategy" },
  { to: "/architecture", label: "Systems" },
  { to: "/wallet", label: "AWAL setup" },
  { to: "/x402-lab", label: "x402 Lab" },
];

function linkCls({ isActive }) {
  return `flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors border ${
    isActive
      ? "bg-accent/10 text-accent border-accent/25"
      : "text-muted hover:bg-edge hover:text-white border-transparent"
  }`;
}

export default function AppShell() {
  return (
    <div className="min-h-full flex bg-ink text-white">
      <aside className="w-56 shrink-0 border-r border-edge bg-panel/90 backdrop-blur hidden md:flex flex-col">
        <div className="p-4 border-b border-edge">
          <div className="flex items-center gap-2">
            <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_12px_#7cf6c4]" aria-hidden />
            <span className="font-semibold tracking-[0.2em] text-xs text-white">ALPHANET</span>
            <span className="text-[10px] text-muted font-mono">402</span>
          </div>
          <p className="text-[11px] text-muted mt-2 leading-snug">
            Fintel-style scout · Bayesian edge · x402 monetization
          </p>
        </div>
        <nav className="p-2 space-y-0.5 flex-1 overflow-y-auto">
          {items.map(({ to, label, end }) => (
            <NavLink key={to} to={to} end={end} className={linkCls}>
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="p-3 text-[10px] text-muted border-t border-edge leading-relaxed">
          Repos: <span className="text-muted/80 font-mono">chf</span> +{" "}
          <span className="text-muted/80 font-mono">polymarket-sentiment-agent</span>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="md:hidden border-b border-edge bg-panel/80 px-3 py-2 flex flex-wrap gap-1.5">
          {items.map(({ to, label, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `text-[11px] px-2 py-1 rounded border ${
                  isActive
                    ? "border-accent/40 text-accent bg-accent/10"
                    : "border-edge text-muted"
                }`
              }
            >
              {label}
            </NavLink>
          ))}
        </header>
        <div className="flex-1 overflow-auto">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
