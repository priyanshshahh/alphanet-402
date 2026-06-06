export default function StatCard({ label, value, sub, accent = "text-emerald-400", icon }) {
  return (
    <div className="rounded-2xl border border-edge bg-panel/70 backdrop-blur p-4 shadow-lg shadow-black/30">
      <div className="flex items-center justify-between">
        <span className="text-xs uppercase tracking-widest text-slate-400">{label}</span>
        {icon && <span className="text-slate-500 text-lg">{icon}</span>}
      </div>
      <div className={`mt-2 text-2xl font-semibold font-mono ${accent}`}>{value}</div>
      {sub && <div className="mt-1 text-xs text-slate-500">{sub}</div>}
    </div>
  );
}
