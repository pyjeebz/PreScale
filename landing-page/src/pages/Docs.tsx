import { type ReactNode, type MouseEvent } from "react";
import { Nav } from "../chrome";

/* smooth in-page scroll without touching the hash (the router owns "#/…") */
const jump = (id: string) => (e: MouseEvent) => {
  e.preventDefault();
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
};

const TOC: [string, string][] = [
  ["installation", "Installation"],
  ["quickstart", "Quickstart"],
  ["investigate", "investigate"],
  ["run", "run"],
  ["options", "Options"],
  ["ci", "CI gate"],
  ["safety", "Safety"],
];

/* ── small building blocks ───────────────────────────────────────── */
function Term({ children }: { children: ReactNode }) {
  return (
    <div className="my-5 overflow-x-auto border border-line bg-night-raised px-4 py-3 text-[0.85rem] leading-relaxed">
      {children}
    </div>
  );
}
function Cmd({ children }: { children: ReactNode }) {
  return (
    <div>
      <span className="select-none text-faint">$ </span>
      <span className="text-cream">{children}</span>
    </div>
  );
}
function Out({ children, accent = false }: { children: ReactNode; accent?: boolean }) {
  return <div className={accent ? "text-accent" : "text-dim"}>{children}</div>;
}
function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <section id={id} className="scroll-mt-20 border-b border-line px-8 py-14 last:border-b-0 sm:px-10">
      <h2 className="text-[1.4rem] font-medium leading-tight">{title}</h2>
      <div className="mt-6 space-y-4 text-[0.9rem] leading-relaxed text-dim">{children}</div>
    </section>
  );
}

const OPTIONS: [string, string, string][] = [
  ["--path <route>", "repeatable", "Extra route to test, relative to the URL. Pass it multiple times."],
  ["-u, --max-users", "200", "Peak virtual users to ramp toward."],
  ["-s, --stage-seconds", "5.0", "Seconds to hold each load level."],
  ["--max-rps", "—", "Cap aggregate requests/sec across the whole ramp."],
  ["--i-own-this", "off", "Skip the confirmation prompt for non-local targets."],
  ["--fail-under <N>", "—", "Exit non-zero if it survives fewer than N users (a CI gate)."],
  ["--json", "off", "Emit the full result as JSON instead of the terminal report."],
  ["--store <dir>", "./.prescale", "Directory for saved runs."],
];

export function Docs() {
  return (
    <div className="mx-auto max-w-5xl border-x border-b border-line">
      <Nav />

      {/* header */}
      <section className="border-b border-line px-8 pt-20 pb-12 sm:px-10">
        <div className="text-[0.72rem] uppercase tracking-[0.09em] text-faint">§ Documentation</div>
        <h1 className="mt-6 text-[clamp(2rem,5vw,3rem)] font-medium leading-[1.05] tracking-[-0.03em]">
          Docs
        </h1>
        <p className="mt-6 max-w-2xl text-[0.95rem] leading-relaxed text-dim">
          Everything you need to point PreScale at a URL and read the verdict — install it, run
          your first investigation, and wire it into CI.
        </p>
      </section>

      {/* body: sticky TOC + content */}
      <div className="grid md:grid-cols-[220px_1fr]">
        <aside className="hidden border-r border-line md:block">
          <nav className="sticky top-16 flex flex-col gap-1 p-6 text-[0.82rem]">
            <div className="mb-2 text-[0.72rem] uppercase tracking-[0.09em] text-faint">On this page</div>
            {TOC.map(([id, label]) => (
              <a
                key={id}
                href={`#${id}`}
                onClick={jump(id)}
                className="py-1 text-dim transition-colors hover:text-cream"
              >
                {label}
              </a>
            ))}
          </nav>
        </aside>

        <div className="min-w-0">
          <Section id="installation" title="Installation">
            <p>PreScale is a Python CLI. It needs Python 3.10 or newer.</p>
            <Term>
              <Cmd>pip install prescale</Cmd>
            </Term>
            <p>
              <span className="text-cream">pipx</span> and <span className="text-cream">uv</span> work
              too if you prefer an isolated tool install — <span className="text-cream">brew</span>,{" "}
              <span className="text-cream">npm</span>, and a <span className="text-cream">curl</span>{" "}
              installer are on the way.
            </p>
          </Section>

          <Section id="quickstart" title="Quickstart">
            <p>
              Point it at a URL you own. PreScale ramps virtual users, finds which route breaks
              first, and tells you — in plain English — when and why it falls over.
            </p>
            <Term>
              <Cmd>prescale investigate http://localhost:8000 --path /checkout</Cmd>
              <div className="mt-3" />
              <Out>→ ramping virtual users .......... 20 → 200</Out>
              <Out>→ diagnosing the culprit route ... done</Out>
              <div className="mt-2" />
              <Out accent>✗ /checkout breaks at ~100 users — 5xx under load (connection_pool).</Out>
              <div className="text-cream">✓ fix: raise the DB/upstream pool size, or add pgbouncer.</div>
            </Term>
            <p>
              Everything runs on your machine and the results are saved locally — your data never
              leaves your box.
            </p>
          </Section>

          <Section id="investigate" title="prescale investigate">
            <p>
              The headline command. It ramps load to find the first breaking point, then fires a
              few active probes to classify the bottleneck and name a fix — deterministically, with
              no LLM in the loop.
            </p>
            <Term>
              <Cmd>prescale investigate https://staging.myapp.com --i-own-this</Cmd>
            </Term>
            <p>
              Add <span className="text-cream">--path</span> for each extra route you care about.
              Run it with no URL to re-investigate the target of your latest saved run.
            </p>
            <Term>
              <Cmd>prescale investigate http://localhost:8000 --path /search --path /checkout</Cmd>
            </Term>
          </Section>

          <Section id="run" title="prescale run">
            <p>
              A straight load test with a live ramp table — watch users, throughput, latency
              percentiles, and error rate climb in real time, without the diagnosis step.
            </p>
            <Term>
              <Cmd>prescale run http://localhost:8000 -u 500 -s 3</Cmd>
            </Term>
          </Section>

          <Section id="options" title="Options">
            <p>These flags apply to both investigate and run.</p>
            <div className="mt-2 grid grid-cols-[1.3fr_0.6fr_2fr] border border-line text-[0.8rem]">
              <div className="border-b border-r border-line p-3 font-medium text-cream">Flag</div>
              <div className="border-b border-r border-line p-3 font-medium text-cream">Default</div>
              <div className="border-b border-line p-3 font-medium text-cream">What it does</div>
              {OPTIONS.map(([flag, def, desc]) => (
                <div key={flag} className="contents">
                  <div className="border-b border-r border-line p-3 text-cream">{flag}</div>
                  <div className="border-b border-r border-line p-3 text-faint">{def}</div>
                  <div className="border-b border-line p-3 text-dim">{desc}</div>
                </div>
              ))}
            </div>
          </Section>

          <Section id="ci" title="CI gate">
            <p>
              Use <span className="text-cream">--fail-under</span> to fail a build when the app
              can't survive a target concurrency. It exits non-zero, so it drops straight into any
              pipeline.
            </p>
            <Term>
              <Cmd>prescale investigate https://staging.myapp.com --i-own-this --fail-under 300</Cmd>
              <div className="mt-2" />
              <Out accent>✗ fail-under: survives ~180 &lt; 300</Out>
            </Term>
          </Section>

          <Section id="safety" title="Safety">
            <p>PreScale sends real traffic, so it's built to be safe by default:</p>
            <ul className="ml-4 list-disc space-y-2 marker:text-faint">
              <li>It only hits the host you point it at.</li>
              <li>
                It refuses non-local targets until you confirm — or pass{" "}
                <span className="text-cream">--i-own-this</span>. Point it at staging or a preview
                URL, never production you don't control.
              </li>
              <li>
                Cap the intensity with <span className="text-cream">--max-rps</span> so you never
                hammer a shared host.
              </li>
              <li>Runs locally and stores results locally. Nothing is sent anywhere.</li>
            </ul>
          </Section>
        </div>
      </div>
    </div>
  );
}
