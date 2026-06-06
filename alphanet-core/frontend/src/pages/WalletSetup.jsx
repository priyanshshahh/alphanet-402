export default function WalletSetup() {
  return (
    <main className="max-w-3xl mx-auto px-6 py-10 space-y-8 text-sm text-slate-200">
      <div>
        <h1 className="text-2xl font-semibold text-white">Agentic Wallet (AWAL)</h1>
        <p className="text-muted mt-2 leading-relaxed">
          Authenticate with email OTP before any <code className="text-accent/90">x402 pay</code>{" "}
          or on-chain action. This mirrors the official CDP Agentic Wallet flow. Full doc index:{" "}
          <a
            className="text-accent hover:underline"
            href="https://docs.cdp.coinbase.com/llms.txt"
            target="_blank"
            rel="noreferrer"
          >
            docs.cdp.coinbase.com/llms.txt
          </a>{" "}
          (also mirrored in-repo at <code className="text-muted">docs/cdp-llms.txt</code>).
        </p>
      </div>

      <section className="rounded-xl border border-edge bg-panel/70 p-5 space-y-4">
        <h2 className="text-xs uppercase tracking-wider text-muted font-semibold">1 · Status</h2>
        <pre className="text-[11px] font-mono bg-ink rounded-lg p-3 border border-edge text-accent/90 overflow-x-auto">
          npx awal@latest status{"\n"}
          npx awal@latest status --json
        </pre>
      </section>

      <section className="rounded-xl border border-edge bg-panel/70 p-5 space-y-4">
        <h2 className="text-xs uppercase tracking-wider text-muted font-semibold">2 · Email OTP</h2>
        <pre className="text-[11px] font-mono bg-ink rounded-lg p-3 border border-edge text-accent/90 overflow-x-auto whitespace-pre">
{`npx awal@latest auth login <your-email>
# copy flowId from output → check email for 6-digit code

npx awal@latest auth verify <flowId> <otp>`}
        </pre>
        <p className="text-xs text-muted">
          If the agent cannot read the inbox, the human pastes the OTP once; afterwards the wallet
          can sign x402 flows autonomously.
        </p>
      </section>

      <section className="rounded-xl border border-edge bg-panel/70 p-5 space-y-4">
        <h2 className="text-xs uppercase tracking-wider text-muted font-semibold">
          3 · Base Sepolia (this project default)
        </h2>
        <pre className="text-[11px] font-mono bg-ink rounded-lg p-3 border border-edge text-accent/90 overflow-x-auto whitespace-pre">
{`npx awal@latest balance --chain base-sepolia
npx awal@latest address --json`}
        </pre>
        <p className="text-xs text-muted">
          Fund test USDC from the Coinbase Base Sepolia faucet, then set{" "}
          <code className="text-white">TRADING_MODE=LIVE</code> in the backend <code>.env</code>.
          The backend appends <code className="text-white">AWAL_X402_PAY_EXTRA</code> (default{" "}
          <code className="text-white">--chain base-sepolia</code>) to Tavily <code>x402 pay</code>{" "}
          calls—clear it if your CLI version resolves chain from the invoice only.
        </p>
      </section>

      <section className="rounded-xl border border-accent/20 bg-accent/5 p-5 text-xs text-muted leading-relaxed">
        <strong className="text-white">Reference</strong> — see{" "}
        <code className="text-accent/90">docs/AWAL_WALLET_SETUP.md</code> in the repo root for a
        short checklist aligned with this UI.
      </section>
    </main>
  );
}
