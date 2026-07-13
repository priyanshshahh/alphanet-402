export default function Pitch() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-8 text-slate-200 leading-relaxed text-sm">
      <header>
        <p className="text-[10px] uppercase tracking-[0.25em] text-muted mb-2">Strategy</p>
        <h1 className="text-2xl md:text-3xl font-semibold text-white tracking-tight">
          AlphaNet-402 — an equities research agent that pays for its own data
        </h1>
        <p className="text-muted mt-3 text-sm">
          A decentralized, <strong className="text-white">x402-funded</strong> research agent: it pays
          per query for market intelligence (free yfinance fundamentals, paid Tavily news), validates it with deterministic quant math,
          enforces risk limits, and sells its alpha back to other machines over USDC on Base.
        </p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg text-accent font-medium">Why this shape</h2>
        <p className="text-muted">
          Traditional funds rent data through long contracts; autonomous agents need{" "}
          <strong className="text-white">metered intelligence</strong> and a settlement rail that works
          machine-to-machine. AlphaNet-402 is built for that: yfinance for real prices and fundamentals, Tavily for narrative + flow context, Python
          for beliefs and edges, SQLite for auditability, and HTTP 402 for wholesale alpha.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg text-accent font-medium">Design pillars</h2>
        <ul className="list-disc pl-5 space-y-2 text-muted">
          <li>
            <strong className="text-white">Leakage-aware quant</strong> — no lookahead in evidence;
            kill-switches on spend and drawdown; reproducible math in code.
          </li>
          <li>
            <strong className="text-white">Bayesian beliefs</strong> — LLM is only an NLP feature
            extractor; pricing and posterior updates stay in Python.
          </li>
          <li>
            <strong className="text-white">x402 + AWAL</strong> — micropayments for search and for
            selling structured rationales at{" "}
            <code className="text-accent/90">{"GET /api/trade/{id}/rationale"}</code>.
          </li>
        </ul>
      </section>

      <section className="rounded-xl border border-edge bg-panel/60 p-5 space-y-2">
        <h2 className="text-sm font-semibold text-white uppercase tracking-wider">One-liner</h2>
        <p className="text-muted italic">
          “We built a self-funding quant agent that buys live intelligence on demand, proves an edge in
          Python, and sells the proof to other bots for micro-USDC over HTTP 402.”
        </p>
      </section>
    </main>
  );
}
