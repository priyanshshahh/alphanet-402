import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Pill } from "./Panel";
import { fmtUsd, sentimentPillTone, decisionPillTone } from "../utils/trading";

export default function SignalDrawer({ signalId, onClose }) {
  const [sig, setSig] = useState(null);

  useEffect(() => {
    if (signalId == null) {
      setSig(null);
      return;
    }
    let cancelled = false;
    api
      .signal(signalId)
      .then((d) => {
        if (!cancelled) setSig(d);
      })
      .catch(() => {
        if (!cancelled) setSig(null);
      });
    return () => {
      cancelled = true;
    };
  }, [signalId]);

  if (signalId == null) return null;

  return (
    <div
      className="fixed inset-0 bg-black/65 z-50 flex justify-end"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="w-full max-w-lg h-full bg-panel border-l border-edge overflow-y-auto shadow-2xl"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="signal-drawer-title"
      >
        <div className="p-5 border-b border-edge flex items-start justify-between gap-3">
          <div>
            <div className="text-[10px] text-muted uppercase tracking-wider">Signal</div>
            <h2 id="signal-drawer-title" className="text-lg font-semibold mt-0.5">
              {sig?.ticker ?? "…"}{" "}
              <span className="text-muted font-mono text-base">#{signalId}</span>
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-muted hover:text-white text-sm border border-edge rounded-lg px-3 py-1.5 shrink-0"
          >
            Close
          </button>
        </div>

        <div className="p-5 space-y-4">
          {!sig && <p className="text-muted text-sm">Loading…</p>}

          {sig && (
            <>
              <section className="bg-edge/50 rounded-xl p-4 border border-edge/80">
                <div className="text-[10px] text-muted uppercase mb-2">Decision</div>
                <div className="flex flex-wrap gap-2 items-center">
                  <Pill tone={sentimentPillTone(sig.sentiment)}>{sig.sentiment}</Pill>
                  <Pill tone={decisionPillTone(sig.decision)}>{sig.decision}</Pill>
                  <Pill>conf {Number(sig.confidence).toFixed(2)}</Pill>
                </div>
                <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-muted font-mono">
                  <div>prior {Number(sig.prior).toFixed(3)}</div>
                  <div>post {Number(sig.posterior).toFixed(3)}</div>
                  <div className={sig.edge >= 0 ? "text-accent" : "text-danger"}>
                    edge {sig.edge >= 0 ? "+" : ""}
                    {Number(sig.edge).toFixed(3)}
                  </div>
                </div>
              </section>

              <section className="bg-edge/50 rounded-xl p-4 border border-edge/80">
                <div className="text-[10px] text-muted uppercase mb-1">Whale read</div>
                <p className="text-sm text-slate-200">{sig.whale_action || "—"}</p>
                {sig.source_snippet && (
                  <p className="text-xs text-muted mt-2 leading-relaxed line-clamp-5">{sig.source_snippet}</p>
                )}
              </section>

              <section className="bg-edge/50 rounded-xl p-4 border border-edge/80">
                <div className="text-[10px] text-muted uppercase mb-2">NLP features (strict JSON)</div>
                <pre className="text-[11px] font-mono text-accent/90 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(sig.nlp_features || {}, null, 2)}
                </pre>
              </section>

              <section className="rounded-xl border border-accent/20 bg-accent/5 p-4">
                <p className="text-xs text-muted mb-2">
                  Sell full causal chain to another agent for{" "}
                  <strong className="text-white">{fmtUsd(0.01)}</strong> USDC (x402).
                </p>
                <code className="text-[10px] text-muted break-all block">
                  GET /api/trade/{sig.id}/rationale
                </code>
                <Link
                  to={`/signals/${sig.id}`}
                  className="inline-block mt-3 text-xs text-accent hover:underline"
                  onClick={onClose}
                >
                  Open full signal page →
                </Link>
              </section>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
