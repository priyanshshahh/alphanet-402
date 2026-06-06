import React from "react";

export function Panel({
  title,
  right,
  children,
  className = "",
}: {
  title?: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-panel border border-edge rounded-xl ${className}`}>
      {(title || right) && (
        <div className="px-4 py-3 border-b border-edge flex items-center justify-between">
          <div className="text-xs uppercase tracking-wider text-muted">{title}</div>
          {right}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}

export function Stat({
  label,
  value,
  tone = "neutral",
  sub,
}: {
  label: string;
  value: React.ReactNode;
  tone?: "neutral" | "positive" | "negative" | "warn";
  sub?: string;
}) {
  const toneClass =
    tone === "positive"
      ? "text-accent"
      : tone === "negative"
      ? "text-danger"
      : tone === "warn"
      ? "text-warn"
      : "text-white";
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-muted">{label}</div>
      <div className={`text-2xl mt-1 ${toneClass}`}>{value}</div>
      {sub && <div className="text-xs text-muted mt-0.5">{sub}</div>}
    </div>
  );
}

export function Pill({
  children,
  tone = "neutral",
}: {
  children: React.ReactNode;
  tone?: "neutral" | "positive" | "negative" | "warn";
}) {
  const cls =
    tone === "positive"
      ? "bg-accent/10 text-accent border-accent/30"
      : tone === "negative"
      ? "bg-danger/10 text-danger border-danger/30"
      : tone === "warn"
      ? "bg-warn/10 text-warn border-warn/30"
      : "bg-edge text-muted border-edge";
  return (
    <span className={`px-2 py-0.5 rounded text-[10px] uppercase tracking-wider border ${cls}`}>
      {children}
    </span>
  );
}
