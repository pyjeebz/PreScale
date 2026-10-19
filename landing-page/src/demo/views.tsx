import { createContext, useContext, type ReactNode } from "react";
import {
  ChangeTag,
  CodeBlock,
  Sparkline,
  Status,
  Surface,
  TargetStatusLabel,
  buttonPrimary,
  buttonSecondary,
  changeLabel,
  cn,
  type StatusTone,
} from "../components/ui";
import {
  PROFILES,
  TARGETS,
  findRun,
  findTarget,
  latestOnBaseline,
  launchCall,
  recentRuns,
  type LaunchCall,
  type Run,
} from "./data";
import { CapacityTimeline } from "./timeline";

export type View =
  | { name: "overview" }
  | { name: "targets" }
  | { name: "runs" }
  | { name: "connect" }
  | { name: "target"; id: string }
  | { name: "run"; id: string }
  | { name: "launch"; target: string; profile: string };

export const viewPath = (view: View) => {
  switch (view.name) {
    case "overview":
      return "";
    case "target":
      return `/targets/${view.id}`;
    case "run":
      return `/runs/${view.id.split("-")[1]}`;
    case "launch":
      return `/launch-guard?target=${view.target}&profile=${view.profile}`;
    default:
      return `/${view.name}`;
  }
};

type DemoState = {
  go: (view: View) => void;
  /** Element the tour cursor is resting on, shown with the hover style. */
  hovered: string | null;
  activePoint: string | null;
  setActivePoint: (id: string | null) => void;
};

export const DemoContext = createContext<DemoState>({
  go: () => {},
  hovered: null,
  activePoint: null,
  setActivePoint: () => {},
});

/** Props that let the tour find an element and show it hovered. */
export function useHot() {
  const { hovered } = useContext(DemoContext);
  return (id: string) => ({ "data-demo": id, "data-hover": hovered === id ? "" : undefined });
}

function PageHeader({ title, lede, actions }: { title: string; lede?: string; actions?: ReactNode }) {
  return (
    <header className="mb-5 flex items-start justify-between gap-4">
      <div className="min-w-0">
        <h2 className="text-xl font-semibold leading-[1.3] tracking-[-.02em]">{title}</h2>
        {lede && <p className="mt-0.5 truncate text-[13px] text-muted-foreground">{lede}</p>}
      </div>
      {actions && <div className="flex shrink-0 gap-2">{actions}</div>}
    </header>
  );
}

const row = "transition-colors duration-150 [@media(hover:hover)]:hover:bg-muted/60 data-[hover]:bg-muted/60";

/* ── Overview ──────────────────────────────────────────────────────── */

export function Overview() {
  const runs = TARGETS.reduce((sum, target) => sum + target.runs.length, 0);
  const stats: Array<[string, string, StatusTone | null]> = [
    ["Targets", String(TARGETS.length), null],
    ["Regressed", "1", "fail"],
    ["Runs, last 30 days", String(runs), null],
    ["Signed off", "1", "pass"],
  ];
  return (
    <>
      <PageHeader title="Overview" lede="Capacity across your targets, judged against main." />
      <div className="mb-5 grid grid-cols-4 overflow-hidden rounded-[9px] border border-border">
        {stats.map(([label, value, tone], index) => (
          <div key={label} className={cn("px-4 py-3", index > 0 && "border-l border-border")}>
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="mt-1 flex items-center gap-2 text-[22px] font-semibold tabular-nums tracking-[-.02em]">
              {value}
              {tone && <span className={cn("h-[6px] w-[6px] rounded-full", tone === "fail" ? "bg-danger" : "bg-success")} />}
            </div>
          </div>
        ))}
      </div>
      <TargetsTable />
      <RecentRuns />
    </>
  );
}

function TargetsTable() {
  const { go } = useContext(DemoContext);
  const hot = useHot();
  return (
    <Surface title="Targets" className="mb-5">
      <table className="w-full text-left text-[13px]">
        <thead>
          <tr className="border-b border-border text-xs text-muted-foreground">
            <th className="px-4 py-2 font-[450]">Target</th>
            <th className="px-4 py-2 font-[450]">Status</th>
            <th className="px-4 py-2 text-right font-[450]">Survives</th>
            <th className="px-4 py-2 font-[450]">Change</th>
            <th className="px-4 py-2 font-[450]">Trend</th>
            <th className="px-4 py-2 text-right font-[450]">Last run</th>
          </tr>
        </thead>
        <tbody>
          {TARGETS.map((target) => {
            const latest = latestOnBaseline(target);
            const trend = target.runs.filter((item) => item.branch === target.baselineBranch).map((item) => item.survives);
            return (
              <tr
                key={target.id}
                {...hot(`row-${target.id}`)}
                onClick={() => go({ name: "target", id: target.id })}
                className={cn("cursor-pointer border-b border-muted/70 last:border-b-0", row)}
              >
                <td className="px-4 py-2.5 font-medium">{target.hostname}</td>
                <td className="px-4 py-2.5">
                  <TargetStatusLabel status={target.status} />
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-[12.5px] tabular-nums">~{latest.survives}</td>
                <td className="px-4 py-2.5">
                  <ChangeTag change={target.change} />
                </td>
                <td className="px-4 py-2.5">
                  <Sparkline points={trend} status={target.status} />
                </td>
                <td className="px-4 py-2.5 text-right text-xs text-muted-foreground">{latest.when}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </Surface>
  );
}

function RecentRuns({ limit = 4 }: { limit?: number }) {
  const { go } = useContext(DemoContext);
  return (
    <Surface title="Recent runs">
      <ul>
        {recentRuns()
          .slice(0, limit)
          .map(({ target, run }) => (
            <li
              key={run.id}
              onClick={() => go({ name: "run", id: run.id })}
              className={cn("flex cursor-pointer items-center gap-4 border-b border-muted/70 px-4 py-2.5 text-[13px] last:border-b-0", row)}
            >
              <span className="w-[110px] shrink-0 truncate">{target.hostname}</span>
              <span className="w-[150px] shrink-0 truncate font-mono text-[12px] text-muted-foreground">
                {run.commit} · {run.branch}
              </span>
              <span className="w-[90px] shrink-0 text-xs text-muted-foreground">{run.source}</span>
              <span className="w-[70px] shrink-0 text-right font-mono text-[12.5px] tabular-nums">~{run.survives}</span>
              <ChangeTag change={run.change} className="w-[60px] shrink-0" />
              <span className="ml-auto text-xs text-muted-foreground">{run.when}</span>
            </li>
          ))}
      </ul>
    </Surface>
  );
}

export function TargetsView() {
  return (
    <>
      <PageHeader title="Targets" lede="The sites you test. Verified targets can be signed off." actions={<button className={cn(buttonPrimary, "h-7 px-2.5 text-xs")}>Add target</button>} />
      <TargetsTable />
    </>
  );
}

export function RunsView() {
  return (
    <>
      <PageHeader title="Runs" lede="Every uploaded run, newest first." />
      <RecentRuns limit={6} />
    </>
  );
}

export function ConnectView() {
  return (
    <>
      <PageHeader title="Connect" lede="Send runs from your terminal or CI to this dashboard." />
      <Surface title="1. Create a token" hint="Shown once. Revoke it any time." className="mb-5">
        <div className="flex items-center gap-3 px-4 py-3.5">
          <code className="flex-1 truncate rounded-[7px] border border-border bg-muted/50 px-2.5 py-1.5 font-mono text-[12px]">
            psk_live_••••••••••••••••••••••••
          </code>
          <button className={cn(buttonSecondary, "h-7 px-2.5 text-xs")}>Create token</button>
        </div>
      </Surface>
      <Surface title="2. Log in and upload">
        <div className="px-4 py-3.5">
          <CodeBlock>
            <span className="text-muted-foreground">$ </span>prescale login{"\n"}
            <span className="text-muted-foreground">$ </span>prescale investigate https://staging.myapp.com --upload
          </CodeBlock>
          <p className="mt-2 text-xs text-muted-foreground">Nothing leaves your machine unless you pass --upload.</p>
        </div>
      </Surface>
    </>
  );
}

/* ── Target ────────────────────────────────────────────────────────── */

export function TargetView({ id }: { id: string }) {
  const { go, activePoint, setActivePoint } = useContext(DemoContext);
  const target = findTarget(id);
  const headline = latestOnBaseline(target);
  const regressions = target.runs.filter((item) => item.change?.kind === "regressed" || item.change?.kind === "possible");
  const facts: Array<[string, string]> = [
    ["First failure", headline.onset],
    ["Culprit", headline.culprit ?? "none"],
    ["Cause", headline.cause ?? "not diagnosed"],
    ["Peak throughput", `${headline.peakRps} req/s`],
    ["Commit", `${headline.commit} · ${headline.branch}`],
  ];

  return (
    <>
      <PageHeader
        title={target.hostname}
        lede={[`https://${target.hostname}`, target.previewPattern && `previews ${target.previewPattern}`, `verified via ${target.verifiedVia}`]
          .filter(Boolean)
          .join(" · ")}
      />
      <div className="mb-5 grid grid-cols-[minmax(0,2fr)_minmax(0,1fr)] gap-5">
        <CapacityTimeline
          points={target.runs}
          baselineBranch={target.baselineBranch}
          active={activePoint}
          onActive={setActivePoint}
          onOpen={(runId) => go({ name: "run", id: runId })}
        />
        <Surface title="Latest verdict" hint={`${headline.date} · ${headline.source}`} action={<TargetStatusLabel status={target.status} />}>
          <div className="px-4 py-3.5">
            <div className="text-[30px] font-semibold leading-none tracking-[-.03em]">
              ~{headline.survives} <span className="text-[13px] font-[450] text-muted-foreground">users</span>
            </div>
            <p className="mt-1.5 text-xs text-muted-foreground">
              band {headline.low}–{headline.high} · <ChangeTag change={target.change} showAgainst />
            </p>
            {target.regressedSince && (
              <p className="mt-1 text-xs text-muted-foreground">
                Regression open {target.regressedSince}. It closes when {target.baselineBranch} gets back within 20% of the earlier level.
              </p>
            )}
            <div className="my-3 h-px bg-border" />
            <dl className="flex flex-col gap-1.5">
              {facts.map(([label, value]) => (
                <div key={label} className="flex justify-between gap-4">
                  <dt className="shrink-0 text-xs text-muted-foreground">{label}</dt>
                  <dd className="min-w-0 truncate text-right font-mono text-xs tabular-nums">{value}</dd>
                </div>
              ))}
            </dl>
          </div>
        </Surface>
      </div>
      <Surface title="Regressions" hint="Drops of more than 20% vs the baseline">
        {regressions.length === 0 ? (
          <p className="px-4 py-4 text-xs text-muted-foreground">None so far. Every run has held within 20% of its baseline.</p>
        ) : (
          <ul>
            {regressions.map((item) => (
              <li
                key={item.id}
                onClick={() => go({ name: "run", id: item.id })}
                className={cn("flex cursor-pointer items-center justify-between gap-4 border-b border-muted/70 px-4 py-2.5 last:border-b-0", row)}
              >
                <span className="font-mono text-[12px]">
                  {item.commit} <span className="ml-1 font-sans text-[11.5px] text-muted-foreground">{item.branch}</span>
                </span>
                <span className="flex-1 truncate text-xs text-muted-foreground">
                  {item.change && `${changeLabel[item.change.kind]}: ${item.change.arrow} users vs ${item.change.against}`}
                  {item.culprit && (
                    <>
                      {" "}· breaks at <span className="font-mono text-foreground">{item.culprit}</span>
                    </>
                  )}
                </span>
                <ChangeTag change={item.change} />
              </li>
            ))}
          </ul>
        )}
      </Surface>
    </>
  );
}

/* ── Run ───────────────────────────────────────────────────────────── */

export function RunView({ id }: { id: string }) {
  const subject = findRun(id);
  const target = findTarget(subject.targetId);
  const routes = subject.routes ?? [{ path: subject.culprit ?? "/", p95: 900 }];
  const maxP95 = Math.max(...routes.map((route) => route.p95));
  const breakingUsers = subject.onsetUsers ?? subject.maxTested;

  return (
    <>
      <PageHeader
        title={`Run ${subject.commit}`}
        lede={`${target.hostname} · ${subject.branch} · ${subject.source} · ${subject.date}`}
        actions={
          <>
            <button className={cn(buttonSecondary, "h-7 px-2.5 text-xs")}>Share report</button>
            <button className={cn(buttonSecondary, "h-7 px-2.5 text-xs")}>Sign off</button>
          </>
        }
      />
      <Surface className="mb-5 p-5">
        <div className="flex items-start gap-4">
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-warning/25 bg-warning/10 text-warning-foreground">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden>
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" />
              <line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
          </span>
          <div className="min-w-0 flex-1">
            <h3 className="text-[17px] font-[550] leading-[1.35] tracking-[-.015em]">
              Survives ~{subject.survives} ({subject.low}–{subject.high}) concurrent users
            </h3>
            <p className="mt-1 text-[13px] text-muted-foreground">
              First failure: {subject.onset}. Likely cause: {subject.cause ?? "not diagnosed"}.
            </p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-[28px] font-semibold leading-none tabular-nums">{subject.peakRps}</div>
            <div className="mt-1 text-[11px] font-[450] text-muted-foreground">peak req/s</div>
          </div>
        </div>
      </Surface>

      <div className="grid grid-cols-[minmax(0,3fr)_minmax(0,2fr)] items-start gap-5">
        <DiagnosisCard subject={subject} />

        <Surface title={`Routes at ${breakingUsers} users`}>
          {routes.map((route) => {
            const culprit = route.path === subject.culprit;
            return (
              <div key={route.path} className="flex items-center gap-3 border-b border-muted/70 px-4 py-2.5 last:border-b-0">
                <span className={cn("w-[96px] shrink-0 truncate font-mono text-xs", culprit && "font-medium text-danger-foreground")}>{route.path}</span>
                <span className="h-[3px] flex-1 overflow-hidden rounded-full bg-muted">
                  <span
                    className={cn("block h-full rounded-full", culprit ? "bg-danger" : "bg-border-strong")}
                    style={{ width: `${Math.max((route.p95 / maxP95) * 100, 4)}%` }}
                  />
                </span>
                <span className={cn("w-14 shrink-0 text-right font-mono text-[11.5px] tabular-nums", culprit ? "text-danger-foreground" : "text-muted-foreground")}>
                  {route.p95 >= 1000 ? `${(route.p95 / 1000).toFixed(2)}s` : `${route.p95}ms`}
                </span>
              </div>
            );
          })}
          <div className="border-t border-border px-4 py-2.5 text-xs text-muted-foreground">p95 per route at the first failure</div>
        </Surface>
      </div>
    </>
  );
}

export function DiagnosisCard({ subject }: { subject: Run }) {
  const hot = useHot();
  const diagnosis = subject.diagnosis;
  return (
    <Surface>
      <div className="flex items-start gap-3 border-b border-border px-4 py-3.5">
        <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] border border-border bg-muted">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className="h-[13px] w-[13px]" aria-hidden>
            <path d="M9 3v12.5a4 4 0 0 0 6 0V8" />
            <line x1="9" y1="7" x2="15" y2="7" />
            <line x1="9" y1="10" x2="15" y2="10" />
          </svg>
        </span>
        <div className="min-w-0 flex-1">
          <h3 className="text-[13.5px] font-[550]">
            Diagnosis · <span className="font-mono text-[12.5px]">{diagnosis?.bottleneck ?? "not run"}</span>
          </h3>
          <p className="mt-0.5 text-[12.5px] leading-5 text-muted-foreground">
            {diagnosis?.summary ?? "This run found where it breaks but didn't probe why. Run prescale investigate to get the cause and the fix."}
          </p>
        </div>
        {diagnosis && (
          <span className={cn("shrink-0 text-[11.5px] font-[450]", diagnosis.confidence === "high" ? "text-success-foreground" : "text-warning-foreground")}>
            {diagnosis.confidence === "high" ? "High" : "Medium"} confidence
          </span>
        )}
      </div>
      {diagnosis && (
        <>
          <ul className="border-b border-muted px-4 py-2.5">
            {diagnosis.evidence.map((line) => (
              <li key={line} className="relative py-0.5 pl-3.5 text-[12.5px] text-muted-foreground first-letter:uppercase">
                <span className="absolute left-1 top-[11px] h-[3px] w-[3px] rounded-full bg-border-strong" />
                {line}
              </li>
            ))}
          </ul>
          <ul className="px-2 py-2">
            {diagnosis.fixes.map((fix, index) => (
              <li
                key={fix}
                {...hot(`fix-${index}`)}
                className="relative rounded-[6px] py-1 pl-6 pr-2 text-[12.5px] transition-colors duration-150 data-[hover]:bg-muted/70"
              >
                <span className="absolute left-2 top-[5px] text-[11px] text-muted-foreground">→</span>
                {fix}
              </li>
            ))}
          </ul>
        </>
      )}
    </Surface>
  );
}

/* ── Launch Guard ──────────────────────────────────────────────────── */

const callStyle: Record<LaunchCall, { label: string; tone: StatusTone; text: string }> = {
  go: { label: "GO", tone: "pass", text: "text-success-foreground" },
  risky: { label: "RISKY", tone: "watch", text: "text-warning-foreground" },
  "no-go": { label: "NO-GO", tone: "fail", text: "text-danger-foreground" },
  untested: { label: "UNTESTED", tone: "muted", text: "text-muted-foreground" },
};

function pill(active: boolean) {
  return cn(
    "inline-flex h-7 items-center rounded-[7px] border px-2.5 text-xs font-[450] transition-[background-color,border-color,color,transform] duration-150 active:scale-[.97]",
    active
      ? "border-border-strong bg-muted text-foreground"
      : "border-border text-muted-foreground [@media(hover:hover)]:hover:text-foreground data-[hover]:text-foreground data-[hover]:border-border-strong",
  );
}

export function LaunchGuardView({ targetId, profileName }: { targetId: string; profileName: string }) {
  const { go } = useContext(DemoContext);
  const hot = useHot();
  const target = findTarget(targetId);
  const profile = PROFILES.find((option) => option.name === profileName) ?? PROFILES[1];
  const subject = latestOnBaseline(target);
  const { call, reason } = launchCall(subject, profile);
  const style = callStyle[call];

  return (
    <>
      <PageHeader
        title="Launch Guard"
        lede={`Will ${target.hostname} survive ${profile.label}?`}
        actions={
          <button
            {...hot("signoff")}
            title={call === "go" ? undefined : `Only a GO can be signed off for ${profile.label}.`}
            className={cn(buttonPrimary, "h-7 px-2.5 text-xs", call !== "go" && "pointer-events-none opacity-50", "data-[hover]:bg-white")}
          >
            Sign off for {profile.short}
          </button>
        }
      />
      <div className="mb-4 flex flex-wrap items-center gap-x-5 gap-y-2">
        <div className="flex items-center gap-1.5">
          <span className="mr-1 text-xs text-muted-foreground">Target</span>
          {TARGETS.map((option) => (
            <button
              key={option.id}
              {...hot(`target-${option.id}`)}
              onClick={() => go({ name: "launch", target: option.id, profile: profile.name })}
              className={pill(option.id === target.id)}
            >
              {option.hostname}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="mr-1 text-xs text-muted-foreground">Launch</span>
          {PROFILES.map((option) => (
            <button
              key={option.name}
              {...hot(`profile-${option.name}`)}
              onClick={() => go({ name: "launch", target: target.id, profile: option.name })}
              className={pill(option.name === profile.name)}
            >
              {option.short}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-[820px]">
        <Surface className="mb-4">
          <div className="px-5 py-4">
            <div className="flex items-baseline gap-4">
              <span className={cn("text-[40px] font-semibold leading-none tracking-[-.03em]", style.text)}>{style.label}</span>
              <span className="text-[13px] text-muted-foreground">for {profile.label}</span>
            </div>
            <p className="mt-2 max-w-[600px] text-[13px] leading-[1.55] text-muted-foreground">{reason}</p>
            <PeakMeter subject={subject} peak={profile.peak} />
          </div>
        </Surface>
        <Surface title="Checklist" hint={`Judged from run ${subject.commit} · ${subject.when}`}>
          <ul>
            {checklist(subject, profile.name, profile.short, style, target.verifiedVia).map(([title, tone, result, detail]) => (
              <li key={title} className="grid grid-cols-[150px_1fr_auto] items-start gap-4 border-b border-muted/70 px-4 py-2.5 last:border-b-0">
                <span className="text-[13px] font-[450]">{title}</span>
                <div className="min-w-0 text-xs leading-5 text-muted-foreground">{detail}</div>
                <Status tone={tone}>{result}</Status>
              </li>
            ))}
          </ul>
        </Surface>
      </div>
    </>
  );
}

function checklist(
  subject: Run,
  profileName: string,
  profileShort: string,
  style: (typeof callStyle)[LaunchCall],
  verifiedVia: string,
): Array<[string, StatusTone, string, ReactNode]> {
  const tested = subject.profile === profileName;
  const audit = subject.audit;
  const warnings = audit?.filter((finding) => finding.status !== "pass") ?? [];
  return [
    ["Capacity", style.tone, style.label, <>Survives <span className="font-mono">~{subject.survives}</span> users (band <span className="font-mono">{subject.low}–{subject.high}</span>).</>],
    [
      "Tested to the peak",
      tested ? "pass" : "watch",
      tested ? "Yes" : "Not yet",
      tested ? <>Run with <span className="font-mono">--profile {profileName}</span>.</> : <>Ramped to {subject.maxTested} users. Re-run with the {profileShort} profile to test its exact shape.</>,
    ],
    [
      "Root cause",
      subject.diagnosis ? "pass" : "watch",
      subject.diagnosis ? "Diagnosed" : "Not diagnosed",
      <>
        Breaks first at <span className="font-mono">{subject.culprit}</span>
        {subject.diagnosis && <> · {subject.diagnosis.bottleneck}. Top fix: {subject.diagnosis.fixes[0]}</>}
      </>,
    ],
    audit
      ? ["HTTP hygiene", warnings.length ? "watch" : "pass", warnings.length ? `${warnings.length} warning` : "Clean", warnings.length ? <>{warnings[0].name}: {warnings[0].detail}</> : <>Compression, caching, CDN and HTTP version all check out.</>]
      : ["HTTP hygiene", "muted", "Not checked", <>Add <span className="font-mono">--audit</span> to check compression, caching, CDN and HTTP/2.</>],
    ["Ownership", "pass", "Verified", <>Verified via {verifiedVia}. A GO can be signed off publicly.</>],
  ];
}

export function PeakMeter({ subject, peak }: { subject: Pick<Run, "survives" | "low" | "high">; peak: number }) {
  const max = Math.max(subject.high, peak, subject.survives) * 1.15;
  const pct = (value: number) => `${(value / max) * 100}%`;
  const fill = subject.low >= peak ? "bg-success" : subject.survives >= peak ? "bg-warning" : "bg-danger";
  // Keep the two labels apart when the values sit close together.
  const close = Math.abs(subject.survives - peak) / max < 0.12;
  return (
    <div className="mt-4" role="img" aria-label={`Survives ~${subject.survives} users (band ${subject.low}–${subject.high}); peak near ${peak}.`}>
      <div className="relative h-8">
        <div className="absolute inset-x-0 top-3 h-2 rounded-full bg-muted" />
        <div className={`absolute top-3 h-2 rounded-full opacity-35 ${fill}`} style={{ left: pct(subject.low), width: `calc(${pct(subject.high)} - ${pct(subject.low)})` }} />
        <div className={`absolute top-2 h-4 w-[3px] -translate-x-1/2 rounded-full ${fill}`} style={{ left: pct(subject.survives) }} />
        <div className="absolute top-0 h-8 w-px bg-foreground" style={{ left: pct(peak) }} />
      </div>
      <div className="relative mt-1 h-4 font-mono text-[11px] text-muted-foreground">
        <span className={cn("absolute whitespace-nowrap", close ? (subject.survives >= peak ? "" : "-translate-x-full") : "-translate-x-1/2")} style={{ left: pct(subject.survives) }}>
          ~{subject.survives}
        </span>
        <span
          className={cn("absolute whitespace-nowrap text-foreground", close ? (subject.survives >= peak ? "-translate-x-full pr-2" : "pl-2") : "-translate-x-1/2")}
          style={{ left: pct(peak) }}
        >
          peak {peak}
        </span>
      </div>
    </div>
  );
}
