import { Panel } from "../components/Panel";

function Step({ n, title, children }) {
  return (
    <div className="flex gap-3">
      <div className="shrink-0 h-6 w-6 rounded-full bg-accent/10 border border-accent/30 text-accent text-xs font-mono flex items-center justify-center">
        {n}
      </div>
      <div>
        <div className="text-white font-medium">{title}</div>
        <p className="text-muted text-sm mt-1 leading-relaxed">{children}</p>
      </div>
    </div>
  );
}

export default function Methodology() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-6 text-sm">
      <div>
        <h1 className="text-2xl font-semibold text-white">Methodology</h1>
        <p className="text-muted mt-2 leading-relaxed">
          How AlphaNet-402 turns market data into a directional belief — and, just as important,
          what it does <strong className="text-white">not</strong> claim to be.
        </p>
      </div>

      <Panel title="The pipeline: prior → posterior → edge">
        <div className="space-y-4">
          <Step n="1" title="Prior (base rate)">
            In real modes the prior is the last-60-session up-day frequency from yfinance daily
            bars, shrunk toward 0.5 and clipped to [0.35, 0.65] so a short window can't dominate. It
            is a base-rate estimate, not a market-implied probability.
          </Step>
          <Step n="2" title="Evidence extraction (LLM as parser only)">
            Groq (when a key is set) reads the scout text — yfinance events plus optional Tavily
            news — and returns strict JSON features (CEO buying, institutional trend, regulatory
            risk, insider selling, quality metrics). A deterministic regex heuristic covers keyless
            runs. The model never computes probabilities, prices, or position sizes.
          </Step>
          <Step n="3" title="Bayesian log-odds update">
            Each feature carries a fixed log-likelihood weight. They sum in log-odds space onto the
            prior to produce a posterior. A second, sentiment-only channel is blended in on every
            decision at a configurable weight (<code className="text-accent/90">BAYES_TABLE_WEIGHT</code>,
            default 0.65 to the evidence table / 0.35 to sentiment).
          </Step>
          <Step n="4" title="Edge, leakage guard, and decision">
            Edge = posterior − prior. Before it is acted on, a leakage guard rejects look-ahead
            priors, empty evidence, and future-year text (forcing HOLD). Only |edge| ≥{" "}
            <code className="text-accent/90">EDGE_THRESHOLD</code> (default 0.05) yields a paper BUY
            or SELL; everything else HOLDs.
          </Step>
          <Step n="5" title="Risk sizing">
            A risk overseer caps notional exposure with fractional-Kelly-style scaling on
            |edge|·confidence (10% of a 1,000 USDC notional bankroll), and halts the loop on spend
            or drawdown breaches.
          </Step>
        </div>
      </Panel>

      <Panel title="Data sources">
        <ul className="text-muted space-y-2 leading-relaxed list-disc pl-5">
          <li>
            <strong className="text-white">yfinance</strong> — keyless daily price history and
            fundamentals (an unofficial Yahoo endpoint).
          </li>
          <li>
            <strong className="text-white">Tavily</strong> — finance-topic news, via REST plan
            credits or paid per-call over x402 (USDC on Base) when configured.
          </li>
          <li>
            <strong className="text-white">Groq</strong> — LLM feature extraction only, never
            portfolio math.
          </li>
        </ul>
      </Panel>

      <Panel title="Limitations (what this is not)">
        <ul className="text-muted space-y-2 leading-relaxed list-disc pl-5">
          <li>
            Signals are <strong className="text-white">directional beliefs, not calibrated
            forecasts</strong>. The log-odds weights are hand-set, not fitted; no backtest is
            claimed.
          </li>
          <li>Paper trading only — notional sizes, no broker integration, no real orders.</li>
          <li>yfinance is not a production market-data contract; treat it as research-grade.</li>
          <li>Everything runs on testnet USDC (Base Sepolia). No mainnet value, no custody, no KYC.</li>
        </ul>
      </Panel>

      <div className="rounded-xl border border-warn/40 bg-warn/10 px-4 py-4">
        <div className="text-warn font-semibold text-sm">Not investment advice</div>
        <p className="text-warn/90 text-xs mt-2 leading-relaxed">
          AlphaNet-402 is a research and engineering demonstration. Nothing it produces is legal,
          financial, or investment advice, an offer, or a recommendation to buy or sell any
          security. Outputs are model-generated and may be wrong. Do your own research and consult a
          licensed professional before making any financial decision.
        </p>
      </div>
    </main>
  );
}
