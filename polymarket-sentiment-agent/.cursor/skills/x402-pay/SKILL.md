---
name: x402-pay
description: Install an Open Wallet Standard (OWS) wallet, create a local wallet and record its addresses in CLAUDE.md, and make paid (x402) API requests signed by that wallet in USDC. Triggers - "install the OWS wallet", "set up x402", "create a wallet", "make an x402 payment", "order coffee", "buy premium beans", "pay for URL".
tags: [payments, api, wallet, setup]
---

# x402-pay

This skill covers three actions. Pick the one that matches the request:

1. **[Install OWS](#action-1-install-ows)** — install the OWS CLI and the components this skill needs.
2. **[Create a wallet + record addresses](#action-2-create-a-wallet-and-record-addresses)** — make a local wallet and write its addresses into `CLAUDE.md`.
3. **[Make an x402 payment](#action-3-make-an-x402-payment)** — call an x402-protected URL and pay for it.

Payments are signed by a local **Open Wallet Standard (OWS)** wallet. The private
key stays encrypted in the OWS vault (`~/.ows/wallets/`) and is never written to
the repo, `.env`, or exposed to the script.

---

## Action 1: Install OWS

**The only native component is the global `ows` CLI.** `pay.ts` itself is pure
JavaScript using Node built-ins (`fetch`, `crypto`, `child_process`) — it has no
native node bindings, so it runs on any platform with Node ≥ 18. All cryptography
(EIP-712 signing) happens inside the `ows` CLI.

**a) Install the global `ows` CLI** — installs the prebuilt binary for the host
platform (macOS arm64/x64, Linux x64/arm64):

```bash
npm install -g @open-wallet-standard/core
ows --version
```

> Alternative full installer: `curl -fsSL https://docs.openwallet.sh/install.sh | bash`

**b) Install the script's dependencies** (pure JS — no native code, no compiler):

```bash
cd .claude/skills/x402-pay/scripts
npm install
```

Per `scripts/package.json` there are **no runtime dependencies** at all;
`tsx`/`typescript` are dev tooling to run the `.ts` file. There is no `viem`,
`x402-fetch`, `keccak`, `dotenv`, or any native node addon — the script uses only
Node built-ins, and the OWS CLI does the signing.

---

## Action 2: Create a wallet and record addresses

**1. Create the wallet** with the `ows` CLI. It writes to the vault
(`~/.ows/wallets/`) and derives addresses for every supported chain.

```bash
ows wallet create --name headless-vibe
ows wallet list                          # shows each chain: "eip155:84532 (Base Sepolia) -> 0x.."
```

**2. Record the wallet in `CLAUDE.md`.** Add (or update) a `## Crypto wallet`
section so the address is shared with anyone who clones the project. Include:

- **Wallet name** (e.g. `headless-vibe`)
- **EVM address** — the `eip155:*` account; identical across all EVM chains incl. Base Sepolia
- **Payment network** — Base Sepolia testnet (chain ID **84532**)
- **USDC on Base Sepolia** — `0x036CbD53842c5426634e7929541eC2318f3dCF7e`

Example block to write into `CLAUDE.md`:

```markdown
## Crypto wallet
- Wallet name: **headless-vibe** (OWS, keys in ~/.ows/wallets/)
- EVM address (all EVM chains, incl. Base Sepolia): 0x83425FD2cC0EFECee4b6D5a85A90F7944e2A981c
- Payment network: Base Sepolia testnet (chain ID 84532)
- USDC on Base Sepolia: 0x036CbD53842c5426634e7929541eC2318f3dCF7e
```

**3. No config file needed.** `pay.ts` reads the wallet **name and EVM address
straight from the `## Crypto wallet` section of `CLAUDE.md`** (what you wrote in
step 2). There is no `.env`. Resolution order:

1. `--wallet <name>` flag (address then derived from `ows wallet list`), else
2. CLAUDE.md `## Crypto wallet` section (name + address), else
3. `OWS_WALLET` environment variable.

**4. Fund it.** Send **Base Sepolia USDC** to the EVM address from the Circle
faucet (https://faucet.circle.com → Base Sepolia). **No native ETH needed** — the
x402 facilitator pays the gas. Check the balance with
`ows fund balance --wallet headless-vibe` (or query the chain RPC directly;
MoonPay-style balance APIs do not index testnets).

---

## Action 3: Make an x402 payment

Call an x402-protected endpoint; the script handles the `402 → sign → retry` flow
and pays from the OWS wallet.

The script defaults to **POST** and always sends `Accept: application/json` (many
x402 servers only emit the `402` challenge for JSON POSTs). It implements the
x402 **V1 + V2** "exact" (EIP-3009) flow directly in pure JS. V2 reads
`PAYMENT-REQUIRED` from the 402 response header and retries with `PAYMENT-SIGNATURE`.

```bash
cd .claude/skills/x402-pay/scripts

# Pay for premium beans (the workshop demo endpoint)
npx tsx pay.ts --url https://cafe-chooser-pro.lovable.app/api/public/premium-beans --body '{}'

# Custom POST body
npx tsx pay.ts --url <endpoint> --body '{"size":"large"}'

# A GET-style x402 endpoint
npx tsx pay.ts --url <endpoint> --method GET

# Query params
npx tsx pay.ts --url <endpoint> --params '{"roast":"dark"}'
```

On success it prints the HTTP status, the JSON response, and the settlement
(`transaction`, `network`, `payer`). Verify at
`https://sepolia.basescan.org/tx/<hash>`.

If a request needs a name and none is given, default to **Andy** (see CLAUDE.md).

### How the payment works

1. The script POSTs the request; the server replies `402 Payment Required` with
   the accepted networks/amounts (`accepts[]`).
2. `pay.ts` builds the **EIP-3009 `TransferWithAuthorization`** typed data
   (from `accepts[0]`: `payTo`, `asset`, amount, `extra.name`/`version`, a random
   nonce, validity window) and signs it via the CLI:
   `ows sign message --typed-data <json>` — the key never leaves the vault.
3. The signed authorization is base64-encoded into the `X-PAYMENT` header and the
   request is retried.
4. The server's facilitator settles the transfer on-chain and **pays the gas** —
   the wallet only needs USDC, not ETH.

> Implementation notes:
> - The OWS core wants strict `eth_signTypedData_v4` JSON, so `pay.ts` includes
>   the `EIP712Domain` type definition explicitly.
> - Addresses are passed through as-is (OWS already returns EIP-55 checksummed,
>   and EIP-712 hashing is case-insensitive), so no keccak/checksum code is needed.

### Notes

- Requires the OWS wallet to hold USDC on the target network.
- If the request fails (status ≥ 400) the payment is not settled — you don't pay
  for errors.
- The **x402.org facilitator** is configured on the *server* side (for our own
  paid API later in the workshop), not here — this skill is the *paying client*.

## Related

- `moonpay-check-wallet` — check balances (note: that API does not index testnets).
- OWS SDK/CLI docs: https://github.com/open-wallet-standard/core
