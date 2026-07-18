import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { Panel, Pill } from "../components/Panel";
import { fmtUsd, sentimentPillTone, decisionPillTone } from "../utils/trading";

export default function SignalDetail() {
  const { id } = useParams();
  const [sig, setSig] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api.signal(id);
        if (!cancelled) setSig(data);
      } catch (e) {
        if (!cancelled) setErr(String(e.message || e));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (err) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-10">
        <p className="text-danger text-sm">{err}</p>
        <Link to="/" className="text-accent text-sm mt-4 inline-block hover:underline">
          ← Overview
        </Link>
      </main>
    );
  }

  if (!sig) {
    return (
      <main className="max-w-3xl mx-auto px-6 py-10 text-muted text-sm">Loading signal…</main>
    );
  }

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <Link to="/" className="text-[11px] text-accent hover:underline">
            ← Overview
          </Link>
          <h1 className="text-2xl font-semibold text-white mt-2">
            {sig.ticker} <span className="text-muted font-mono text-lg">#{sig.id}</span>
          </h1>
          <p className="text-xs text-muted font-mono mt-1">{sig.ts}</p>
        </div>
        <Pill tone={decisionPillTone(sig.decision)}>{sig.decision}</Pill>
      </div>

      <section className="grid sm:grid-cols-2 gap-4">
        <Panel title="Belief update">
          <div className="text-[10px] text-muted uppercase mb-2">Prior → Posterior</div>
          <div className="text-2xl font-mono text-white">
            {sig.prior?.toFixed(4)} → {sig.posterior?.toFixed(4)}
          </div>
          <p className={`text-sm mt-2 font-mono ${sig.edge >= 0 ? "text-accent" : "text-danger"}`}>
            edge {sig.edge >= 0 ? "+" : ""}
            {sig.edge}
          </p>
        </Panel>
        <Panel title="Sentiment">
          <Pill tone={sentimentPillTone(sig.sentiment)}>{sig.sentiment}</Pill>
          <p className="text-sm text-muted mt-3">confidence {sig.confidence}</p>
          <p className="text-xs text-muted mt-1">leakage_ok: {String(sig.leakage_ok)}</p>
        </Panel>
      </section>

      <Panel title="Flow / positioning read">
        <p className="text-sm text-slate-200">{sig.whale_action || "—"}</p>
        {sig.source_snippet && (
          <blockquote className="text-xs text-muted border-l-2 border-accent/40 pl-3 mt-3 leading-relaxed">
            {sig.source_snippet}
          </blockquote>
        )}
      </Panel>

      {Array.isArray(sig.evidence?.urls) && sig.evidence.urls.length > 0 && (
        <Panel title="Sources / provenance">
          <ul className="space-y-2">
            {sig.evidence.urls.map((u, i) => (
              <li key={i} className="text-sm">
                <a
                  href={u.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-accent hover:underline break-all"
                >
                  {u.title || u.url}
                </a>
                {u.score != null && (
                  <span className="text-muted text-xs ml-2 font-mono">score {u.score}</span>
                )}
              </li>
            ))}
          </ul>
          <p className="text-[11px] text-muted mt-3">
            These are the exact sources that fed this signal — also included in the paid x402
            payload so a buyer can audit the analysis.
          </p>
        </Panel>
      )}

      <Panel title="NLP features (JSON)">
        <pre className="text-[11px] font-mono text-accent/90 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(sig.nlp_features || {}, null, 2)}
        </pre>
      </Panel>

      <Panel title="Tavily evidence bundle">
        <pre className="text-[11px] font-mono text-muted overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(sig.evidence || {}, null, 2)}
        </pre>
      </Panel>

      <Panel title="Monetize (x402)">
        <p className="text-xs text-muted mb-2">
          Full causal payload for <strong className="text-white">{fmtUsd(0.01)}</strong> — see{" "}
          <Link to="/x402-lab" className="text-accent hover:underline">
            x402 Lab
          </Link>
          .
        </p>
        <code className="text-[11px] text-muted break-all">
          GET /api/trade/{sig.id}/rationale
        </code>
        <p className="text-[11px] text-muted mt-2 leading-relaxed">
          Revenue is booked only when the x402 settlement is verified on-chain; unverified
          payments are served but excluded from the revenue counter.
        </p>
      </Panel>
    </main>
  );
}
