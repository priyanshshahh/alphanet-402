export function fmtUsd(n) {
  return `$${Number(n ?? 0).toFixed(2)}`;
}

/** Poly-style Pill tone for BUY / SELL / HOLD */
export function decisionPillTone(d) {
  if (d === "BUY") return "positive";
  if (d === "SELL") return "negative";
  return "neutral";
}

export function sentimentPillTone(s) {
  if (s === "bullish") return "positive";
  if (s === "bearish") return "negative";
  return "neutral";
}
