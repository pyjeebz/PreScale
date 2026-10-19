/**
 * Mock workspace for the interactive dashboard on the landing page. Shapes
 * follow the dashboard's view models (web/src/lib/data.ts), and the numbers
 * obey the same rules: a regression is a >20% drop, confirmed when the
 * confidence bands don't overlap.
 */

export type ChangeKind = "regressed" | "possible" | "improved" | "steady" | "inconclusive";
export type TargetStatus = "healthy" | "watch" | "critical";

export interface Change {
  kind: ChangeKind;
  pct: string;
  arrow: string;
  against: string;
}

export interface Diagnosis {
  bottleneck: string;
  confidence: "high" | "medium" | "low";
  summary: string;
  evidence: string[];
  fixes: string[];
}

export interface Run {
  id: string;
  targetId: string;
  commit: string;
  branch: string;
  source: string;
  preview: boolean;
  survives: number;
  low: number;
  high: number;
  maxTested: number;
  /** Users at the first failure; null when it held to the max tested. */
  onsetUsers: number | null;
  onset: string;
  culprit: string | null;
  cause: string | null;
  peakRps: number;
  change: Change | null;
  date: string;
  when: string;
  profile?: string;
  diagnosis?: Diagnosis;
  routes?: Array<{ path: string; p95: number }>;
  audit?: Array<{ name: string; status: "pass" | "warn" | "fail"; detail: string; fix?: string }>;
}

export interface Target {
  id: string;
  hostname: string;
  status: TargetStatus;
  change: Change | null;
  regressedSince: string | null;
  baselineBranch: string;
  previewPattern: string | null;
  verifiedVia: string;
  runs: Run[];
}

const shopRuns: Run[] = [
  run("shop", "9b1e2c0", "main", 140, 110, 180, "Sep 22", "3 weeks ago", { kind: "improved", pct: "+8%", arrow: "130 → 140", against: "main @ 2c7a1f4" }),
  run("shop", "3fd81aa", "main", 150, 120, 200, "Sep 25", "3 weeks ago", { kind: "steady", pct: "+7%", arrow: "140 → 150", against: "main @ 9b1e2c0" }),
  run("shop", "c72d1e9", "feat/wishlist", 145, 110, 200, "Sep 26", "3 weeks ago", { kind: "steady", pct: "−3%", arrow: "150 → 145", against: "main @ 3fd81aa" }, "CI · PR #38"),
  run("shop", "5e0b7d3", "main", 150, 120, 200, "Sep 29", "2 weeks ago", { kind: "steady", pct: "±0%", arrow: "150 → 150", against: "main @ 3fd81aa" }),
  run("shop", "0aa94f1", "main", 155, 120, 200, "Oct 2", "2 weeks ago", { kind: "steady", pct: "+3%", arrow: "150 → 155", against: "main @ 5e0b7d3" }),
  run("shop", "8f3c2b6", "feat/reviews", 150, 120, 200, "Oct 5", "11 days ago", { kind: "steady", pct: "−3%", arrow: "155 → 150", against: "main @ 0aa94f1" }, "CI · PR #41"),
  run("shop", "71aa0c9", "main", 150, 120, 200, "Oct 7", "9 days ago", { kind: "steady", pct: "−3%", arrow: "155 → 150", against: "main @ 0aa94f1" }),
  {
    ...run("shop", "a41f9c2", "main", 100, 75, 110, "Oct 9", "7 days ago", { kind: "regressed", pct: "−33%", arrow: "150 → 100", against: "main @ 71aa0c9" }, "CI · push"),
    maxTested: 200,
    onsetUsers: 120,
    onset: "errors climbed at ~120 users",
    culprit: "/api/search",
    cause: "connection_pool",
    peakRps: 412,
    diagnosis: {
      bottleneck: "connection_pool",
      confidence: "high",
      summary:
        "5xx under load while static assets held: the app/backend is the wall (often a DB or upstream pool).",
      evidence: [
        "culprit p95 48ms at 1 user vs 1,240ms at 120 users",
        "static /app.css held at 120 users",
        "errors under load: 5xx (212)",
        "throughput plateaued while users kept rising",
      ],
      fixes: [
        "Increase the DB/upstream connection-pool size.",
        "Add a pooler (e.g. pgbouncer) and check the pool checkout timeout.",
        "Make sure connections are released promptly under load (no leaks).",
      ],
    },
    routes: [
      { path: "/api/search", p95: 1240 },
      { path: "/checkout", p95: 410 },
      { path: "/products", p95: 182 },
      { path: "/", p95: 96 },
    ],
  },
  run("shop", "d93be10", "fix/search-pool", 150, 120, 200, "Oct 12", "4 days ago", { kind: "improved", pct: "+50%", arrow: "100 → 150", against: "main @ a41f9c2" }, "CI · PR #44"),
  {
    ...run("shop", "e1c0f77", "main", 100, 75, 110, "Oct 14", "2 days ago", { kind: "steady", pct: "±0%", arrow: "100 → 100", against: "main @ a41f9c2" }, "CI · push"),
    onsetUsers: 120,
    onset: "errors climbed at ~120 users",
    culprit: "/api/search",
    cause: "connection_pool",
    peakRps: 405,
  },
];

const apiRuns: Run[] = [
  run("api", "4c21ab9", "main", 260, 200, 300, "Sep 24", "3 weeks ago", null),
  run("api", "b7e0d12", "main", 280, 250, 350, "Sep 30", "2 weeks ago", { kind: "steady", pct: "+8%", arrow: "260 → 280", against: "main @ 4c21ab9" }),
  run("api", "16fa3c8", "main", 290, 250, 350, "Oct 4", "12 days ago", { kind: "steady", pct: "+4%", arrow: "280 → 290", against: "main @ b7e0d12" }),
  run("api", "e8d4407", "main", 300, 250, 400, "Oct 8", "8 days ago", { kind: "steady", pct: "+3%", arrow: "290 → 300", against: "main @ 16fa3c8" }),
  {
    ...run("api", "2b9f6e1", "main", 300, 250, 400, "Oct 15", "yesterday", { kind: "steady", pct: "±0%", arrow: "300 → 300", against: "main @ e8d4407" }, "CLI"),
    maxTested: 450,
    onsetUsers: 350,
    onset: "p95 crossed the latency wall at ~350 users",
    culprit: "/v1/orders",
    cause: "concurrency_ceiling",
    peakRps: 1180,
    profile: "hn-frontpage",
    diagnosis: {
      bottleneck: "concurrency_ceiling",
      confidence: "medium",
      summary: "Latency rose in step with users while errors stayed flat: requests are queueing for a fixed number of workers.",
      evidence: [
        "p95 doubled between 300 and 350 users with no errors",
        "throughput flat at ~1,180 req/s past 300 users",
      ],
      fixes: ["Raise the worker or instance concurrency limit.", "Move slow work off the request path."],
    },
    routes: [
      { path: "/v1/orders", p95: 2140 },
      { path: "/v1/products", p95: 620 },
      { path: "/v1/health", p95: 40 },
    ],
    audit: [
      { name: "Compression", status: "pass", detail: "Responses are compressed (br)." },
      { name: "HTTP version", status: "pass", detail: "Negotiated HTTP/2." },
      {
        name: "Static asset caching",
        status: "warn",
        detail: "2 of 3 sampled assets have no long-lived Cache-Control.",
        fix: "serve hashed assets with Cache-Control: public, max-age=31536000, immutable",
      },
    ],
  },
];

const docsRuns: Run[] = [
  run("docs", "aa0e1f3", "main", 210, 150, 300, "Oct 1", "2 weeks ago", null),
  run("docs", "c91d2b4", "main", 210, 150, 300, "Oct 6", "10 days ago", { kind: "steady", pct: "±0%", arrow: "210 → 210", against: "main @ aa0e1f3" }),
  {
    ...run("docs", "f03a8e7", "main", 160, 120, 200, "Oct 13", "3 days ago", { kind: "possible", pct: "−24%", arrow: "210 → 160", against: "main @ c91d2b4" }),
    onsetUsers: 200,
    onset: "p95 crossed the latency wall at ~200 users",
    culprit: "/search",
    cause: "slow_endpoint",
  },
];

export const TARGETS: Target[] = [
  {
    id: "shop",
    hostname: "shop.acme.dev",
    status: "critical",
    change: { kind: "regressed", pct: "−33%", arrow: "150 → 100", against: "main @ 71aa0c9" },
    regressedSince: "since a41f9c2",
    baselineBranch: "main",
    previewPattern: "shop-*-acme.vercel.app",
    verifiedVia: "DNS",
    runs: shopRuns,
  },
  {
    id: "api",
    hostname: "api.acme.dev",
    status: "healthy",
    change: { kind: "steady", pct: "±0%", arrow: "300 → 300", against: "main @ e8d4407" },
    regressedSince: null,
    baselineBranch: "main",
    previewPattern: null,
    verifiedVia: "DNS",
    runs: apiRuns,
  },
  {
    id: "docs",
    hostname: "docs.acme.dev",
    status: "watch",
    change: { kind: "possible", pct: "−24%", arrow: "210 → 160", against: "main @ c91d2b4" },
    regressedSince: null,
    baselineBranch: "main",
    previewPattern: null,
    verifiedVia: "HTML file",
    runs: docsRuns,
  },
];

export const findTarget = (id: string) => TARGETS.find((target) => target.id === id) ?? TARGETS[0];
export const findRun = (id: string) =>
  TARGETS.flatMap((target) => target.runs).find((candidate) => candidate.id === id) ?? shopRuns[7];
export const latestOnBaseline = (target: Target) =>
  [...target.runs].reverse().find((candidate) => candidate.branch === target.baselineBranch)!;
export const recentRuns = () =>
  TARGETS.flatMap((target) => target.runs.map((candidate) => ({ target, run: candidate })))
    .sort((a, b) => order(b.run.date) - order(a.run.date))
    .slice(0, 6);

/** "Sep 22" → sortable number. */
function order(date: string) {
  const [month, day] = date.split(" ");
  return (month === "Oct" ? 100 : 0) + Number(day);
}

function run(
  targetId: string,
  commit: string,
  branch: string,
  survives: number,
  low: number,
  high: number,
  date: string,
  when: string,
  change: Change | null,
  source = "CI · push",
): Run {
  const preview = branch !== "main";
  return {
    id: `${targetId}-${commit}`,
    targetId,
    commit,
    branch,
    source,
    preview,
    survives,
    low,
    high,
    maxTested: Math.max(200, high),
    onsetUsers: high + 20,
    onset: `errors climbed at ~${high + 20} users`,
    culprit: targetId === "shop" ? "/api/search" : targetId === "api" ? "/v1/orders" : "/search",
    cause: null,
    peakRps: Math.round(survives * (targetId === "api" ? 3.9 : 4.1)),
    change,
    date,
    when,
  };
}

/** Launch profiles, mirrored from the CLI (cli/src/prescale_cli/profiles.py). */
export const PROFILES = [
  { name: "steady-10k-dau", label: "steady traffic (~10k daily users)", short: "Steady 10k DAU", peak: 25 },
  { name: "product-hunt", label: "a Product Hunt #1 launch", short: "Product Hunt #1", peak: 100 },
  { name: "reddit", label: "a top Reddit post spike", short: "Reddit spike", peak: 300 },
  { name: "hn-frontpage", label: "a Hacker News front-page hug", short: "HN front page", peak: 300 },
  { name: "black-friday", label: "sustained Black Friday load", short: "Black Friday", peak: 500 },
] as const;

export type Profile = (typeof PROFILES)[number];
export type LaunchCall = "go" | "risky" | "no-go" | "untested";

/** Same rule as the dashboard (web/src/lib/launch.ts). */
export function launchCall(subject: Run, profile: Profile): { call: LaunchCall; reason: string } {
  const peak = profile.peak;
  if (subject.onsetUsers === null && subject.maxTested < peak) {
    return {
      call: "untested",
      reason: `Held to all ${subject.maxTested} users tested, but ${profile.label} peaks near ${peak}. Re-run with the profile to test that high.`,
    };
  }
  if (subject.survives < peak) {
    return { call: "no-go", reason: `Survives ~${subject.survives} users; ${profile.label} peaks near ${peak}.` };
  }
  if (subject.low >= peak) {
    return {
      call: "go",
      reason: `Clears the ~${peak}-user peak of ${profile.label}, even at the low end of the confidence band (${subject.low}–${subject.high}).`,
    };
  }
  return {
    call: "risky",
    reason: `Survives ~${subject.survives} on average, but the confidence band (${subject.low}–${subject.high}) dips below the ~${peak}-user peak.`,
  };
}
