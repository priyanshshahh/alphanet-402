// Focused ~30s clip of the live x402 payment in the x402 Lab.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
const BASE = process.env.BASE_URL || "http://localhost:5173";
const OUT = "demo-recording/x402";
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = await chromium.launch();
const ctx = await b.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 720 } },
  deviceScaleFactor: 2,
});
const p = await ctx.newPage();
await p.goto(`${BASE}/x402-lab`, { waitUntil: "networkidle" });
await sleep(2500); // show the hero + consumer wallet + live balance
await p.getByRole("button", { name: /Run the x402 payment/i }).click();
await sleep(8000); // 5-step flow animates + balance refresh + alpha reveal
await p.mouse.wheel(0, 380); // scroll to 402 terms + delivered alpha
await sleep(4500);
await p.mouse.wheel(0, 380);
await sleep(3000);
await ctx.close();
await b.close();
console.log("saved x402 clip");
