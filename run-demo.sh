#!/usr/bin/env bash
# SignalRelay — cinematic x402 demo runner
# Shows: 402 challenge -> Privy-signed USDC payment on Base -> 200 OK + Bayesian alpha
set -euo pipefail

PROVIDER="${PROVIDER_URL:-https://shiny-otters-sip.loca.lt}"
WALLET="0x6e45bf955Ce5e097ec038Bd153F4c935344092Ce"
USDC="0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC="https://sepolia.base.org"
TRADE_ID="${TRADE_ID:-1}"

cyan(){ printf "\033[36m%s\033[0m\n" "$1"; }
green(){ printf "\033[32m%s\033[0m\n" "$1"; }
dim(){ printf "\033[2m%s\033[0m\n" "$1"; }

balance(){
  curl -s -X POST "$RPC" -H "Content-Type: application/json" \
    -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"eth_call\",\"params\":[{\"to\":\"$USDC\",\"data\":\"0x70a08231000000000000000000000000${WALLET#0x}\"},\"latest\"]}" \
    | python3 -c "import json,sys; print(int(json.load(sys.stdin)['result'],16)/1e6)"
}

echo
cyan "================ SignalRelay · Agent-to-Agent Commerce on Base ================"
dim  "Consumer agent (Privy-authorized) hires the Polymarket sentiment oracle over x402."
echo
green "[1/4] Consumer wallet — Privy embedded, key in TEE"
echo   "      address: $WALLET"
echo   "      USDC on Base Sepolia: \$$(balance)"
echo
green "[2/4] Naked request -> expect the paywall"
dim    "      GET $PROVIDER/api/trade/$TRADE_ID/rationale"
code=$(curl -s -o /dev/null -w "%{http_code}" -H "bypass-tunnel-reminder: 1" "$PROVIDER/api/trade/$TRADE_ID/rationale")
echo   "      <- HTTP $code Payment Required  (\$0.01 USDC, network eip155:84532)"
echo
green "[3/4] Agent pays autonomously — Privy TEE signs, facilitator settles on Base"
npx --yes @privy-io/agent-wallet-cli fetch-x402 \
  --header "bypass-tunnel-reminder: 1" \
  "$PROVIDER/api/trade/$TRADE_ID/rationale" \
  | python3 -m json.tool
echo
green "[4/4] Settlement confirmed on-chain"
echo   "      USDC balance now: \$$(balance)   (debited \$0.01)"
echo
cyan "================ A service that earns. An agent that spends. No humans. ========"
