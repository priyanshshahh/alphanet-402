import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

export default function JudgeDemo({ embed = false }) {
  const [briefing, setBriefing] = useState(null);
  const [briefErr, setBriefErr] = useState(null);
  const [runResult, setRunResult] = useState(null);
  const [runErr, setRunErr] = useState(null);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .briefing()
      .then((b) => {
        if (!cancelled) setBriefing(b);
      })
      .catch((e) => {
        if (!cancelled) setBriefErr(String(e.message || e));
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const onRun = useCallback(async () => {
    setRunning(true);
    setRunErr(null);
    setRunResult(null);
    try {
      const r = await api.judgeRun();
      setRunResult(r);
    } catch (e) {
      setRunErr(String(e.message || e));
    } finally {
      setRunning(false);
    }
  }, []);

  return (
    <main
      className={`mx-auto text-slate-200 leading-relaxed text-sm ${
        embed
          ? "max-w-full min-h-full bg-ink px-4 py-4 space-y-4 overflow-y-auto"
          : "max-w-3xl px-6 py-10 space-y-8"
      }`}
    >
      <header>
        <p className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">Judge walkthrough</p>
        <h1
          className={`font-semibold text-white tracking-tight ${
            embed ? "text-lg md:text-xl" : "text-2xl md:text-3xl"
          }`}
        >
          AlphaNet-402 — live demo script
        </h1>
        {!embed && (
          <p className="text-muted mt-3 text-sm">
            Use this page as a single anchor during judging: talking points load from the API, then one
            button runs the full scout → quant → risk cycle and surfaces fresh signals plus a sample x402
            invoice.
          </p>
        )}
        {embed && (
          <p className="text-muted mt-2 text-[11px]">
            Embedded in pitch deck — run the pipeline below; full console in a new tab from the deck exit
            menu.
          </p>
        )}
      </header>

      <section className="rounded-xl border border-edge bg-panel/60 p-5 space-y-4">
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={onRun}
            disabled={running}
            className="px-4 py-2 rounded-lg bg-accent text-ink text-sm font-semibold disabled:opacity-50"
          >
            {running ? "Running pipeline…" : "Run pipeline (judge button)"}
          </button>
          <Link
            to="/"
            className="text-xs text-accent hover:underline"
          >
            Open Overview →
          </Link>
          <Link
            to="/x402-lab"
            className="text-xs text-accent hover:underline"
          >
            x402 Lab →
          </Link>
        </div>
        {runErr && (
          <p className="text-red-400 text-xs font-mono">{runErr}</p>
        )}
        {runResult && (
          <div className="space-y-3 text-xs">
            <p className="text-muted">
              <span className="text-white font-medium">Ran at</span>{" "}
              <span className="font-mono text-accent/90">{runResult.ran_at}</span>
            </p>
            {runResult.cycle != null && (
              <pre className="rounded-lg bg-ink/80 border border-edge p-3 overflow-x-auto text-[11px] text-muted max-h-40">
                {JSON.stringify(runResult.cycle, null, 2)}
              </pre>
            )}
            {runResult.state && (
              <div className="grid gap-2 sm:grid-cols-2">
                <div className="rounded-lg border border-edge p-3">
                  <p className="text-[10px] uppercase text-muted mb-1">Agent status</p>
                  <p className="text-white font-mono">{runResult.state.status}</p>
                  <p className="text-muted mt-1">
                    Spend today:{" "}
                    <span className="text-accent">${Number(runResult.state.daily_spend_usdc ?? 0).toFixed(4)}</span>
                  </p>
                </div>
                <div className="rounded-lg border border-edge p-3">
                  <p className="text-[10px] uppercase text-muted mb-1">Latest signals</p>
                  <ul className="space-y-1 font-mono text-[11px]">
                    {(runResult.latest_signals || []).map((s) => (
                      <li key={s.id}>
                        <Link to={`/signals/${s.id}`} className="text-accent hover:underline">
                          #{s.id} {s.ticker}
                        </Link>{" "}
                        <span className="text-muted">
                          edge{" "}
                          {typeof s.edge === "number" && Number.isFinite(s.edge)
                            ? s.edge.toFixed(4)
                            : String(s.edge ?? "—")}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
            {runResult.sample_x402_invoice && (
              <details className="rounded-lg border border-edge">
                <summary className="cursor-pointer px-3 py-2 text-white text-xs">
                  Sample x402 invoice JSON
                </summary>
                <pre className="px-3 pb-3 text-[10px] text-muted overflow-x-auto">
                  {JSON.stringify(runResult.sample_x402_invoice, null, 2)}
                </pre>
              </details>
            )}
            {runResult.deep_links && (
              <p className="text-muted text-[11px]">
                API paths for narration:{" "}
                <code className="text-accent/80">{runResult.deep_links.alpha_rationale_unpaid}</code>
                {runResult.deep_links.trade_rationale_unpaid && (
                  <>
                    {" · "}
                    <code className="text-accent/80">{runResult.deep_links.trade_rationale_unpaid}</code>
                  </>
                )}
              </p>
            )}
          </div>
        )}
      </section>

      {!embed && (
      <section className="space-y-4">
        <h2 className="text-lg text-accent font-medium">Talking points</h2>
        {briefErr && <p className="text-red-400 text-xs font-mono">{briefErr}</p>}
        {!briefing && !briefErr && <p className="text-muted text-xs">Loading briefing…</p>}
        {briefing && (
          <div className="space-y-4">
            <p className="text-white font-medium text-base">{briefing.product}</p>
            <p className="text-muted">{briefing.elevator}</p>
            <ul className="space-y-3">
              {(briefing.pillars || []).map((p) => (
                <li key={p.name} className="rounded-lg border border-edge bg-panel/40 p-4">
                  <p className="text-accent font-medium text-sm">{p.name}</p>
                  <p className="text-muted mt-1 text-xs">{p.detail}</p>
                </li>
              ))}
            </ul>
            <div className="rounded-xl border border-edge bg-panel/60 p-4">
              <p className="text-[10px] uppercase tracking-wider text-muted mb-2">Judge tips</p>
              <ul className="list-disc pl-5 space-y-2 text-muted text-xs">
                {(briefing.judge_tips || []).map((t, i) => (
                  <li key={i}>{t}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </section>
      )}
    </main>
  );
}
