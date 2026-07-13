export default function Architecture() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-8 text-slate-200 leading-relaxed text-sm">
      <div>
        <h1 className="text-2xl font-semibold text-white mb-2">Systems architecture</h1>
        <p className="text-muted">
          AlphaNet-402 composes a <strong className="text-white">scout</strong> (yfinance + Tavily 402/AWAL), a{" "}
          <strong className="text-white">quant core</strong> (NLP JSON → log-odds / Bayes), a{" "}
          <strong className="text-white">risk overseer</strong> (leakage + drawdown), and an{" "}
          <strong className="text-white">x402 seller</strong> surface for rationales.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-lg text-accent font-medium">Network (current default)</h2>
        <p className="text-muted">
          The backend ships with <code className="text-white">eip155:84532</code> (Base Sepolia)
          and test USDC in <code className="text-white">.env.example</code>. Invoices for your own
          rationales use the same CAIP-2 id so judges can pay on Sepolia without mainnet exposure.
          Switch env vars to Base Mainnet when you are ready for production USDC.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg text-accent font-medium">HTTP payment handshake</h2>
        <ol className="list-decimal pl-5 space-y-2 text-muted">
          <li>Client requests a paid resource.</li>
          <li>Server responds with <code className="text-white">402</code> + invoice JSON.</li>
          <li>AWAL settles; client retries with <code className="text-white">X-Payment</code>.</li>
          <li>Server returns payload + records idempotent receipt.</li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg text-accent font-medium">Routes</h2>
        <ul className="text-muted space-y-1 font-mono text-xs">
          <li>GET /api/alpha/AAPL/rationale — latest signal for ticker</li>
          <li>GET /api/trade/123/rationale — blueprint path by signal id</li>
          <li>POST /api/cycle — run one scout pass (demo)</li>
        </ul>
      </section>
    </main>
  );
}
