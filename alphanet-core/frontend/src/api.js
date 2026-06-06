const BASE = "";

async function j(path, opts = {}) {
  const res = await fetch(BASE + path, opts);
  if (!res.ok && res.status !== 402) throw new Error(`${path} -> ${res.status}`);
  return res.json();
}

export const api = {
  briefing: () => j("/api/demo/briefing"),
  judgeRun: () => j("/api/demo/judge-run", { method: "POST" }),
  state: () => j("/api/state"),
  signals: () => j("/api/signals?limit=12"),
  signal: (id) => j(`/api/signals/${id}`),
  logs: () => j("/api/logs?limit=30"),
  runCycle: () => j("/api/cycle", { method: "POST" }),
  reset: () => j("/api/reset", { method: "POST" }),
  invoice: (ticker) => j(`/api/alpha/${ticker}/rationale`),
  paidRationale: (ticker) =>
    j(`/api/alpha/${ticker}/rationale`, {
      headers: { "X-Payment": "demo-settlement-proof-alpha" },
    }),
  async tradeRationaleInvoice(signalId) {
    const res = await fetch(BASE + `/api/trade/${signalId}/rationale`);
    const data = await res.json().catch(() => ({}));
    return { status: res.status, data };
  },
  paidTradeRationale: (signalId) =>
    j(`/api/trade/${signalId}/rationale`, {
      headers: { "X-Payment": `demo-settlement-proof-trade-${signalId}` },
    }),
};
