import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { parsePitchDemoVideoUrl } from "../utils/pitchDemoVideo";

const envVideo = import.meta.env.VITE_PITCH_DEMO_VIDEO_URL;

const SLIDES = [
  {
    key: "title",
    render: () => (
      <div className="text-center space-y-6">
        <p className="text-xs uppercase tracking-[0.35em] text-accent/90 font-medium">
          Submission deck · ~3–5 min with demo
        </p>
        <h1 className="text-5xl md:text-7xl font-semibold text-white tracking-tight leading-[1.05]">
          AlphaNet<span className="text-accent">-402</span>
        </h1>
        <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto font-light">
          An autonomous, self-funding <span className="text-white font-medium">equities intelligence agent</span>{" "}
          — scout real market data, quantify, risk-manage, settle on Base, sell alpha over HTTP 402.
        </p>
        <p className="text-sm text-muted pt-2">FastAPI · React · SQLite · Base · AWAL · yfinance · Tavily · Groq</p>
      </div>
    ),
  },
  {
    key: "loop",
    render: () => (
      <div className="max-w-4xl mx-auto space-y-6">
        <h2 className="text-xs uppercase tracking-[0.3em] text-accent font-medium">How the fund runs</h2>
        <p className="text-2xl md:text-3xl text-white font-semibold leading-snug">
          One loop: <span className="text-accent">Scout</span> → <span className="text-accent">Quant</span> →{" "}
          <span className="text-accent">Risk</span> → <span className="text-accent">Monetize</span>.
        </p>
        <ul className="space-y-3 text-sm text-muted leading-relaxed">
          <li className="rounded-xl border border-edge bg-panel/50 px-4 py-3">
            <strong className="text-white">Scout</strong> — Tavily (REST credits or x402+AWAL) pulls live narrative and
            flow language; logs prove the call path.
          </li>
          <li className="rounded-xl border border-edge bg-panel/50 px-4 py-3">
            <strong className="text-white">Quant</strong> — Groq shapes text into JSON; Bayesian edges and posteriors
            are computed in Python only.
          </li>
          <li className="rounded-xl border border-edge bg-panel/50 px-4 py-3">
            <strong className="text-white">Risk</strong> — Spend caps, drawdown limits, leakage-aware guards; the loop
            halts instead of ghost-trading.
          </li>
          <li className="rounded-xl border border-edge bg-panel/50 px-4 py-3">
            <strong className="text-white">Monetize</strong> — HTTP 402 sells structured rationale for micro-USDC;
            receipts are idempotent.
          </li>
        </ul>
      </div>
    ),
  },
  {
    key: "demo",
    render: () => <DemoSlide />,
  },
  {
    key: "stack",
    render: () => (
      <div className="max-w-4xl mx-auto space-y-6">
        <h2 className="text-xs uppercase tracking-[0.3em] text-muted font-medium">Stack &amp; settlement</h2>
        <h3 className="text-2xl md:text-3xl font-semibold text-white">Production-shaped, demo-ready</h3>
        <div className="flex flex-wrap gap-2">
          {["FastAPI", "React", "SQLite", "Base Mainnet", "USDC", "Coinbase AWAL", "HTTP 402", "Tavily", "Groq"].map(
            (x) => (
              <span
                key={x}
                className="px-3 py-1.5 rounded-full border border-edge bg-panel/80 text-xs text-slate-200"
              >
                {x}
              </span>
            )
          )}
        </div>
        <p className="text-muted text-sm leading-relaxed">
          Hackathon builds default to <strong className="text-white">Base Sepolia</strong> + test USDC so judges can
          run safely; flip env to mainnet CAIP-2 and contract addresses for production AWAL settlement.
        </p>
      </div>
    ),
  },
  {
    key: "cta",
    render: () => (
      <div className="text-center space-y-8 max-w-2xl mx-auto">
        <h2 className="text-3xl md:text-4xl font-semibold text-white">Ship the slice</h2>
        <div className="flex flex-wrap gap-3 justify-center">
          <Link
            to="/demo"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl bg-accent text-ink text-sm font-semibold hover:opacity-95"
          >
            Judge demo
          </Link>
          <Link
            to="/x402-lab"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl border border-edge bg-panel/80 text-sm text-white hover:border-accent/30"
          >
            x402 Lab
          </Link>
          <Link
            to="/"
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl border border-edge bg-panel/80 text-sm text-white hover:border-accent/30"
          >
            Command Center
          </Link>
        </div>
        <p className="text-[11px] text-muted">Space / → next · ← previous · Exit deck above</p>
      </div>
    ),
  },
];

function DemoSlide() {
  const parsed = useMemo(() => parsePitchDemoVideoUrl(envVideo), []);
  /** If bundled `/pitch-demo.webm` / `.mp4` fail to load, fall back to live embed. */
  const [localVideoFailed, setLocalVideoFailed] = useState(false);

  const showYoutube = parsed.kind === "youtube" && parsed.youtubeId;
  const showFile = parsed.kind === "file" && parsed.href;
  const showLoom = parsed.kind === "iframe" && parsed.href;
  const tryBundledLocal = parsed.kind === "none" && !localVideoFailed;
  const showEmbedFallback = parsed.kind === "none" && localVideoFailed;

  return (
    <div className="w-full max-w-5xl mx-auto space-y-4">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-2">
        <div>
          <h2 className="text-xs uppercase tracking-[0.3em] text-accent font-medium">Demo</h2>
          <h3 className="text-2xl md:text-3xl font-semibold text-white mt-2">See the product in action</h3>
        </div>
        <p className="text-[11px] text-muted max-w-md text-right md:text-right">
          {showYoutube || showFile || showLoom || tryBundledLocal
            ? "Recorded walkthrough (~60–90s) when public/pitch-demo.webm is present"
            : "Live embedded judge console"}
        </p>
      </div>

      <div className="relative aspect-video w-full rounded-2xl overflow-hidden border border-edge bg-black shadow-[0_0_0_1px_rgba(124,246,196,0.08),0_24px_80px_rgba(0,0,0,0.45)]">
        {showYoutube && (
          <iframe
            title="AlphaNet-402 demo video"
            className="absolute inset-0 w-full h-full"
            src={`https://www.youtube-nocookie.com/embed/${parsed.youtubeId}?rel=0`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowFullScreen
          />
        )}
        {showFile && (
          <video className="absolute inset-0 w-full h-full" controls playsInline src={parsed.href}>
            <track kind="captions" />
          </video>
        )}
        {showLoom && (
          <iframe title="Demo (Loom)" className="absolute inset-0 w-full h-full" src={parsed.href} allowFullScreen />
        )}
        {tryBundledLocal && (
          <video
            className="absolute inset-0 w-full h-full"
            controls
            playsInline
            preload="metadata"
            onError={() => setLocalVideoFailed(true)}
          >
            <source src="/pitch-demo.webm" type="video/webm" />
            <source src="/pitch-demo.mp4" type="video/mp4" />
            <track kind="captions" />
          </video>
        )}
        {showEmbedFallback && (
          <iframe
            title="Live judge demo"
            className="absolute inset-0 w-full h-full bg-ink"
            src="/demo/embed"
          />
        )}
      </div>

      <div className="rounded-xl border border-edge/80 bg-panel/40 px-4 py-3 text-[11px] text-muted leading-relaxed">
        <strong className="text-white">Recording:</strong> from repo root,{" "}
        <code className="text-accent/90">npm run record:demo:install</code> then{" "}
        <code className="text-accent/90">npm run record:demo</code> (Judge embed + Overview →{" "}
        <code className="text-accent/90">public/pitch-demo.webm</code>
        ). Optional: <code className="text-accent/90">RECORD_POST_CLICK_MS</code>,{" "}
        <code className="text-accent/90">RECORD_OVERVIEW_MS</code>. Or set{" "}
        <code className="text-accent/90">VITE_PITCH_DEMO_VIDEO_URL</code> (see{" "}
        <code className="text-accent/90">alphanet-core/frontend/.env.example</code>).
      </div>
    </div>
  );
}

export default function PitchDeck() {
  const [i, setI] = useState(0);
  const total = SLIDES.length;
  const go = useCallback(
    (d) => {
      setI((x) => Math.max(0, Math.min(total - 1, x + d)));
    },
    [total]
  );

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        go(1);
      } else if (e.key === "ArrowLeft") go(-1);
      else if (e.key === "Home") setI(0);
      else if (e.key === "End") setI(total - 1);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, total]);

  const slide = SLIDES[i];

  return (
    <div className="fixed inset-0 z-[100] bg-ink text-slate-200 flex flex-col overflow-hidden">
      <div
        className="absolute inset-y-0 left-0 w-16 md:w-24 z-10 cursor-w-resize hover:bg-white/[0.03]"
        onClick={() => go(-1)}
        aria-hidden
      />
      <div
        className="absolute inset-y-0 right-0 w-16 md:w-24 z-10 cursor-e-resize hover:bg-white/[0.03]"
        onClick={() => go(1)}
        aria-hidden
      />

      <header className="relative z-20 flex items-center justify-between px-4 md:px-8 py-3 border-b border-edge/80 bg-panel/40 backdrop-blur-md">
        <span className="text-[10px] md:text-xs tracking-[0.25em] text-muted font-medium">ALPHANET 402</span>
        <div className="flex items-center gap-3">
          <span className="text-[11px] text-muted hidden sm:inline">
            {i + 1} / {total}
          </span>
          <Link
            to="/"
            className="text-[11px] px-3 py-1.5 rounded-lg border border-edge text-muted hover:text-white hover:border-accent/30"
          >
            Exit deck
          </Link>
        </div>
      </header>

      <main className="relative z-0 flex-1 flex items-center justify-center px-6 md:px-16 py-8 md:py-12 overflow-y-auto">
        <div key={slide.key} className="w-full motion-reduce:opacity-100" style={{ animation: "pitchFade 420ms ease-out" }}>
          {slide.render()}
        </div>
      </main>

      <footer className="relative z-20 border-t border-edge/80 bg-panel/40 backdrop-blur-md px-4 md:px-8 py-4">
        <div className="max-w-3xl mx-auto flex items-center gap-2">
          {SLIDES.map((s, idx) => (
            <button
              key={s.key}
              type="button"
              onClick={() => setI(idx)}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                idx === i ? "bg-accent" : "bg-edge hover:bg-muted/40"
              }`}
              aria-label={`Go to slide ${idx + 1}`}
            />
          ))}
        </div>
        <p className="text-center text-[10px] text-muted mt-3">Space / → next · ← previous</p>
      </footer>

      <style>{`
        @keyframes pitchFade {
          from { opacity: 0; transform: translateY(8px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
