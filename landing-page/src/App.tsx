import { Fragment, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { Nav, Footer, Reveal } from "./chrome";
import { Docs } from "./pages/Docs";

/* ── Install tabs — terminal-inspired, tabbed install commands ───── */
type InstallCmd = { key: string; pre: string; pkg: string; post: string; soon?: boolean };
const INSTALL: InstallCmd[] = [
  { key: "pip", pre: "pip install", pkg: "prescale", post: "" },
  { key: "curl", pre: "curl -fsSL", pkg: "prescale.dev/install", post: " | sh", soon: true },
  { key: "npm", pre: "npm install -g", pkg: "prescale", post: "", soon: true },
  { key: "bun", pre: "bun add -g", pkg: "prescale", post: "", soon: true },
  { key: "brew", pre: "brew install", pkg: "prescale", post: "", soon: true },
  { key: "paru", pre: "paru -S", pkg: "prescale", post: "", soon: true },
];
const fullCmd = (c: InstallCmd) => `${c.pre} ${c.pkg}${c.post}`;

function InstallTabs() {
  const [tab, setTab] = useState("pip"); // pip active by default (the real path)
  const [copied, setCopied] = useState(false);
  const active = INSTALL.find((i) => i.key === tab)!;

  const copy = () => {
    if (active.soon) return;
    navigator.clipboard?.writeText(fullCmd(active));
    setCopied(true);
    setTimeout(() => setCopied(false), 1200);
  };

  return (
    <div id="install" className="mt-8 w-full max-w-2xl border border-line-strong bg-night-raised font-mono">
      {/* header — tabs */}
      <div className="flex border-b border-line-strong text-[0.95rem]">
        {INSTALL.map((i) => {
          const on = tab === i.key;
          return (
            <button
              key={i.key}
              onClick={() => setTab(i.key)}
              className={`-mb-px flex items-center gap-1.5 border-b-2 px-5 py-3.5 transition-colors ${
                on
                  ? "border-cream text-cream"
                  : "border-transparent text-dim hover:text-cream"
              }`}
            >
              {i.key}
              {i.soon && <span className="h-1.5 w-1.5 bg-accent" title="coming soon" />}
            </button>
          );
        })}
      </div>
      {/* content — active command + copy icon, or a coming-soon note */}
      <div className="flex items-center justify-between gap-3 px-5 py-5 text-[1.05rem]">
        {active.soon ? (
          <span className="truncate">
            <span className="text-faint">Coming soon</span>
            <span className="text-dim"> — {active.key} support is on the way.</span>
          </span>
        ) : (
          <>
            <span className="truncate">
              <span className="select-none text-dim">{active.pre} </span>
              <span className="font-bold text-cream">{active.pkg}</span>
              <span className="text-dim">{active.post}</span>
            </span>
            <button
              onClick={copy}
              aria-label="Copy install command"
              className="shrink-0 text-dim transition-colors hover:text-cream"
            >
              {copied ? (
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
              ) : (
                <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="9" width="13" height="13" rx="0" />
                  <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                </svg>
              )}
            </button>
          </>
        )}
      </div>
    </div>
  );
}

/* ── Hero — headline over a full-bleed video, zoom on the Diagnosis ─ */
function Hero() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [zoomed, setZoomed] = useState(false);

  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    const onTime = () => {
      if (!v.duration || Number.isNaN(v.duration)) return;
      setZoomed(v.currentTime >= v.duration - 3.4); // Diagnosis lands ~3.4s before end
    };
    v.addEventListener("timeupdate", onTime);
    return () => v.removeEventListener("timeupdate", onTime);
  }, []);

  return (
    <section className="border-b border-line">
      <div className="flex flex-col items-start px-8 pt-20 pb-16 sm:px-12 sm:pt-28 sm:pb-24">
        <div className="mb-8 inline-flex w-fit items-center gap-2 border border-line-strong px-2.5 py-1 text-[0.72rem] text-dim">
          <span className="bg-cream px-1.5 py-0.5 font-medium text-night">New</span>
          v0.2 <span className="text-faint">·</span> Apache-2.0
        </div>
        <h1 className="max-w-[18ch] text-[clamp(2.2rem,6vw,3.5rem)] font-medium leading-[1.05] tracking-[-0.03em]">
          Find what breaks before your users do.
        </h1>
        <p className="mt-8 max-w-2xl text-[0.95rem] leading-relaxed text-dim">
          PreScale is an open-source CLI that load-tests your site before it sees real traffic.
          Point it at a URL — it ramps virtual users, finds which route breaks first, and tells
          you, in plain English, when your app falls over.
        </p>
        <InstallTabs />
        <p className="mt-5 text-[0.72rem] text-faint">Free · works with any stack · no account required</p>
      </div>
      <div className={`vid-wrap relative overflow-hidden border-t border-line bg-night ${zoomed ? "zoomed" : ""}`}>
        <video
          ref={videoRef}
          className="vid block w-full object-cover"
          autoPlay
          muted
          loop
          playsInline
          poster="/poster.png"
        >
          <source src="/hero.webm" type="video/webm" />
          <source src="/hero.mp4" type="video/mp4" />
        </video>
      </div>
    </section>
  );
}

/* ── What is PreScale — seamless 2x2, invert title on hover ───────── */
const FEATURES: [string, string][] = [
  ["Ramps real traffic", "Closed-loop virtual users over HTTP/2 — no external load tool, no server to stand up."],
  ["Finds the first break", "Pinpoints which route fails first, and the exact concurrency where it starts to give."],
  ["Diagnoses the cause", "Active probes classify the bottleneck — connection pool, concurrency ceiling, slow query — and name the fix."],
  ["Local-first & honest", "Runs on your machine; your data never leaves it. Deterministic — no LLM in the core. Apache-2.0."],
];

function WhatIs() {
  return (
    <Reveal className="py-24 md:py-32">
      <div className="px-8 sm:px-10">
        <div className="text-[0.72rem] uppercase tracking-[0.09em] text-faint">§ What is PreScale</div>
        <h2 className="mt-6 max-w-2xl text-[1.5rem] font-medium leading-tight">
          A load test that reads like a verdict, not a dashboard.
        </h2>
      </div>
      <div className="mt-14 grid grid-cols-1 sm:grid-cols-2">
        {FEATURES.map(([t, d], i) => {
          const border =
            i === 0 ? "border-b border-line sm:border-r"
            : i === 1 ? "border-b border-line"
            : i === 2 ? "border-b border-line sm:border-b-0 sm:border-r"
            : "";
          return (
            <div key={t} className={`group p-8 sm:p-10 ${border}`}>
              <span className="inline-block px-1 font-medium text-cream transition-colors group-hover:bg-cream group-hover:text-night">
                {t}
              </span>
              <p className="mt-4 max-w-md text-[0.85rem] leading-relaxed text-dim">{d}</p>
            </div>
          );
        })}
      </div>
    </Reveal>
  );
}

/* ── Figures — 3-column autopsy, SVGs draw & loop forever ────────── */
const DRAW = 2.6;                     // seconds to draw one element (slower)
const TIMES = [0, 0.32, 0.84, 1];     // draw in · hold · fade out · reset (while invisible)
const GAP = 1.8;                      // pause before the cycle restarts
const loop = (delay: number) => ({
  duration: DRAW,
  times: TIMES,
  ease: "easeInOut" as const,
  repeat: Infinity,
  repeatDelay: GAP,
  delay,
});
// keyframes: appear, hold, disappear — the 1→0 reset happens while opacity is 0
const kDraw = { pathLength: [0, 1, 1, 0], opacity: [0, 1, 1, 0] };
const kBar = { scaleX: [0, 1, 1, 0], opacity: [0, 1, 1, 0] };
const kPop = { scale: [0, 1, 1, 0], opacity: [0, 1, 1, 0] };
const kFade = { opacity: [0, 1, 1, 0] };
const hidDraw = { pathLength: 0, opacity: 0 };
const hidBar = { scaleX: 0, opacity: 0 };
const hidPop = { scale: 0, opacity: 0 };
const hidFade = { opacity: 0 };

function Figures() {
  return (
    <Reveal className="py-24 md:py-32">
      <div className="px-8 sm:px-10">
        <div className="text-[0.72rem] uppercase tracking-[0.09em] text-faint">§ Figures</div>
        <h2 className="mt-6 max-w-2xl text-[1.5rem] font-medium leading-tight">
          Every run is a small experiment. PreScale reports it like one.
        </h2>
      </div>
      <div className="mt-14 grid grid-cols-1 md:grid-cols-3">
        {/* Fig 1 — verdict leads: marker + label, then the guide, then the curve builds */}
        <figure className="border-b border-line p-8 sm:p-10 md:border-b-0 md:border-r">
          <div className="grid-bg border border-line p-4">
            <svg viewBox="0 0 300 150" className="w-full" fill="none">
              <motion.circle cx="224" cy="44" r="2.6" fill="var(--color-accent)" initial={hidPop} animate={kPop} transition={loop(0)} />
              <motion.text x="150" y="20" fill="var(--color-accent)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0)}>breaking point</motion.text>
              <motion.line x1="224" y1="6" x2="224" y2="140" stroke="var(--color-accent)" strokeWidth="1" strokeDasharray="3 3" initial={hidDraw} animate={kDraw} transition={loop(0.34)} />
              <motion.polyline points="10,120 60,116 110,108 160,92 200,70 224,44" stroke="var(--color-dim)" strokeWidth="1.5" initial={hidDraw} animate={kDraw} transition={loop(0.68)} />
              <motion.polyline points="224,44 250,26 275,14 292,9" stroke="var(--color-accent)" strokeWidth="2" initial={hidDraw} animate={kDraw} transition={loop(1.02)} />
              <motion.text x="150" y="140" fill="var(--color-faint)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(1.36)}>concurrent users →</motion.text>
            </svg>
          </div>
          <figcaption className="mt-5 text-[0.72rem] leading-relaxed text-dim">
            <span className="text-faint">Fig 1.</span> Latency (p95) vs. users — holds, then snaps.
          </figcaption>
        </figure>
        {/* Fig 2 — culprit leads: /checkout first, then the rest fill in bottom-up */}
        <figure className="border-b border-line p-8 sm:p-10 md:border-b-0 md:border-r">
          <div className="grid-bg border border-line p-4">
            <svg viewBox="0 0 300 150" className="w-full" fill="none">
              <motion.rect x="70" y="112" width="118" height="14" fill="var(--color-accent)" style={{ transformOrigin: "left center" }} initial={hidBar} animate={kBar} transition={loop(0)} />
              <motion.text x="8" y="122" fill="var(--color-accent)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0)}>/checkout</motion.text>
              <motion.rect x="70" y="88" width="168" height="14" fill="var(--color-line-strong)" style={{ transformOrigin: "left center" }} initial={hidBar} animate={kBar} transition={loop(0.3)} />
              <motion.text x="8" y="98" fill="var(--color-dim)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0.3)}>/cart</motion.text>
              <motion.rect x="70" y="64" width="205" height="14" fill="var(--color-line-strong)" style={{ transformOrigin: "left center" }} initial={hidBar} animate={kBar} transition={loop(0.6)} />
              <motion.text x="8" y="74" fill="var(--color-dim)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0.6)}>/product</motion.text>
              <motion.rect x="70" y="40" width="215" height="14" fill="var(--color-line-strong)" style={{ transformOrigin: "left center" }} initial={hidBar} animate={kBar} transition={loop(0.9)} />
              <motion.text x="8" y="50" fill="var(--color-dim)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0.9)}>/search</motion.text>
              <motion.rect x="70" y="16" width="215" height="14" fill="var(--color-line-strong)" style={{ transformOrigin: "left center" }} initial={hidBar} animate={kBar} transition={loop(1.2)} />
              <motion.text x="8" y="26" fill="var(--color-dim)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(1.2)}>/</motion.text>
            </svg>
          </div>
          <figcaption className="mt-5 text-[0.72rem] leading-relaxed text-dim">
            <span className="text-faint">Fig 2.</span> First route to fail — /checkout caps first.
          </figcaption>
        </figure>
        {/* Fig 3 — envelope, then guide, then climb → collapse, marker last */}
        <figure className="p-8 sm:p-10">
          <div className="grid-bg border border-line p-4">
            <svg viewBox="0 0 300 150" className="w-full" fill="none">
              <motion.path d="M10,140 L10,96 60,74 110,52 160,38 200,34 L250,78 292,116 292,140 Z" fill="var(--color-line)" initial={hidFade} animate={kFade} transition={loop(0)} />
              <motion.line x1="200" y1="10" x2="200" y2="140" stroke="var(--color-accent)" strokeWidth="1" strokeDasharray="3 3" initial={hidDraw} animate={kDraw} transition={loop(0.34)} />
              <motion.text x="150" y="24" fill="var(--color-accent)" fontSize="9" initial={hidFade} animate={kFade} transition={loop(0.34)}>ceiling</motion.text>
              <motion.polyline points="10,96 60,74 110,52 160,38 200,34" stroke="var(--color-dim)" strokeWidth="1.5" initial={hidDraw} animate={kDraw} transition={loop(0.68)} />
              <motion.polyline points="200,34 250,78 292,116" stroke="var(--color-accent)" strokeWidth="2" initial={hidDraw} animate={kDraw} transition={loop(1.02)} />
              <motion.circle cx="200" cy="34" r="2.6" fill="var(--color-accent)" initial={hidPop} animate={kPop} transition={loop(1.36)} />
            </svg>
          </div>
          <figcaption className="mt-5 text-[0.72rem] leading-relaxed text-dim">
            <span className="text-faint">Fig 3.</span> Throughput ceiling — climbs, then collapses.
          </figcaption>
        </figure>
      </div>
    </Reveal>
  );
}

/* ── Compare — PreScale vs the load engines ──────────────────────── */
const COMPARE: { dim: string; ps: string; locust: string; k6: string }[] = [
  { dim: "Setup", ps: "Point it at a URL", locust: "Write a locustfile", k6: "Write a JS script" },
  { dim: "Scripting", ps: "None", locust: "Python", k6: "JavaScript" },
  { dim: "Finds the first route to break", ps: "Automatic", locust: "You design it", k6: "You design it" },
  { dim: "Explains the cause", ps: "Names the bottleneck + fix", locust: "—", k6: "—" },
  { dim: "Reads like", ps: "A plain-English verdict", locust: "A live dashboard", k6: "Metrics & thresholds" },
  { dim: "CI gate", ps: "--fail-under", locust: "Custom", k6: "Thresholds" },
  { dim: "Best for", ps: "Pre-launch readiness", locust: "Custom user flows", k6: "Scripted perf tests" },
];

function Compare() {
  return (
    <Reveal id="compare" className="py-24 md:py-32">
      <div className="space-y-6 px-8 sm:px-10">
        <div className="text-[0.72rem] uppercase tracking-[0.09em] text-faint">§ How it compares</div>
        <h2 className="max-w-2xl text-[1.5rem] font-medium leading-tight">
          Locust and k6 are load engines you script. PreScale is the pre-launch verdict.
        </h2>
        <p className="max-w-2xl text-[0.85rem] leading-relaxed text-dim">
          Different jobs. Reach for Locust or k6 when you need to model a bespoke user journey.
          Reach for PreScale when you just need to know what breaks first — and why — before you ship.
        </p>
      </div>
      <div className="mt-14 grid grid-cols-[1.2fr_1fr_1fr_1fr] border-t border-line text-[0.8rem]">
        {/* header */}
        <div className="border-b border-r border-line p-5" />
        <div className="border-b border-r border-line bg-cream/5 p-5 font-medium text-accent">PreScale</div>
        <div className="border-b border-r border-line p-5 font-medium text-cream">Locust</div>
        <div className="border-b border-line p-5 font-medium text-cream">k6</div>
        {/* rows */}
        {COMPARE.map((r) => (
          <Fragment key={r.dim}>
            <div className="border-b border-r border-line p-5 text-dim">{r.dim}</div>
            <div className="border-b border-r border-line bg-cream/5 p-5 text-cream">{r.ps}</div>
            <div className="border-b border-r border-line p-5 text-dim">{r.locust}</div>
            <div className="border-b border-line p-5 text-dim">{r.k6}</div>
          </Fragment>
        ))}
      </div>
      <p className="max-w-2xl px-8 pt-8 text-[0.72rem] leading-relaxed text-faint sm:px-10">
        Also in the space: Artillery, JMeter, hey, wrk — general-purpose load generators you point and script.
      </p>
    </Reveal>
  );
}

/* ── Landing page ────────────────────────────────────────────────── */
function Landing() {
  return (
    <div className="mx-auto max-w-5xl border-x border-line">
      <Nav />
      <Hero />
      <WhatIs />
      <Figures />
      <Compare />
      <Footer />
    </div>
  );
}

/* ── Hash router — treats "#/…" as a route, plain "#anchor" as scroll ── */
function currentRoute() {
  const h = window.location.hash;
  return h.startsWith("#/") ? h.slice(1) : "/";
}

export default function App() {
  const [route, setRoute] = useState(currentRoute);

  useEffect(() => {
    const onHash = () => setRoute(currentRoute());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    if (route === "/docs") window.scrollTo(0, 0);
  }, [route]);

  return (
    <div className="bg-night pb-24 text-cream md:pb-32">
      {route === "/docs" ? <Docs /> : <Landing />}
    </div>
  );
}
