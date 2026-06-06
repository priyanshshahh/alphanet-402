// Records a <90s demo video of the SignalRelay app.
// Usage: node scripts/record-demo.mjs   (frontend dev server must be on :5173)
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

const BASE = process.env.BASE_URL || "http://localhost:5173";
const OUT = "demo-recording";
mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 720 },
  recordVideo: { dir: OUT, size: { width: 1280, height: 720 } },
  deviceScaleFactor: 2,
});
const page = await context.newPage();

async function go(path, wait = 1500) {
  await page.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await sleep(wait);
}

// 1) Pitch deck — step through slides
await go("/pitch", 2200);
for (let i = 0; i < 5; i++) {
  await page.keyboard.press("ArrowRight");
  await sleep(2000);
}
await sleep(800);

// 2) Command Center — the live oracle + equity curve
await go("/", 3500);
await page.mouse.wheel(0, 500);
await sleep(2500);
await page.mouse.wheel(0, -500);
await sleep(800);

// 3) x402 Lab — run the live payment
await go("/x402-lab", 2000);
const btn = page.getByRole("button", { name: /Run the x402 payment/i });
await btn.click();
// let the 5-step flow + balance + revealed alpha play out
await sleep(7000);
await page.mouse.wheel(0, 400);
await sleep(4000);
await page.mouse.wheel(0, 400);
await sleep(3000);

await context.close(); // flushes the video
await browser.close();
console.log(`Saved video to ./${OUT}/ (webm). Total run ~75s.`);
