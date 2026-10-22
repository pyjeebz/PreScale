import type { ReactNode } from "react";
import { Ctas, InstallBox, LINKS, Reveal } from "./components/chrome";
import { CodeBlock, Surface, cn } from "./components/ui";
import { MiniBar } from "./components/mini-bar";
import { FeatureList } from "./components/feature-list";
import { HeroBars } from "./components/hero-bars";
import { DashboardDemo } from "./demo/demo";

const container = "mx-auto w-full max-w-[1200px] px-4 sm:px-8";

/** Two-tone, like the hero: the claim in white, the rest in grey. */
function Heading({ title, dim, className }: { title: ReactNode; dim?: ReactNode; className?: string }) {
  return (
    <h2 className={cn("font-medium leading-[1.05] tracking-[-0.035em] text-balance", className)}>
      {title}
      {dim && <span className="font-normal text-muted-foreground"> {dim}</span>}
    </h2>
  );
}

function SectionHead({ title, dim, lede, center = false }: { title: ReactNode; dim?: ReactNode; lede?: ReactNode; center?: boolean }) {
  return (
    <div className={cn(center && "mx-auto text-center")}>
      <Heading title={title} dim={dim} className={cn("text-[clamp(30px,4.4vw,52px)]", center && "mx-auto max-w-[820px]")} />
      {lede && (
        <p className={cn("mt-5 max-w-[560px] text-base leading-relaxed text-pretty text-muted-foreground sm:text-[17px]", center && "mx-auto")}>{lede}</p>
      )}
    </div>
  );
}

/* ── Hero ──────────────────────────────────────────────────────────── */

export function Hero() {
  return (
    <section id="top" className="relative flex min-h-svh min-h-[640px] items-center overflow-hidden pt-16">
      <HeroBars />
      <div className={cn(container, "relative flex flex-col items-center py-20 text-center")}>
        <h1 className="max-w-[1000px] text-[clamp(40px,7.4vw,84px)] leading-[1.02] tracking-[-0.035em] text-balance">
          <span className="block font-medium text-foreground">Capacity checks that</span>
          <span className="block font-normal text-muted-foreground">run themselves.</span>
        </h1>
        <p className="mt-7 max-w-[700px] text-lg text-pretty text-muted-foreground sm:text-xl">One command load-tests every deploy and tells you why it breaks.</p>
        <div id="install" className="mt-9 flex w-full scroll-mt-24 flex-col items-center gap-4">
          <InstallBox />
          <Ctas />
        </div>
        <p className="mt-6 text-xs tracking-wide text-muted-foreground">Open source · macOS · Linux · Windows · GitHub Action</p>
      </div>
    </section>
  );
}

/* ── The dashboard, embedded ───────────────────────────────────────── */

export function Product() {
  return (
    <Reveal id="product" className="py-16 sm:py-24">
      <div className={container}>
        <SectionHead
          center
          title="Every deploy,"
          dim="measured."
          lede="Each site gets a capacity timeline: how many users every deploy survives, the commit where it dropped, and why. Take the cursor and click around."
        />
        <div className="mt-12">
          <DashboardDemo />
        </div>
        <p className="mt-4 text-center text-xs text-muted-foreground">Interactive demo with sample data.</p>
      </div>
    </Reveal>
  );
}

/* ── Feature rows with a cursor-following live preview ───────────── */

export function Features() {
  return (
    <Reveal id="features" className="py-16 sm:py-24">
      <div className={container}>
        <div className="mb-12">
          <Heading title="From one command" dim="to every pull request" className="max-w-[640px] text-[clamp(30px,4.4vw,52px)]" />
          <p className="mt-5 max-w-[520px] text-[15px] leading-relaxed text-pretty text-muted-foreground">
            Start in your terminal or hand it to your coding agent. Add the dashboard and CI when you want them.
          </p>
        </div>
        <FeatureList />
      </div>
    </Reveal>
  );
}

/* ── Privacy ───────────────────────────────────────────────────────── */

export function Privacy() {
  const never = ["Request and response bodies", "Cookies", "Header values you pass with -H", "Environment variables", "Your code"];
  return (
    <Reveal className="py-16 sm:py-24">
      <div className={cn(container, "grid gap-10 lg:grid-cols-2 lg:gap-16")}>
        <div>
          <Heading title="Runs on your machine." dim="Private by default." className="text-[clamp(26px,3vw,38px)] leading-[1.1]" />
          <p className="mt-4 max-w-xl text-base leading-relaxed text-muted-foreground">
            The CLI is open source and works fully offline. Nothing leaves your machine unless you upload a run, and you can see exactly what would be
            sent before you do. Runs stay private to you until you share one.
          </p>
          <a href={LINKS.data} className="mt-4 inline-block text-sm text-accent hover:underline">
            What gets uploaded
          </a>
        </div>
        <div className="flex min-w-0 flex-col gap-4">
          <CodeBlock className="whitespace-pre-wrap">
            <span className="text-muted-foreground">$ </span>prescale upload --dry-run
            {"\n"}
            <span className="text-muted-foreground">
              {'{\n  "schema_version": 1,\n  "kind": "run",\n  "verdict": { "survives_users": 100, … },\n  …\n}\n'}
            </span>
            Dry run: this is the full payload for 20261016T224558Z-8e5714. Nothing was sent.
          </CodeBlock>
          <Surface title="Never leaves your machine">
            <ul>
              {never.map((item) => (
                <li key={item} className="flex items-center gap-2.5 border-b border-muted/70 px-4 py-2.5 text-[13px] last:border-b-0">
                  <span className="h-[5px] w-[5px] rounded-full bg-border-strong" />
                  {item}
                </li>
              ))}
            </ul>
          </Surface>
        </div>
      </div>
    </Reveal>
  );
}

/* ── Compare ───────────────────────────────────────────────────────── */

const COMPARE: Array<[string, string, string, string]> = [
  ["Setup", "Point it at a URL", "Write a JS script", "Write a locustfile"],
  ["Finds the first route to break", "Automatic", "You design it", "You design it"],
  ["Explains the cause", "Names the bottleneck and the fix", "No", "No"],
  ["Launch readiness", "GO / NO-GO for a named launch", "No", "No"],
  ["Reads like", "A plain-English verdict", "Metrics and thresholds", "A live dashboard"],
];

export function Compare() {
  return (
    <Reveal className="py-16 sm:py-24">
      <div className={container}>
        <SectionHead title="Not another load generator." dim="An answer, not a graph." lede="k6 and Locust are great at generating load you script. PreScale answers the question you had in the first place." />
        <div className="mt-10 overflow-x-auto rounded-[10px] border border-border">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead>
              <tr className="border-b border-border text-xs text-muted-foreground">
                <th className="px-4 py-3 font-[450]" />
                <th className="bg-[#3FD3DE]/[0.06] px-4 py-3 font-medium text-foreground">
                  <span className="flex items-center gap-2">
                    <MiniBar color="#3FD3DE" />
                    PreScale
                  </span>
                </th>
                <th className="px-4 py-3 font-[450]">k6</th>
                <th className="px-4 py-3 font-[450]">Locust</th>
              </tr>
            </thead>
            <tbody>
              {COMPARE.map(([dimension, ours, k6, locust]) => (
                <tr key={dimension} className="border-b border-muted/70 last:border-b-0">
                  <td className="px-4 py-3 text-muted-foreground">{dimension}</td>
                  <td className="bg-[#3FD3DE]/[0.06] px-4 py-3">{ours}</td>
                  <td className="px-4 py-3 text-muted-foreground">{k6}</td>
                  <td className="px-4 py-3 text-muted-foreground">{locust}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Reveal>
  );
}

/* ── FAQ ───────────────────────────────────────────────────────────── */

const FAQ: Array<[string, ReactNode]> = [
  [
    "What does PreScale measure?",
    "How many concurrent users your app survives before errors climb or response times cross the latency wall, with a confidence band around the number, and the requests per second that means. Virtual users don't pause between clicks the way people do, so PreScale also gives a rough real-visitor equivalent. It names the route that breaks first and, with investigate, why.",
  ],
  [
    "Do I need to write test scripts?",
    <>No. Point it at a URL. Add routes with <code className="font-mono text-[13px]">--path</code> and headers for logged-in or protected pages with <code className="font-mono text-[13px]">-H</code>.</>,
  ],
  [
    "Is it safe to run against production?",
    "Test staging or a preview when you can. PreScale asks you to confirm you own the site before it ramps load, the GitHub Action skips production deploys unless you allow them, and CI checks ramp gently (100 users) by default. Previews often share production's database, so the load reaches it too.",
  ],
  [
    "What leaves my machine?",
    <>Nothing, unless you upload a run. An upload is the saved run file: the verdict, timings, diagnosis, the URL and the git commit. Never bodies, cookies, header values or your code. <a href={LINKS.data} className="text-accent hover:underline">Details</a>.</>,
  ],
  [
    "Can I load-test a site on Vercel, Netlify or Cloudflare?",
    "Only with your host's permission. Vercel permits load testing on Enterprise plans with prior notice, and Netlify and Cloudflare need it arranged. PreScale recognises these hosts and asks before sending any load, and the GitHub Action skips their deploys unless you confirm. Without it, let PreScale build and test your app itself, on your machine or in CI, with no host involved.",
  ],
  [
    "What if my laptop is the bottleneck?",
    "PreScale watches its own machine while it measures. If it falls behind, the result says from which level the numbers may understate your app, so it never blames your app for its own limits.",
  ],
  ["Which platforms does it support?", "macOS, Linux and Windows for the CLI, GitHub Actions for pull requests, and any other CI with prescale ci."],
];

export function Faq() {
  return (
    <Reveal className="py-16 sm:py-24">
      <div className={cn(container, "grid gap-10 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:gap-16")}>
        <SectionHead title="Questions," dim="answered." lede={<>Something else? <a href={`${LINKS.repo}/issues`} className="text-accent hover:underline">Open an issue</a>. We read every one.</>} />
        <div className="min-w-0 border-t border-border">
          {FAQ.map(([question, answer]) => (
            <details key={question} className="group border-b border-border">
              <summary className="flex cursor-pointer list-none items-center justify-between gap-6 py-5 text-[17px] font-medium tracking-[-0.01em] [&::-webkit-details-marker]:hidden">
                {question}
                <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 text-muted-foreground transition-transform duration-200 group-open:rotate-45" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden>
                  <line x1="12" y1="5" x2="12" y2="19" />
                  <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
              </summary>
              <p className="max-w-2xl pb-6 pr-10 text-[15px] leading-relaxed text-muted-foreground">{answer}</p>
            </details>
          ))}
        </div>
      </div>
    </Reveal>
  );
}

/* ── Closing call to action ────────────────────────────────────────── */

export function FinalCta() {
  return (
    <Reveal className="relative flex min-h-[calc(100svh-56px)] min-h-[600px] items-center overflow-hidden py-24">
      <HeroBars mirror offset={7} />
      <div className={cn(container, "relative flex flex-col items-center text-center")}>
        <Heading title="Know your number" dim="before launch day." className="max-w-[820px] text-[clamp(32px,5vw,60px)] tracking-[-0.04em]" />
        <p className="mt-6 max-w-md text-base leading-relaxed text-muted-foreground sm:text-[17px]">One command to install. Your first verdict in about a minute.</p>
        <div className="mt-9 flex w-full flex-col items-center gap-4">
          <InstallBox />
          <Ctas />
        </div>
      </div>
    </Reveal>
  );
}
