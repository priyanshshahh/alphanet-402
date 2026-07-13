import { useState, useEffect } from "react";
import { api } from "../api";

export default function X402Lab() {
  const [ticker, setTicker] = useState("AAPL");
  const [signalId, setSignalId] = useState("1");
  const [out, setOut] = useState(null);
  const [err, setErr] = useState("");
  const [net, setNet] = useState("");

  useEffect(() => {
    api
      .state()
      .then((s) => setNet(s.network || ""))
      .catch(() => {});
  }, []);

  const loadUnpaidAlpha = async () => {
    setErr("");
    try {
      const data = await api.invoice(ticker);
      setOut({ label: `402 invoice (alpha / ${ticker})`, status: 402, data });
    } catch (e) {
      setErr(String(e.message || e));
    }
  };

  const loadUnpaidTrade = async () => {
    setErr("");
    try {
      const { status, data } = await api.tradeRationaleInvoice(signalId);
      setOut({ label: `402 invoice (trade #${signalId})`, status, data });
    } catch (e) {
      setErr(String(e.message || e));
    }
  };

  const simulatePaid = async () => {
    setErr("");
    try {
      const data = await api.paidRationale(ticker);
      setOut({ label: `Paid alpha / ${ticker}`, status: 200, data });
    } catch (e) {
      setErr(String(e.message || e));
    }
  };

  const simulatePaidTrade = async () => {
    setErr("");
    try {
      const data = await api.paidTradeRationale(signalId);
      setOut({ label: `Paid trade #${signalId}`, status: 200, data });
    } catch (e) {
      setErr(String(e.message || e));
    }
  };

  const curlAlpha = `curl -i "http://localhost:8000/api/alpha/${ticker}/rationale"`;
  const curlPaid = `curl -i -H "X-Payment: <proof-from-awal>" "http://localhost:8000/api/alpha/${ticker}/rationale"`;

  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-6 text-sm text-slate-200">
      <div>
        <h1 className="text-2xl font-semibold text-white">x402 Lab</h1>
        <p className="text-muted mt-2 leading-relaxed">
          Unpaid responses return machine-readable invoices. Paid retries attach{" "}
          <code className="text-accent/90">X-Payment</code>. Backend network:{" "}
          <code className="text-white font-mono">{net || "…"}</code> (Base Sepolia in default{" "}
          <code>.env.example</code>).
        </p>
      </div>

      <div className="rounded-xl border border-edge bg-panel/70 p-4 space-y-3">
        <label className="block text-[10px] text-muted uppercase tracking-wider">Ticker</label>
        <input
          className="w-full rounded-lg bg-ink border border-edge px-3 py-2 text-sm font-mono text-white"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={loadUnpaidAlpha}
            className="text-xs border border-edge rounded-lg px-3 py-1.5 hover:bg-edge text-white"
          >
            GET 402 invoice (alpha)
          </button>
          <button
            type="button"
            onClick={simulatePaid}
            className="text-xs border border-accent/40 bg-accent/10 text-accent rounded-lg px-3 py-1.5 hover:bg-accent/20"
          >
            Simulate paid alpha (demo header)
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-edge bg-panel/70 p-4 space-y-3">
        <label className="block text-[10px] text-muted uppercase tracking-wider">Signal id</label>
        <input
          className="w-full rounded-lg bg-ink border border-edge px-3 py-2 text-sm font-mono text-white"
          value={signalId}
          onChange={(e) => setSignalId(e.target.value.replace(/\D/g, ""))}
        />
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={loadUnpaidTrade}
            className="text-xs border border-edge rounded-lg px-3 py-1.5 hover:bg-edge text-white"
          >
            GET 402 invoice (trade by id)
          </button>
          <button
            type="button"
            onClick={simulatePaidTrade}
            className="text-xs border border-accent/40 bg-accent/10 text-accent rounded-lg px-3 py-1.5 hover:bg-accent/20"
          >
            Simulate paid trade rationale
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-edge bg-ink/60 p-4">
        <p className="text-[10px] text-muted uppercase mb-2">curl (backend :8000)</p>
        <pre className="text-[11px] text-accent/90 whitespace-pre-wrap font-mono">{curlAlpha}</pre>
        <pre className="text-[11px] text-accent/90 whitespace-pre-wrap font-mono mt-2">{curlPaid}</pre>
      </div>

      {err && (
        <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
          {err}
        </div>
      )}

      {out && (
        <div className="rounded-xl border border-edge bg-panel/70 p-4">
          <p className="text-[10px] text-muted uppercase mb-2">
            {out.label} · HTTP {out.status}
          </p>
          <pre className="text-[11px] text-slate-200 overflow-x-auto font-mono whitespace-pre-wrap">
            {JSON.stringify(out.data, null, 2)}
          </pre>
        </div>
      )}
    </main>
  );
}
