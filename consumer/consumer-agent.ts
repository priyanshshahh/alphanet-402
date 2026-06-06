/**
 * AlphaNet-402 — Consumer Agent
 * -----------------------------
 * The "spender" in the agent-to-agent commerce loop. A downstream trading
 * agent that hires the Polymarket Sentiment Oracle for its Bayesian edge.
 *
 * Flow (handled automatically by wrapFetchWithPayment):
 *   1. GET /api/trade/{id}/rationale            -> 402 Payment Required
 *   2. Privy TEE signs a $0.01 USDC authorization on Base Sepolia
 *   3. Facilitator settles, returns a receipt
 *   4. Request is retried with the X-PAYMENT header -> 200 OK + alpha JSON
 *
 * The agent NEVER holds the wallet private key. It uses a Privy-authorized
 * session (one-time human approval via `privy-agent-wallets login`).
 */
import { PrivyClient } from "@privy-io/node";
import { createX402Client } from "@privy-io/node/x402";
import { wrapFetchWithPayment } from "@x402/fetch";
import * as dotenv from "dotenv";

dotenv.config();

function requireEnv(name: string): string {
  const v = process.env[name];
  if (!v) {
    console.error(`Missing required env var: ${name} (see consumer/.env.example)`);
    process.exit(1);
  }
  return v;
}

async function executeAgentCommerce(): Promise<void> {
  console.log("Initializing AlphaNet-402 Consumer Agent…");

  const privy = new PrivyClient({
    appId: requireEnv("PRIVY_APP_ID"),
    appSecret: requireEnv("PRIVY_APP_SECRET"),
  });

  const walletId = requireEnv("PRIVY_AGENT_WALLET_ID");
  const providerUrl = (process.env.PROVIDER_URL ?? "http://localhost:8000").replace(/\/$/, "");
  const tradeId = process.env.TRADE_ID ?? "1";
  const maxValue = BigInt(process.env.MAX_PAYMENT_BASE_UNITS ?? "1000000"); // $1.00 cap

  console.log(`Connecting to Privy Wallet ID: ${walletId}`);
  const wallet = await privy.wallets().get({ walletId });
  console.log(`Wallet address confirmed: ${wallet.address}`);

  // chain type (EVM/Base) is inferred from the 402 challenge parameters.
  const x402client = createX402Client(privy, {
    walletId: wallet.id,
    address: wallet.address,
  });

  // Native fetch, augmented: intercepts 402, signs via Privy, settles, retries.
  const fetchWithPayment = wrapFetchWithPayment(fetch, x402client, { maxValue });

  const target = `${providerUrl}/api/trade/${tradeId}/rationale`;
  console.log("Requesting Bayesian rationale from Provider Agent…");
  console.log(`Target: GET ${target}`);

  const response = await fetchWithPayment(target);
  if (!response.ok) {
    throw new Error(`Agent commerce failed with status: ${response.status}`);
  }

  const data = await response.json();
  const receipt = response.headers.get("x-payment-response") ?? response.headers.get("payment-response");

  console.log("=========================================");
  console.log(" x402 Transaction Successful (Base Sepolia)");
  console.log("=========================================");
  if (receipt) console.log(`Payment receipt: ${receipt}`);
  console.log("Acquired financial intelligence:");
  console.log(JSON.stringify(data, null, 2));
}

executeAgentCommerce().catch((error) => {
  console.error("Agent execution encountered a critical error:", error);
  process.exit(1);
});
