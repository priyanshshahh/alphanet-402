/**
 * Records pitch-demo.webm: Judge embed (Run pipeline) then Overview (/).
 * For LIVE + AWAL Tavily, allow extra wait via RECORD_POST_CLICK_MS (default 28000).
 *
 * Prereqs: Vite + API running (proxy). One-time: npm run record:demo:install
 *
 *   BASE_URL=http://127.0.0.1:5173 npm run record:demo
 *   RECORD_POST_CLICK_MS=35000 npm run record:demo
 */
import { chromium } from "playwright";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { setTimeout as delay } from "timers/promises";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const publicDir = path.join(__dirname, "..", "public");
const tmpDir = path.join(publicDir, ".pitch-rec");
const base = (process.env.BASE_URL || "http://127.0.0.1:5173").replace(/\/$/, "");
const postClickMs = parseInt(process.env.RECORD_POST_CLICK_MS || "28000", 10);
const overviewMs = parseInt(process.env.RECORD_OVERVIEW_MS || "8000", 10);

async function reachable(url) {
  try {
    const r = await fetch(url, { method: "GET", signal: AbortSignal.timeout(5000) });
    return r.ok;
  } catch {
    return false;
  }
}

async function main() {
  if (!(await reachable(`${base}/`))) {
    console.error(
      `Cannot reach ${base}/ — start Vite first (npm run dev). Use BASE_URL if you use another port.`
    );
    process.exit(1);
  }

  fs.rmSync(tmpDir, { recursive: true, force: true });
  fs.mkdirSync(tmpDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1280, height: 720 },
    recordVideo: { dir: tmpDir, size: { width: 1280, height: 720 } },
  });
  const page = await context.newPage();

  await page.goto(`${base}/demo/embed`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await delay(2000);

  const btn = page.getByRole("button", { name: /Run pipeline/i });
  await btn.waitFor({ state: "visible", timeout: 20000 });
  await btn.click();
  await delay(postClickMs);

  await page.goto(`${base}/`, { waitUntil: "domcontentloaded", timeout: 60000 });
  await page.getByText(/Command Center|AlphaNet-402/i).first().waitFor({ state: "visible", timeout: 20000 });
  await delay(overviewMs);

  await context.close();
  await browser.close();

  const files = fs.readdirSync(tmpDir);
  const webm = files.find((f) => f.endsWith(".webm"));
  if (!webm) {
    console.error("No .webm produced. Contents:", files);
    process.exit(1);
  }

  const dest = path.join(publicDir, "pitch-demo.webm");
  fs.copyFileSync(path.join(tmpDir, webm), dest);
  fs.rmSync(tmpDir, { recursive: true, force: true });

  const stat = fs.statSync(dest);
  console.log(`Wrote ${dest} (${(stat.size / 1024 / 1024).toFixed(2)} MiB)`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
