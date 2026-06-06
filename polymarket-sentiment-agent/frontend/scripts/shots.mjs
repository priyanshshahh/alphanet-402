import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
const BASE = "http://localhost:5173";
const OUT = "demo-recording";
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const b = await chromium.launch();
const ctx = await b.newContext({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 2 });
const p = await ctx.newPage();
async function shot(path, name, wait = 2500, run = false) {
  await p.goto(`${BASE}${path}`, { waitUntil: "networkidle" });
  await sleep(wait);
  if (run) {
    await p.getByRole("button", { name: /Run the x402 payment/i }).click();
    await sleep(7000);
  }
  await p.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log("shot", name);
}
await shot("/pitch", "01-pitch");
await shot("/", "02-command-center", 3500);
await shot("/x402-lab", "03-x402-lab", 2000, true);
await ctx.close();
await b.close();
