import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Panel, Stat, Pill } from "../components/Panel";
import SignalDrawer from "../components/SignalDrawer";
import { fmtUsd, sentimentPillTone, decisionPillTone } from "../utils/trading";

export default function Dashboard() {
  const [state, setState] = useState(null);
  const [signals, setSignals] = useState([]);
  const [logs, setLogs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [invoice, setInvoice] = useState(null);
  const [drawerId, setDrawerId] = useState(null);
  const [lastOk, setLastOk] = useState(null);
  const [stale, setStale] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, sig, lg] = await Promise.all([api.state(), api.signals(), api.logs()]);
      setState(s);
      setSignals(sig);
      setLogs(lg);
      setLastOk(new Date());
      setStale(false);
    } catch {
      // Don't wipe the last good data — flag it as stale so the operator can
      // tell "healthy, no new signals" apart from "polling has been failing".
      setStale(true);
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 4000);
    return () => clearInterval(t);
  }, [refresh]);

  const runCycle = async () => {
    setBusy(true);
    try {
      await api.runCycle();
      await refresh();
    } finally {
      setBusy(false);
    }
  };

  const reset = async () => {
    await api.reset();
    await refresh();
  };

  const invoiceTicker = signals[0]?.ticker ?? "AAPL";

  const showInvoice = async () => {
    const inv = await api.invoice(invoiceTicker);
    setInvoice(inv);
  };

  const spendPct = state
    ? Math.min(100, (state.daily_spend_usdc / Math.max(state.daily_budget_usdc, 1e-6)) * 100)
    : 0;

  const pnlTone = (v) => (v > 0 ? "positive" : v < 0 ? "negative" : "neutral");

  return (
    <div className="min-h-full text-sm">
      <header className="border-b border-edge bg-panel/60 sticky top-0 backdrop-blur z-30">
        <div className="max-w-[1400px] mx-auto px-6 py-3 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-2.5 h-2.5 rounded-full bg-accent shadow-[0_0_10px_#7cf6c4]" />
            <div>
              <div className="font-semibold tracking-wide text-white">AlphaNet-402 · Command Center</div>
              <div className="text-[11px] text-muted mt-0.5 font-mono flex items-center gap-2">
                <span>
                  {state?.network ?? "…"} · {state?.trading_mode ?? "—"} · {state?.data_mode ?? "…"}
                </span>
                <span
                  role="status"
                  aria-live="polite"
                  className={`inline-flex items-center gap-1 ${stale ? "text-warn" : "text-muted/70"}`}
                  title={lastOk ? `Last updated ${lastOk.toLocaleTimeString()}` : "Waiting for backend"}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${stale ? "bg-warn animate-pulse" : "bg-accent"}`}
                    aria-hidden
                  />
                  {stale
                    ? "stale — reconnecting"
                    : lastOk
                      ? `updated ${lastOk.toLocaleTimeString()}`
                      : "connecting…"}
                </span>
              </div>
            </div>
            {state && (
              <>
                <Pill tone={state.trading_mode === "LIVE" ? "warn" : "neutral"}>{state.trading_mode}</Pill>
                <Pill tone={state.halted ? "negative" : state.status === "SCOUTING" ? "warn" : "positive"}>
                  {state.halted ? "HALTED" : state.status}
                </Pill>
                {state.demo_mode && <Pill tone="warn">DEMO DATA — synthetic</Pill>}
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={runCycle}
              disabled={busy}
              className="text-xs border border-edge rounded-lg px-3 py-1.5 hover:bg-edge disabled:opacity-50 text-white"
            >
              {busy ? "Scouting…" : "Run scout cycle"}
            </button>
            <button
              type="button"
              onClick={showInvoice}
              className="text-xs border border-edge rounded-lg px-3 py-1.5 hover:bg-edge text-muted hover:text-white"
            >
              Preview 402 invoice
            </button>
            <button
              type="button"
              onClick={reset}
              className="text-xs border border-danger/30 text-danger/90 rounded-lg px-3 py-1.5 hover:bg-danger/10"
            >
              Reset day
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-6 py-6 space-y-6">
        {state?.halted && (
          <div className="rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger">
            Kill-switch: {state.halt_reason}
          </div>
        )}

        <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <Panel title="Budget">
            <Stat
              label="Remaining today"
              value={fmtUsd(state?.daily_budget_remaining_usdc)}
              sub={`cap ${fmtUsd(state?.daily_budget_usdc)} · spent ${fmtUsd(state?.daily_spend_usdc)}`}
              tone="positive"
            />
          </Panel>
          <Panel title="x402 revenue (verified)">
            <Stat
              label="On-chain settled (USDC)"
              value={fmtUsd(state?.daily_revenue_usdc)}
              sub={
                (state?.daily_unverified_usdc ?? 0) > 0
                  ? `+ ${fmtUsd(state?.daily_unverified_usdc)} unverified (excluded)`
                  : "Settlement-verified · $0.01 / rationale"
              }
              tone="positive"
            />
          </Panel>
          <Panel title="Paper PnL">
            <Stat
              label="Realized"
              value={fmtUsd(state?.realized_pnl_usdc)}
              tone={pnlTone(state?.realized_pnl_usdc ?? 0)}
            />
          </Panel>
          <Panel title="Risk">
            <Stat
              label="Drawdown"
              value={fmtUsd(state?.daily_drawdown_usdc)}
              sub={`limit ${fmtUsd(state?.drawdown_limit_usdc)}`}
              tone="warn"
            />
          </Panel>
        </section>

        <Panel
          title="Spend vs daily cap"
          right={<span className="text-xs text-muted font-mono">{spendPct.toFixed(0)}%</span>}
        >
          <div className="h-2.5 rounded-full bg-edge overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-accent/80 to-emerald-400/90 transition-all duration-500"
              style={{ width: `${spendPct}%` }}
            />
          </div>
          {invoice && (
            <pre className="mt-4 rounded-lg bg-ink border border-edge p-3 text-[11px] text-accent/90 overflow-x-auto font-mono">
              HTTP 402 — alpha rationale ({invoiceTicker}){"\n"}
              {JSON.stringify(invoice, null, 2)}
            </pre>
          )}
        </Panel>

        <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Panel
            title="Signals · Fintel-style pipeline"
            right={
              <span className="text-xs text-muted">
                Click row · prior → posterior · edge
              </span>
            }
          >
            {signals.length === 0 ? (
              <div className="text-muted text-xs">No signals yet — run a scout cycle.</div>
            ) : (
              <div className="overflow-x-auto -m-1">
                <table className="w-full text-xs">
                  <thead className="text-muted uppercase text-[10px]">
                    <tr>
                      <th className="text-left py-2 pr-3">#</th>
                      <th className="text-left pr-3">Ticker</th>
                      <th className="text-left pr-3">Sentiment</th>
                      <th className="text-right pr-3">Prior</th>
                      <th className="text-right pr-3">Post</th>
                      <th className="text-right pr-3">Edge</th>
                      <th className="text-left">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {signals.map((s) => (
                      <tr
                        key={s.id}
                        className="border-t border-edge/60 hover:bg-edge/40 cursor-pointer transition-colors"
                        onClick={() => setDrawerId(s.id)}
                      >
                        <td className="py-2.5 pr-3 font-mono text-muted">{s.id}</td>
                        <td className="pr-3 font-semibold text-white">{s.ticker}</td>
                        <td className="pr-3">
                          <Pill tone={sentimentPillTone(s.sentiment)}>{s.sentiment}</Pill>
                        </td>
                        <td className="pr-3 text-right font-mono text-muted">{s.prior?.toFixed(3)}</td>
                        <td className="pr-3 text-right font-mono text-muted">{s.posterior?.toFixed(3)}</td>
                        <td
                          className={`pr-3 text-right font-mono ${
                            s.edge >= 0 ? "text-accent" : "text-danger"
                          }`}
                        >
                          {s.edge >= 0 ? "+" : ""}
                          {s.edge?.toFixed(3)}
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <Pill tone={decisionPillTone(s.decision)}>{s.decision}</Pill>
                            <Link
                              to={`/signals/${s.id}`}
                              className="text-[10px] text-accent hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              Page
                            </Link>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>

          <Panel title="Agent log" right={<span className="text-xs text-muted">live tail</span>}>
            <ul className="divide-y divide-edge/60 max-h-[420px] overflow-y-auto -m-1">
              {logs.length === 0 ? (
                <li className="text-muted text-xs py-2">Idle.</li>
              ) : (
                logs.map((l, i) => (
                  <li key={i} className="py-2 text-xs">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex gap-2 flex-wrap">
                        <Pill
                          tone={
                            l.level === "ERROR"
                              ? "negative"
                              : l.level === "WARN"
                                ? "warn"
                                : l.level === "SPEND"
                                  ? "positive"
                                  : l.level === "REVENUE"
                                    ? "positive"
                                    : "neutral"
                          }
                        >
                          {l.level}
                        </Pill>
                        <Pill>{l.category}</Pill>
                      </div>
                      <span className="text-muted font-mono shrink-0">{l.ts?.slice(11, 19)}</span>
                    </div>
                    <div className="text-muted mt-1 leading-relaxed">{l.message}</div>
                  </li>
                ))
              )}
            </ul>
          </Panel>
        </section>

        <footer className="text-center text-muted text-[10px] pb-8 leading-relaxed">
          Real equities data via yfinance · leakage guards + risk caps · Groq extracts JSON only ·
          Tavily news over x402/AWAL · Base Sepolia default
        </footer>
      </main>

      <SignalDrawer signalId={drawerId} onClose={() => setDrawerId(null)} />
    </div>
  );
}
