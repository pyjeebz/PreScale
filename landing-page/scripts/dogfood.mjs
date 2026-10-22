#!/usr/bin/env node
// Draw the footer wordmark from PreScale's own run on its dashboard.
//
//   node scripts/dogfood.mjs ../.prescale/runs/<id>.json [https://prescale.dev/r/<slug>]
//
// Writes src/data/dogfood.ts. Only our own measurement is accepted: a run against
// prescale.dev, or a replica-mode run (`prescale run --app`) of a local build of
// the dashboard. Vercel doesn't allow load tests on our plan, so in practice it's
// the replica, and the caption says so.
import { readFileSync, writeFileSync } from "node:fs";

const [path, report = null] = process.argv.slice(2);
if (!path) {
  console.error("usage: node scripts/dogfood.mjs <result.json> [report-url]");
  process.exit(1);
}

const result = JSON.parse(readFileSync(path, "utf8"));
const target = new URL(result.target.url).hostname;
const local = ["localhost", "127.0.0.1", "0.0.0.0", "::1"].includes(target);
const ours = target === "prescale.dev" || target.endsWith(".prescale.dev");
if (!ours && !(local && result.config?.replica)) {
  console.error(`refusing ${target}: the wordmark only shows PreScale's own run ` +
    "(prescale.dev, or a replica-mode run of the dashboard)");
  process.exit(1);
}
const host = ours ? target : "a local build of prescale.dev/dashboard";

const stages = result.stages
  .filter((stage) => stage.total && stage.p95_ms > 0)
  .map((stage) => ({ users: stage.users, p95: Math.round(stage.p95_ms) }));
if (stages.length < 3) {
  console.error("need at least 3 measured stages to draw the wordmark");
  process.exit(1);
}

const run = { host, measuredAt: result.created_at, report, stages };
const file = new URL("../src/data/dogfood.ts", import.meta.url);
const source = readFileSync(file, "utf8").replace(
  /export const DOGFOOD: DogfoodRun \| null = [\s\S]*;\n$/,
  `export const DOGFOOD: DogfoodRun | null = ${JSON.stringify(run, null, 2)};\n`,
);
writeFileSync(file, source);
console.log(`wordmark drawn from ${stages.length} stages on ${host} (${result.created_at})`);
