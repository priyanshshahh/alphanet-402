import { useEffect, useState, useCallback } from "react";
import { api } from "../api";
import { Panel, Stat, Pill } from "../components/Panel";
import { fmtUsd } from "../utils/trading";

function fmt6(n) {
  return `$${Number(n ?? 0).toFixed(4)}`;
}

export default function Economics() {
  const [econ, setEcon] = useState(null);
  const [err, setErr] = useState("");

  const refresh = useCallback(async () => {
    try {
      setEcon(await api.economics());
      setErr("");
    } catch (e) {
      setErr(String(e.message || e));
    }
  }, []);

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [refresh]);

  const c = econ?.cumulative;

  return (
    <main className="max-w-4xl mx-auto px-6 py-10 space-y-6 text-sm">
      <div>
        <h1 className="text-2xl font-semibold text-white">Unit economics</h1>
        <p className="text-muted mt-2 leading-relaxed">
          The agent's real self-funding P&amp;L, read straight from the append-only{" "}
          <code className="text-accent/90">log_events</code> ledger — USDC spent buying data vs{" "}
          <strong className="text-white">verified</strong> x402 revenue. Unverified sales are shown
          separately and never counted as revenue. All-time, real logged numbers.
        </p>
      </div>

      {err && (
        <div role="alert" className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-danger">
          {err}
        </div>
      )}

      {!econ ? (
        <p className="text-muted">Loading ledger…</p>
      ) : (
        <>
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <Panel title="Data spend">
              <Stat label="USDC bought (cumulative)" value={fmt6(c.spend_usdc)} tone="warn" />
            </Panel>
            <Panel title="Revenue (verified)">
              <Stat label="USDC settled on-chain" value={fmt6(c.revenue_usdc)} tone="positive" />
            </Panel>
            <Panel title="Net margin">
              <Stat
                label="Revenue − spend"
                value={fmt6(econ.net_margin_usdc)}
                tone={econ.net_margin_usdc >= 0 ? "positive" : "negative"}
                sub={econ.break_even ? "at / above break-even" : "below break-even"}
              />
            </Panel>
            <Panel title="Throughput">
              <Stat
                label="Signals produced"
                value={c.signals_produced}
                sub={`${c.purchases} purchases · ${c.sales_verified} sales`}
              />
            </Panel>
          </section>

          <section className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Panel title="Avg cost / purchase">
              <div className="text-xl font-mono text-white">{fmt6(c.avg_cost_per_purchase_usdc)}</div>
              <p className="text-xs text-muted mt-1">per Tavily/x402 data buy</p>
            </Panel>
            <Panel title="Avg revenue / sale">
              <div className="text-xl font-mono text-accent">{fmt6(c.avg_revenue_per_sale_usdc)}</div>
              <p className="text-xs text-muted mt-1">per verified rationale sold</p>
            </Panel>
            <Panel title="Cost / signal">
              <div className="text-xl font-mono text-white">{fmt6(c.cost_per_signal_usdc)}</div>
              <p className="text-xs text-muted mt-1">data spend ÷ signals produced</p>
            </Panel>
          </section>

          {c.sales_unverified > 0 && (
            <div className="rounded-lg border border-warn/40 bg-warn/10 px-4 py-3 text-warn text-xs">
              {c.sales_unverified} unverified payment attempt(s) served but excluded from revenue —
              settlement could not be confirmed on-chain.
            </div>
          )}

          <Panel title="Ledger — SPEND / REVENUE (latest 30)">
            {econ.ledger.length === 0 ? (
              <p className="text-muted text-xs">No spend or revenue booked yet.</p>
            ) : (
              <div className="overflow-x-auto -m-1">
                <table className="w-full text-xs">
                  <thead className="text-muted uppercase text-[10px]">
                    <tr>
                      <th className="text-left py-2 pr-3">Time</th>
                      <th className="text-left pr-3">Kind</th>
                      <th className="text-left pr-3">Ticker</th>
                      <th className="text-right pr-3">USDC</th>
                      <th className="text-left">Detail</th>
                    </tr>
                  </thead>
                  <tbody>
                    {econ.ledger.map((e, i) => (
                      <tr key={i} className="border-t border-edge/60">
                        <td className="py-2 pr-3 font-mono text-muted">{e.ts?.slice(11, 19)}</td>
                        <td className="pr-3">
                          <Pill tone={e.kind === "REVENUE" ? "positive" : "warn"}>{e.kind}</Pill>
                        </td>
                        <td className="pr-3 text-white">{e.ticker || "—"}</td>
                        <td
                          className={`pr-3 text-right font-mono ${
                            (e.amount_usdc ?? 0) >= 0 ? "text-accent" : "text-danger"
                          }`}
                        >
                          {(e.amount_usdc ?? 0) >= 0 ? "+" : ""}
                          {fmtUsd(e.amount_usdc)}
                        </td>
                        <td className="text-muted">{e.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </>
      )}
    </main>
  );
}
