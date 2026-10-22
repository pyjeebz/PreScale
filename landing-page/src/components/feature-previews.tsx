import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { cn } from "./ui";

/*
 * Live mockups for the feature list's floating preview. Each one mounts when
 * its row is hovered and loops until the visitor moves on. No video: these
 * are the product's own screens, animated.
 */

/** Ticks up every `ms`. Keying a child on it restarts that child's animations. */
function useLoop(ms: number) {
  const [run, setRun] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setRun((value) => value + 1), ms);
    return () => window.clearInterval(timer);
  }, [ms]);
  return run;
}

/** Types `text` out one character at a time. */
function useTyped(text: string, speed: number, delay = 0) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let timer: number | undefined;
    const start = window.setTimeout(() => {
      timer = window.setInterval(() => {
        setCount((value) => {
          if (value >= text.length) {
            window.clearInterval(timer);
            return value;
          }
          return value + 1;
        });
      }, speed);
    }, delay);
    return () => {
      window.clearTimeout(start);
      window.clearInterval(timer);
    };
  }, [text, speed, delay]);
  return text.slice(0, count);
}

/** Becomes true after `delay` ms. */
function useAfter(delay: number) {
  const [done, setDone] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setDone(true), delay);
    return () => window.clearTimeout(timer);
  }, [delay]);
  return done;
}

const fadeUp = (delay: number) => ({
  initial: { opacity: 0, y: 4 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3, delay, ease: [0.23, 1, 0.32, 1] as const },
});

const Caret = () => <span className="caret ml-px inline-block h-[11px] w-[6px] translate-y-[2px] bg-foreground" />;

function Spinner({ className }: { className?: string }) {
  return (
    <motion.span
      className={cn("inline-block h-2.5 w-2.5 rounded-full border border-muted-foreground border-t-transparent", className)}
      animate={{ rotate: 360 }}
      transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
    />
  );
}

/* ── 01 · One command, a real answer ──────────────────────────────── */

const COMMAND = "prescale run https://staging.acme.dev";
const RAMP: Array<[string, string, string, string, boolean]> = [
  ["20", "284", "135ms", "0%", false],
  ["50", "331", "231ms", "2%", false],
  ["100", "291", "671ms", "7%", true],
];

function TerminalRun() {
  const typed = useTyped(COMMAND, 26);
  const typing = typed.length < COMMAND.length;
  const start = COMMAND.length * 0.026 + 0.2;
  return (
    <div className="font-mono text-[10.5px] leading-[17px]">
      <div>
        <span className="text-muted-foreground">$ </span>
        {typed}
        {typing && <Caret />}
      </div>
      <motion.div {...fadeUp(start)} className="mt-2 whitespace-pre text-muted-foreground">
        {"  Users  Req/s    p95  Errors"}
      </motion.div>
      {RAMP.map(([users, rps, p95, errors, bad], index) => (
        <motion.div key={users} {...fadeUp(start + 0.25 + index * 0.3)} className={cn("whitespace-pre", bad && "text-danger-foreground")}>
          {`  ${users.padStart(5)}  ${rps.padStart(5)}  ${p95.padStart(5)}  ${errors.padStart(6)}`}
        </motion.div>
      ))}
      <motion.div {...fadeUp(start + 1.4)} className="mt-2 text-warning-foreground">
        {"  ⚠ Survives ~50 (30–75) concurrent users"}
      </motion.div>
      <motion.div {...fadeUp(start + 1.7)} className="whitespace-pre">
        {"  First failure  "}
        <span className="text-foreground">/checkout</span>
        <span className="text-muted-foreground"> at ~75 users</span>
      </motion.div>
    </div>
  );
}

export function TerminalPreview() {
  const run = useLoop(5600);
  return <TerminalRun key={run} />;
}

/* ── 02 · It tells you why ────────────────────────────────────────── */

const ROUTES: Array<[string, number, string]> = [
  ["/api/search", 100, "1.24s"],
  ["/checkout", 33, "410ms"],
  ["/products", 15, "182ms"],
  ["/", 8, "96ms"],
];

function DiagnosisRun() {
  return (
    <div className="flex h-full flex-col">
      <p className="text-[10.5px] text-muted-foreground">p95 per route at 120 users</p>
      <div className="mt-2 flex flex-col gap-2">
        {ROUTES.map(([path, width, p95], index) => {
          const culprit = index === 0;
          return (
            <div key={path} className="flex items-center gap-2.5">
              <motion.span
                className="w-[74px] shrink-0 truncate font-mono text-[10.5px]"
                initial={{ color: "#ededed" }}
                animate={{ color: culprit ? "#f87171" : "#ededed" }}
                transition={{ delay: 1.1, duration: 0.3 }}
              >
                {path}
              </motion.span>
              <span className="h-[3px] flex-1 overflow-hidden rounded-full bg-muted">
                <motion.span
                  className="block h-full origin-left rounded-full"
                  style={{ width: `${width}%` }}
                  initial={{ scaleX: 0, backgroundColor: "#444444" }}
                  animate={{ scaleX: 1, backgroundColor: culprit ? "#ff4500" : "#444444" }}
                  transition={{
                    scaleX: { duration: 0.7, delay: 0.15 + index * 0.1, ease: [0.23, 1, 0.32, 1] },
                    backgroundColor: { delay: 1.1, duration: 0.3 },
                  }}
                />
              </span>
              <span className="w-10 shrink-0 text-right font-mono text-[10px] text-muted-foreground">{p95}</span>
            </div>
          );
        })}
      </div>
      <motion.div {...fadeUp(1.5)} className="mt-3 flex items-center gap-2 rounded-[7px] border border-border bg-muted/50 px-2.5 py-1.5">
        <span className="font-mono text-[10.5px]">connection_pool</span>
        <span className="text-[10px] text-success-foreground">high confidence</span>
      </motion.div>
      <motion.p {...fadeUp(1.9)} className="mt-2 text-[10.5px]">
        <span className="text-muted-foreground">→ </span>Increase the DB connection-pool size.
      </motion.p>
    </div>
  );
}

export function DiagnosisPreview() {
  const run = useLoop(4800);
  return <DiagnosisRun key={run} />;
}

/* ── 03 · Capacity on every pull request ──────────────────────────── */

function PrCommentRun() {
  const measured = useAfter(1300);
  return (
    <div className="text-[10.5px] leading-[16px]">
      <div className="flex items-center gap-1.5 text-muted-foreground">
        <span className="flex h-4 w-4 items-center justify-center rounded-full bg-foreground">
          <span className="h-1.5 w-1.5 rounded-[1.5px] bg-background" />
        </span>
        <span className="font-medium text-foreground">prescale</span> commented on #42
      </div>
      <div className="mt-2.5 h-5">
        <AnimatePresence mode="wait" initial={false}>
          {measured ? (
            <motion.p key="result" {...fadeUp(0)} className="flex items-center gap-2 text-[12px] font-semibold">
              <span className="relative flex h-2 w-2 items-center justify-center">
                <motion.span
                  className="absolute h-2 w-2 rounded-full border border-danger"
                  initial={{ scale: 1, opacity: 0.9 }}
                  animate={{ scale: 3, opacity: 0 }}
                  transition={{ duration: 0.9, ease: "easeOut" }}
                />
                <span className="h-2 w-2 rounded-full bg-danger" />
              </span>
              Capacity regressed: 150 → 100 users (−33%)
            </motion.p>
          ) : (
            <motion.p key="measuring" exit={{ opacity: 0 }} className="flex items-center gap-2 text-muted-foreground">
              <Spinner /> Measuring the preview deploy…
            </motion.p>
          )}
        </AnimatePresence>
      </div>
      {measured && (
        <>
          <motion.p {...fadeUp(0.35)} className="mt-1.5 font-mono text-[10px] text-muted-foreground">
            pr-482.staging.acme.dev vs main @ 71aa0c9
          </motion.p>
          <motion.p {...fadeUp(0.65)} className="mt-2">
            <span className="font-semibold">Breaks first:</span> <span className="font-mono">/api/search</span> at ~120 users
          </motion.p>
          <motion.p {...fadeUp(0.9)}>
            <span className="font-semibold">Why:</span> <span className="font-mono">connection_pool</span> (high confidence)
          </motion.p>
          <motion.p {...fadeUp(1.15)}>
            <span className="font-semibold">Fix:</span> raise the pool size, or add pgbouncer.
          </motion.p>
          <motion.p {...fadeUp(1.4)} className="mt-2 text-accent">
            Open the run · Capacity timeline
          </motion.p>
        </>
      )}
    </div>
  );
}

export function PrCommentPreview() {
  const run = useLoop(5200);
  return <PrCommentRun key={run} />;
}

/* ── 04 · GO or NO-GO for your launch ─────────────────────────────── */

const LAUNCHES = [
  { short: "Product Hunt", peak: 100, call: "GO", text: "text-success-foreground", fill: "bg-success" },
  { short: "HN front page", peak: 300, call: "RISKY", text: "text-warning-foreground", fill: "bg-warning" },
  { short: "Black Friday", peak: 500, call: "NO-GO", text: "text-danger-foreground", fill: "bg-danger" },
] as const;
const SURVIVES = { value: 300, low: 250, high: 400 };
const METER_MAX = 575;
const pct = (value: number) => `${(value / METER_MAX) * 100}%`;

export function LaunchPreview() {
  const index = useLoop(1700) % LAUNCHES.length;
  const launch = LAUNCHES[index];
  return (
    <div className="flex h-full flex-col">
      <div className="flex gap-1">
        {LAUNCHES.map((option, optionIndex) => (
          <span
            key={option.short}
            className={cn(
              "rounded-[6px] border px-1.5 py-0.5 text-[10px] transition-colors duration-200",
              optionIndex === index ? "border-border-strong bg-muted text-foreground" : "border-border text-muted-foreground",
            )}
          >
            {option.short}
          </span>
        ))}
      </div>
      <p className="mt-3 text-[10px] text-muted-foreground">Will api.acme.dev survive it?</p>
      <div className="mt-1 h-[34px]">
        <AnimatePresence mode="wait" initial={false}>
          <motion.span
            key={launch.call}
            initial={{ opacity: 0, y: 6, filter: "blur(2px)" }}
            animate={{ opacity: 1, y: 0, filter: "blur(0px)" }}
            exit={{ opacity: 0, y: -6, filter: "blur(2px)" }}
            transition={{ duration: 0.22 }}
            className={cn("block text-[30px] font-semibold leading-[34px] tracking-[-.03em]", launch.text)}
          >
            {launch.call}
          </motion.span>
        </AnimatePresence>
      </div>
      <div className="relative mt-3 h-4 font-mono text-[10px]">
        <motion.span
          className="absolute -translate-x-1/2 whitespace-nowrap text-foreground"
          initial={false}
          animate={{ left: pct(launch.peak) }}
          transition={{ type: "spring", stiffness: 220, damping: 24 }}
        >
          peak {launch.peak}
        </motion.span>
      </div>
      <div className="relative h-7">
        <div className="absolute inset-x-0 top-2.5 h-1.5 rounded-full bg-muted" />
        <div
          className={cn("absolute top-2.5 h-1.5 rounded-full opacity-40 transition-colors duration-300", launch.fill)}
          style={{ left: pct(SURVIVES.low), width: `calc(${pct(SURVIVES.high)} - ${pct(SURVIVES.low)})` }}
        />
        <div className={cn("absolute top-1.5 h-3.5 w-[3px] -translate-x-1/2 rounded-full transition-colors duration-300", launch.fill)} style={{ left: pct(SURVIVES.value) }} />
        <motion.div
          className="absolute top-0 h-7 w-px bg-foreground"
          initial={false}
          animate={{ left: pct(launch.peak) }}
          transition={{ type: "spring", stiffness: 220, damping: 24 }}
        />
      </div>
      <div className="relative mt-1 h-4 font-mono text-[10px] text-muted-foreground">
        <span className="absolute -translate-x-1/2" style={{ left: pct(SURVIVES.value) }}>
          ~300
        </span>
      </div>
    </div>
  );
}

/* ── 05 · Proof you can share ─────────────────────────────────────── */

const HISTORY = [
  { commit: "2b9f6e1", note: "signed off · Product Hunt", bad: false },
  { commit: "c40d1a8", note: "~300 users · steady", bad: false },
  { commit: "a41f9c2", note: "~200 users · −33%", bad: true },
];

function Badge({ message, tone }: { message: string; tone: "pass" | "fail" }) {
  return (
    <span className="inline-flex overflow-hidden rounded-[3px] font-[Verdana,sans-serif] text-[10px] leading-[18px] text-white">
      <span className="bg-[#24292f] px-1.5">capacity</span>
      <motion.span
        className="px-1.5"
        initial={false}
        animate={{ backgroundColor: tone === "pass" ? "#1f883d" : "#cf222e" }}
        transition={{ duration: 0.3 }}
      >
        {message}
      </motion.span>
    </span>
  );
}

function SignoffRun() {
  const [step, setStep] = useState(0);
  useEffect(() => {
    const timers = [700, 1400, 2100].map((delay, index) => window.setTimeout(() => setStep(index + 1), delay));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, []);
  const regressed = step >= 3;
  return (
    <div className="flex h-full flex-col">
      <div className="relative flex flex-col gap-2.5 pl-4">
        <span className="absolute bottom-1.5 left-[3.5px] top-1.5 w-px bg-border" />
        {HISTORY.map((entry, index) => {
          const shown = step > index;
          return (
            <motion.div
              key={entry.commit}
              className="relative flex items-center gap-2 text-[10.5px]"
              initial={{ opacity: 0.25 }}
              animate={{ opacity: shown ? 1 : 0.25 }}
              transition={{ duration: 0.25 }}
            >
              <motion.span
                className="absolute -left-4 h-2 w-2 rounded-full border border-background"
                initial={{ scale: 0.7, backgroundColor: "#444444" }}
                animate={{ scale: shown ? 1 : 0.7, backgroundColor: shown ? (entry.bad ? "#ff4500" : "#0070f3") : "#444444" }}
                transition={{ duration: 0.25 }}
              />
              <span className="font-mono">{entry.commit}</span>
              <span className={entry.bad ? "text-danger-foreground" : "text-muted-foreground"}>{entry.note}</span>
            </motion.div>
          );
        })}
      </div>
      <div className="mt-4 rounded-[7px] border border-border px-2.5 py-2">
        <p className="mb-1.5 text-[10px] text-muted-foreground">README.md</p>
        <Badge tone={regressed ? "fail" : "pass"} message={regressed ? "regressed since a41f9c2" : "Product Hunt ready · Oct 15"} />
      </div>
      <AnimatePresence>
        {regressed && (
          <motion.span
            {...fadeUp(0.3)}
            className="mt-2.5 self-start rounded-full border border-border bg-muted px-2 py-0.5 text-[10px] text-muted-foreground"
          >
            Badge updated on its own. No one had to remember.
          </motion.span>
        )}
      </AnimatePresence>
    </div>
  );
}

export function SignoffPreview() {
  const run = useLoop(5000);
  return <SignoffRun key={run} />;
}

/* ── 06 · Your coding agent can run it too ────────────────────────── */

/** Becomes the index of the last passed checkpoint (ms from mount). */
function useSteps(times: number[]) {
  const [step, setStep] = useState(0);
  const schedule = useRef(times);
  useEffect(() => {
    const timers = schedule.current.map((time, index) => window.setTimeout(() => setStep(index + 1), time));
    return () => timers.forEach((timer) => window.clearTimeout(timer));
  }, []);
  return step;
}

/** Claude Code's mascot, drawn in pixels. */
function Clawd() {
  const rows = ["..XXXXXXX..", "..X.XXX.X..", "XXXXXXXXXXX", "..XXXXXXX..", "..X.X.X.X.."];
  return (
    <svg width="33" height="15" viewBox="0 0 11 5" shapeRendering="crispEdges" aria-hidden>
      {rows.flatMap((row, y) =>
        [...row].map((cell, x) => (cell === "X" ? <rect key={`${x}-${y}`} x={x} y={y} width="1" height="1" fill="#D97757" /> : null)),
      )}
    </svg>
  );
}

/** Claude Code's ⏺ and ⎿ marks, drawn so they render in any font. */
function Bullet({ done = true }: { done?: boolean }) {
  return <span className={cn("mr-1.5 inline-block h-[6px] w-[6px] -translate-y-px rounded-full", done ? "bg-success" : "bg-muted-foreground")} />;
}

function Elbow() {
  return <span className="ml-1 mr-1.5 inline-block h-[7px] w-[6px] -translate-y-[3px] border-b border-l border-muted-foreground" />;
}

function Sparkle() {
  return (
    <motion.svg
      width="9"
      height="9"
      viewBox="0 0 10 10"
      className="mr-1.5 inline-block -translate-y-px"
      animate={{ rotate: 360 }}
      transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      aria-hidden
    >
      <path d="M5 0v10M0 5h10M1.5 1.5l7 7M8.5 1.5l-7 7" stroke="#D97757" strokeWidth="1.6" strokeLinecap="round" />
    </motion.svg>
  );
}

function TrafficDots() {
  return (
    <span className="flex gap-1">
      <span className="h-2 w-2 rounded-full bg-border-strong" />
      <span className="h-2 w-2 rounded-full bg-border-strong" />
      <span className="h-2 w-2 rounded-full bg-border-strong" />
    </span>
  );
}

const CODE_BEFORE = ["import { Pool } from \"pg\";", "", "export const pool = new Pool({", "  connectionString: env.DATABASE_URL,"];
const CODE_AFTER = ["  idleTimeoutMillis: 30_000,", "});"];

/** The editor behind the terminal: watch the pool size change when Claude edits it. */
function Editor({ edited }: { edited: boolean }) {
  return (
    <div className="absolute left-0 top-5 h-[214px] w-[226px] overflow-hidden rounded-[10px] border border-border bg-[#0a0a0a] shadow-[0_16px_40px_rgba(0,0,0,0.6)]">
      <div className="flex h-6 items-center gap-2 border-b border-border px-2.5">
        <TrafficDots />
        <span className="font-mono text-[9.5px] text-muted-foreground">src/db.ts</span>
      </div>
      <pre className="px-2.5 py-2 font-mono text-[9px] leading-[15px] text-muted-foreground">
        {CODE_BEFORE.map((line, index) => (
          <div key={index}>{line || " "}</div>
        ))}
        <AnimatePresence mode="wait" initial={false}>
          {edited ? (
            <motion.div
              key="after"
              initial={{ backgroundColor: "rgba(12,206,107,0.28)" }}
              animate={{ backgroundColor: "rgba(12,206,107,0.12)" }}
              transition={{ duration: 0.8 }}
              className="-mx-2.5 px-2.5 text-success-foreground"
            >
              {"  max: 40,"}
            </motion.div>
          ) : (
            <motion.div key="before" exit={{ opacity: 0 }} className="text-foreground">
              {"  max: 10,"}
            </motion.div>
          )}
        </AnimatePresence>
        {CODE_AFTER.map((line) => (
          <div key={line}>{line}</div>
        ))}
      </pre>
    </div>
  );
}

const QUESTION = "Can staging take the Product Hunt launch?";
const TYPE_MS = 24;

function ClaudeSession() {
  // Checkpoints: submit, call 1, result 1, edit, call 2, result 2, answer.
  const typedAt = 500;
  const submitAt = typedAt + QUESTION.length * TYPE_MS + 250;
  const step = useSteps([submitAt, submitAt + 700, submitAt + 1700, submitAt + 2400, submitAt + 3200, submitAt + 4200, submitAt + 4800]);
  const typed = useTyped(QUESTION, TYPE_MS, typedAt);
  const submitted = step >= 1;
  const busy = submitted && step < 7;

  const line = (key: string, children: ReactNode, className?: string) => (
    <motion.div key={key} {...fadeUp(0)} className={className}>
      {children}
    </motion.div>
  );

  return (
    <div className="absolute right-0 top-0 flex h-[250px] w-[300px] flex-col overflow-hidden rounded-[10px] border border-border bg-background shadow-[0_24px_60px_rgba(0,0,0,0.7)]">
      <div className="flex h-6 shrink-0 items-center gap-2 border-b border-border px-2.5">
        <TrafficDots />
        <span className="font-mono text-[9.5px] text-muted-foreground">acme-shop — claude — 80×24</span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col justify-end overflow-hidden px-2.5 pb-1.5 pt-2 font-mono text-[9.5px] leading-[14px]">
        <div className="mb-2 flex items-center gap-2.5">
          <Clawd />
          <div>
            <div className="font-semibold text-foreground">
              Claude Code <span className="font-normal text-muted-foreground">v2.1</span>
            </div>
            <div className="text-muted-foreground">Sonnet 5 · ~/acme-shop</div>
          </div>
        </div>
        {submitted && line("ask", <span className="text-muted-foreground">&gt; {QUESTION}</span>, "mb-1.5")}
        {step >= 2 &&
          line(
            "call1",
            <>
              <Bullet done={step >= 3} />
              <span className="font-semibold">prescale - investigate</span> (MCP)
            </>,
          )}
        {step >= 3 && line("res1", <span className="text-muted-foreground"><Elbow />~100 users (75–110) · /api/search · pool</span>)}
        {step >= 4 &&
          line(
            "edit",
            <>
              <Bullet />
              <span className="font-semibold">Update</span>(src/db.ts)
            </>,
            "mt-1",
          )}
        {step >= 4 && line("diff", <span className="text-muted-foreground"><Elbow />max: <span className="text-danger-foreground">10</span> → <span className="text-success-foreground">40</span></span>)}
        {step >= 5 &&
          line(
            "call2",
            <>
              <Bullet done={step >= 6} />
              <span className="font-semibold">prescale - investigate</span> (MCP)
            </>,
            "mt-1",
          )}
        {step >= 6 && line("res2", <span className="text-muted-foreground"><Elbow />~150 users (120–200) · <span className="text-success-foreground">GO</span></span>)}
        {step >= 7 && line("answer", <><Bullet />Ready for Product Hunt: ~150 users, a GO.</>, "mt-1")}
        {busy && step !== 4 && (
          <motion.div key={`spin-${step}`} {...fadeUp(0)} className="mt-1 text-[#D97757]">
            <Sparkle />
            {step < 2 ? "Thinking…" : "Load-testing…"}
          </motion.div>
        )}
        <div className="mt-1.5 rounded-[5px] border border-border-strong px-1.5 py-1">
          <span className="text-muted-foreground">&gt; </span>
          {!submitted && typed}
          <Caret />
        </div>
        <div className="mt-0.5 text-[9px] text-muted-foreground">? for shortcuts</div>
      </div>
    </div>
  );
}

function AgentRun() {
  const typedAt = 500;
  const editAt = typedAt + QUESTION.length * TYPE_MS + 250 + 2400;
  const edited = useAfter(editAt);
  return (
    <div className="relative h-full w-full">
      <Editor edited={edited} />
      <ClaudeSession />
    </div>
  );
}

export function AgentPreview() {
  const run = useLoop(9800);
  return <AgentRun key={run} />;
}

export function PreviewWindow({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-background shadow-[0_24px_60px_rgba(0,0,0,0.65)]">
      <div className="flex h-7 shrink-0 items-center gap-1.5 border-b border-border px-3">
        <span className="h-2 w-2 rounded-full bg-border-strong" />
        <span className="h-2 w-2 rounded-full bg-border-strong" />
        <span className="h-2 w-2 rounded-full bg-border-strong" />
        <span className="ml-2 truncate font-mono text-[10.5px] text-muted-foreground">{title}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-hidden px-3.5 py-3">{children}</div>
    </div>
  );
}
