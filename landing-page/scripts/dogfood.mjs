#!/usr/bin/env node
// Draw the footer wordmark from PreScale's own run on prescale.dev.
//
//   node scripts/dogfood.mjs ../.prescale/runs/<id>.json https://prescale.dev/r/<slug>
//
// Writes src/data/dogfood.ts. Only a real run against prescale.dev is accepted:
// the wordmark claims to be our own measurement, so it never shows anything else.
import { readFileSync, writeFileSync } from "node:fs";

const [path, report = null] = process.argv.slice(2);
if (!path) {
  console.error("usage: node scripts/dogfood.mjs <result.json> [report-url]");
  process.exit(1);
}

const result = JSON.parse(readFileSync(path, "utf8"));
const host = new URL(result.target.url).hostname;
if (host !== "prescale.dev" && !host.endsWith(".prescale.dev")) {
  console.error(`refusing ${host}: the wordmark only shows PreScale's own run on prescale.dev`);
  process.exit(1);
}

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
