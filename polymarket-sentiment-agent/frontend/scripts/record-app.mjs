// Full-app demo clip: Command Center -> x402 Lab live payment. No pitch slides.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
const BASE = process.env.BASE_URL || "http://localhost:5173";
const OUT = "demo-recording/app";
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = await chromium.launch();
const ctx = await b.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 720 } },
  deviceScaleFactor: 2,
});
const p = await ctx.newPage();

// 1) COMMAND CENTER — portfolio, equity curve, trades, signals, markets, news
await p.goto(`${BASE}/`, { waitUntil: "networkidle" });
await sleep(3000);                 // portfolio + equity curve
await p.mouse.wheel(0, 420);
await sleep(2500);                 // trade log
await p.mouse.wheel(0, 420);
await sleep(2500);                 // signals + markets
await p.mouse.wheel(0, 420);
await sleep(2200);                 // news + decision log
await p.mouse.wheel(0, -1260);
await sleep(800);

// 2) X402 LAB — run the live payment
await p.goto(`${BASE}/x402-lab`, { waitUntil: "networkidle" });
await sleep(2500);                 // hero + consumer wallet + live balance
await p.getByRole("button", { name: /Run the x402 payment/i }).click();
await sleep(8000);                 // 5-step flow + balance refresh + alpha reveal
await p.mouse.wheel(0, 380);
await sleep(4500);                 // 402 terms + delivered alpha
await p.mouse.wheel(0, 380);
await sleep(3000);                 // terminal reproduce block

await ctx.close();
await b.close();
console.log("saved full-app clip");
