/**
 * x402-pay — make a paid (x402 V1 + V2) HTTP request from any computer.
 *
 * Pure JavaScript with ZERO npm runtime dependencies: it uses only Node built-ins
 * (fetch, crypto, child_process, fs, Buffer). The only native component is the
 * globally-installed **OWS CLI** (`ows`), which does the signing inside its vault
 * — the private key never leaves `~/.ows/wallets/`.
 *
 * Supports both challenge formats:
 *   V2: PAYMENT-REQUIRED header (base64 JSON) → retry with PAYMENT-SIGNATURE
 *   V1: accepts[] in JSON body              → retry with X-PAYMENT
 *
 * We implement the x402 "exact" (EIP-3009) client flow directly so we don't pull
 * in viem / x402-fetch. OWS handles all cryptography.
 *
 * Wallet selection (no .env needed): --wallet <name>, else the "## Crypto wallet"
 * section of the project's CLAUDE.md (wallet name + EVM address), else OWS_WALLET.
 *
 * Usage:
 *   npx tsx pay.ts --url <endpoint> [--method POST] [--body '<json>'] [--params '<json>'] [--wallet <name>]
 *
 * Requires the OWS CLI on PATH:  npm install -g @open-wallet-standard/core
 */
import { spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";
import { dirname, join } from "node:path";

type Args = { url?: string; method: string; body?: string; params?: string; wallet?: string };

/** network name -> EVM chain id (extend as needed). */
const NETWORK_CHAIN_ID: Record<string, number> = {
  "base-sepolia": 84532,
  base: 8453,
  ethereum: 1,
  "ethereum-sepolia": 11155111,
  "avalanche-fuji": 43113,
  "polygon-amoy": 80002,
};

function parseArgs(argv: string[]): Args {
  const out: Args = { method: "POST" };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => argv[++i];
    switch (a) {
      case "--url": out.url = next(); break;
      case "--method": out.method = (next() ?? "POST").toUpperCase(); break;
      case "--body": out.body = next(); break;
      case "--params": out.params = next(); break;
      case "--wallet": out.wallet = next(); break;
      default: if (!a.startsWith("--") && !out.url) out.url = a;
    }
  }
  return out;
}

function fail(msg: string): never {
  console.error(`\n✗ ${msg}`);
  process.exit(1);
}

/** Run the `ows` CLI, returning trimmed stdout. Fails clearly if it's not installed. */
function ows(args: string[]): string {
  const res = spawnSync("ows", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] });
  if (res.error) {
    if ((res.error as NodeJS.ErrnoException).code === "ENOENT") {
      fail("OWS CLI not found. Install it: npm install -g @open-wallet-standard/core");
    }
    fail(`failed to run ows: ${res.error.message}`);
  }
  if (res.status !== 0) fail(`ows ${args.slice(0, 2).join(" ")} failed: ${(res.stderr || res.stdout || "").trim()}`);
  return (res.stdout || "").trim();
}

/** Resolve a wallet's EVM (eip155) address from `ows wallet list`. */
function evmAddress(wallet: string): string {
  const text = "\n" + ows(["wallet", "list"]);
  for (const block of text.split(/\nID:\s/).slice(1)) {
    if (new RegExp(`\\nName:\\s+${wallet}(\\s|$)`, "m").test("\n" + block)) {
      const m = block.match(/eip155:[^\n]*?(0x[0-9a-fA-F]{40})/);
      if (m) return m[1];
    }
  }
  fail(`No EVM address for OWS wallet "${wallet}". Create it: ows wallet create --name ${wallet}`);
}

/** Walk up from cwd and this file's dir to locate the project's CLAUDE.md. */
function findClaudeMd(): string | undefined {
  for (const base of [process.cwd(), import.meta.dirname]) {
    let dir = base;
    while (dir) {
      const p = join(dir, "CLAUDE.md");
      if (existsSync(p)) return p;
      const parent = dirname(dir);
      if (parent === dir) break;
      dir = parent;
    }
  }
  return undefined;
}

/** Read the wallet name + EVM address from CLAUDE.md's "## Crypto wallet" section. */
function walletFromClaudeMd(): { name?: string; address?: string } {
  const path = findClaudeMd();
  if (!path) return {};
  const text = readFileSync(path, "utf8");
  const section = text.match(/##\s+Crypto wallet[\s\S]*?(?=\n#{1,2}\s|$)/i)?.[0] ?? text;
  // Skip any markdown decoration (**, `, _) between the label and the name.
  const name = section.match(/wallet name:\s*[^A-Za-z0-9]*([A-Za-z0-9._-]+)/i)?.[1];
  const address = section.match(/0x[0-9a-fA-F]{40}/)?.[0];
  return { name, address };
}

/** Sign EIP-712 typed data in the OWS vault, returning a 0x r||s||v signature. */
function owsSignTypedData(wallet: string, chainId: number, typedData: object): string {
  const out = ows([
    "sign", "message", "--json",
    "--wallet", wallet, "--chain", `eip155:${chainId}`,
    "--message", "", "--typed-data", JSON.stringify(typedData),
  ]);
  const parsed = JSON.parse(out) as { signature: string; recovery_id?: number | null };
  let sig = parsed.signature.replace(/^0x/, "");
  if (sig.length === 128 && parsed.recovery_id != null) {
    const v = parsed.recovery_id >= 27 ? parsed.recovery_id : 27 + parsed.recovery_id;
    sig += v.toString(16).padStart(2, "0");
  }
  return "0x" + sig;
}

type Requirements = {
  scheme: string;
  network: string;
  maxAmountRequired: string;
  payTo: string;
  asset: string;
  maxTimeoutSeconds: number;
  extra?: { name?: string; version?: string };
};

type Challenge = { x402Version: number; accepts: Requirements[] };

/** Resolve EVM chain id from legacy name or CAIP-2 (e.g. eip155:84532). */
function chainIdFromNetwork(network: string): number {
  if (NETWORK_CHAIN_ID[network]) return NETWORK_CHAIN_ID[network];
  const m = network.match(/^eip155:(\d+)$/i);
  if (m) return parseInt(m[1], 10);
  fail(`Unknown x402 network "${network}". Use CAIP-2 (eip155:84532) or add to NETWORK_CHAIN_ID.`);
}

/** Normalize V1/V2 accept objects to a single Requirements shape. */
function normalizeAccept(raw: Record<string, unknown>): Requirements {
  const amount = String(raw.maxAmountRequired ?? raw.amount ?? "");
  if (!amount) fail("Payment requirements missing amount / maxAmountRequired.");
  return {
    scheme: String(raw.scheme ?? "exact"),
    network: String(raw.network ?? ""),
    maxAmountRequired: amount,
    payTo: String(raw.payTo ?? ""),
    asset: String(raw.asset ?? ""),
    maxTimeoutSeconds: Number(raw.maxTimeoutSeconds ?? 300),
    extra: raw.extra as Requirements["extra"],
  };
}

/** Parse 402 challenge from PAYMENT-REQUIRED header (V2) or JSON body (V1). */
async function parseChallengeAsync(response: Response): Promise<Challenge> {
  const header =
    response.headers.get("payment-required") ??
    response.headers.get("PAYMENT-REQUIRED");
  if (header) {
    const decoded = JSON.parse(Buffer.from(header, "base64").toString("utf8")) as {
      x402Version?: number;
      accepts?: Record<string, unknown>[];
    };
    const accepts = (decoded.accepts ?? []).map(normalizeAccept);
    if (!accepts.length) fail("PAYMENT-REQUIRED header had no accepts[].");
    return { x402Version: decoded.x402Version ?? 2, accepts };
  }
  const body = (await response.clone().json().catch(() => ({}))) as {
    x402Version?: number;
    accepts?: Record<string, unknown>[];
  };
  const accepts = (body.accepts ?? []).map(normalizeAccept);
  if (!accepts.length) fail("402 response had no accepts[] in body or PAYMENT-REQUIRED header.");
  return { x402Version: body.x402Version ?? 1, accepts };
}

/** Build the base64 payment header for the x402 "exact" EVM scheme (V1 + V2). */
function buildPaymentHeader(wallet: string, from: string, x402Version: number, req: Requirements): string {
  const chainId = chainIdFromNetwork(req.network);
  if (req.scheme !== "exact") fail(`Unsupported x402 scheme "${req.scheme}" (only "exact" is implemented).`);

  const now = Math.floor(Date.now() / 1000);
  const authorization = {
    from,
    to: req.payTo,
    value: req.maxAmountRequired,
    validAfter: String(now - 600),                 // 10 min of clock skew
    validBefore: String(now + req.maxTimeoutSeconds),
    nonce: "0x" + randomBytes(32).toString("hex"),
  };

  // EIP-712 payload. EIP712Domain is defined explicitly (the OWS core requires
  // strict eth_signTypedData_v4 JSON that declares it).
  const typedData = {
    types: {
      EIP712Domain: [
        { name: "name", type: "string" },
        { name: "version", type: "string" },
        { name: "chainId", type: "uint256" },
        { name: "verifyingContract", type: "address" },
      ],
      TransferWithAuthorization: [
        { name: "from", type: "address" },
        { name: "to", type: "address" },
        { name: "value", type: "uint256" },
        { name: "validAfter", type: "uint256" },
        { name: "validBefore", type: "uint256" },
        { name: "nonce", type: "bytes32" },
      ],
    },
    domain: {
      name: req.extra?.name,
      version: req.extra?.version,
      chainId,
      verifyingContract: req.asset,
    },
    primaryType: "TransferWithAuthorization",
    message: authorization,
  };

  const signature = owsSignTypedData(wallet, chainId, typedData);
  const innerPayload = { authorization, signature };

  if (x402Version >= 2) {
    // V2: scheme/network live under `accepted`, not top-level (see x402/schemas/payments.py).
    const payment = {
      x402Version: 2,
      payload: innerPayload,
      accepted: {
        scheme: req.scheme,
        network: req.network,
        asset: req.asset,
        amount: req.maxAmountRequired,
        payTo: req.payTo,
        maxTimeoutSeconds: req.maxTimeoutSeconds,
        extra: req.extra ?? {},
      },
    };
    return Buffer.from(JSON.stringify(payment)).toString("base64");
  }

  // V1 legacy envelope
  const payment = {
    x402Version: 1,
    scheme: req.scheme,
    network: req.network,
    payload: innerPayload,
  };
  return Buffer.from(JSON.stringify(payment)).toString("base64");
}

async function main(): Promise<void> {
  const args = parseArgs(process.argv.slice(2));
  if (!args.url) fail("Missing --url <x402-protected endpoint>.");

  // Resolve the wallet: --wallet override, else CLAUDE.md, else OWS_WALLET env.
  const fromClaude = walletFromClaudeMd();
  const wallet = args.wallet ?? fromClaude.name ?? process.env.OWS_WALLET;
  if (!wallet) {
    fail(
      "No wallet. Add a '## Crypto wallet' section with 'Wallet name: <name>' to " +
        "CLAUDE.md, or pass --wallet <name>.",
    );
  }
  // Use the saved address from CLAUDE.md when not overriding; otherwise derive it
  // from the vault via the CLI.
  const from = !args.wallet && fromClaude.address ? fromClaude.address : evmAddress(wallet);

  let url = args.url!;
  if (args.params) {
    let parsed: Record<string, string>;
    try { parsed = JSON.parse(args.params); } catch { fail("--params must be a JSON object."); }
    const u = new URL(url);
    for (const [k, v] of Object.entries(parsed!)) u.searchParams.set(k, String(v));
    url = u.toString();
  }

  console.log(`Wallet:  ${wallet}  (${from})`);
  console.log(`Request: ${args.method} ${url}\n`);

  const headers: Record<string, string> = { Accept: "application/json" };
  if (args.body && !["GET", "HEAD"].includes(args.method)) headers["Content-Type"] = "application/json";
  const baseInit: RequestInit = { method: args.method, headers, body: args.body };

  // 1) Initial request — expect a 402 challenge.
  let response = await fetch(url, baseInit);

  if (response.status === 402) {
    const challenge = await parseChallengeAsync(response);
    const req = challenge.accepts[0];
    const usdc = Number(req.maxAmountRequired) / 1e6;
    console.log(
      `Paying:  ${req.maxAmountRequired} base units (~${usdc} USDC) on ${req.network} -> ${req.payTo}`,
    );
    console.log(`x402:    v${challenge.x402Version}`);

    const paymentB64 = buildPaymentHeader(wallet, from, challenge.x402Version, req);

    // V2: PAYMENT-SIGNATURE. V1: X-PAYMENT. Send both when version unknown.
    const payHeaders: Record<string, string> = { ...headers };
    if (challenge.x402Version >= 2) {
      payHeaders["PAYMENT-SIGNATURE"] = paymentB64;
    } else {
      payHeaders["X-PAYMENT"] = paymentB64;
    }
    // Belt-and-suspenders for mixed stacks
    payHeaders["PAYMENT-SIGNATURE"] = paymentB64;
    payHeaders["X-PAYMENT"] = paymentB64;

    response = await fetch(url, { ...baseInit, headers: payHeaders });
  }

  const contentType = response.headers.get("content-type") ?? "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();

  console.log(`\nStatus:  ${response.status} ${response.statusText}`);
  console.log("Body:", typeof payload === "string" ? payload : JSON.stringify(payload, null, 2));

  const settleHeader =
    response.headers.get("payment-response") ??
    response.headers.get("PAYMENT-RESPONSE") ??
    response.headers.get("x-payment-response");
  if (settleHeader) {
    const settle = JSON.parse(Buffer.from(settleHeader, "base64").toString("utf8"));
    console.log("\nPayment settled:", JSON.stringify(settle, null, 2));
  }

  if (!response.ok) process.exit(1);
}

main().catch((err) => fail(err?.message ?? String(err)));
