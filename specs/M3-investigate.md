# M3 — `prescale investigate` (the moat)

Status: **spec / not started**
Depends on: M0 (Result envelope), M1 (a trustworthy verdict + the `transport=`
test seam), M2 (to expose it as an MCP tool).

## Goal

Turn *what* broke into *why* and *the fix*. Today `run` names the route that
breaks first; `investigate` runs an **active second pass** on that culprit,
classifies the bottleneck, and prescribes a concrete remediation — e.g.
*"connection-pool ceiling around ~90 VUs: raise the pool / add pgbouncer."*

This is the thing k6/Locust structurally won't do, and it's **fully local and
deterministic — no LLM in the core path** (locked). It grows the existing
rule-based `_bottleneck_hint` (`loadtest.py`) into a real classifier backed by
evidence.

## Command

- `prescale investigate <url>` — run a ramp (find the culprit + onset), then probe
  and diagnose. One shot.
- `prescale investigate` (no arg) — investigate the **latest saved run**'s culprit
  by re-probing its target URL (composes with a prior `prescale run`).
- Flags: `--json`, `--store`, the load-shaping flags `run` has (`-u`, `--path`,
  `--i-own-this`, `--max-rps`, …). `--html` later.

## The active second pass (probes)

After the ramp gives us the culprit route and onset level, run small, targeted
experiments on that route (not a full ramp — fast):

1. **Baseline vs loaded** — measure latency at **1 VU** (unloaded) vs at the onset
   level. Slow already at 1 VU ⇒ an *intrinsically slow endpoint*; fast baseline
   that balloons under load ⇒ *contention/concurrency*.
2. **Concurrency sweep around the knee** — a few levels near onset
   (≈ onset/2, onset, onset·1.5) watching throughput vs latency. Throughput
   plateaus while latency climbs ⇒ a *concurrency ceiling* (requests queue).
3. **Static-vs-dynamic** — hit a static asset (found via the audit asset
   extractor) at the same load. Static holds but the dynamic culprit fails ⇒ the
   wall is in the *app/backend*; static fails too ⇒ *connection/infra-level*.
4. **Error & header forensics** — read the failing level's error kinds, status
   codes, and headers (`Retry-After`, `Server`, `Via`, timing) for class + stack
   hints. (Reuses `RouteStat.error_kinds` / `status_counts`.)

All probes respect the same safety rails (same-origin, `--max-rps`, non-local
confirm).

## Bottleneck taxonomy (deterministic classifier)

First-match-wins rules over the probe evidence; each result carries a
**confidence** (high / medium / low) — honest about being heuristic, like M1's band.

| Class | Signature |
|---|---|
| `rate_limited` | errors dominated by 429 |
| `overload_shedding` | 503s, often with `Retry-After` (proxy/LB shed) |
| `connection_ceiling` | connection-refused / timeouts **and** static route also degrades |
| `connection_pool` | 5xx (500/503) under load while static holds (app/DB pool) |
| `concurrency_ceiling` | low errors, p95 wall crossed, throughput plateaued, fast baseline |
| `slow_endpoint` | p95 wall crossed but already slow at 1 VU (slow query / N+1 / heavy compute) |
| `cold_start` | first requests slow then fast (serverless warmup) |
| `unknown` | none match — report the raw signals with low confidence |

## Remediation library

A curated `class → fix` map (deterministic text), enriched with **stack hints**
from response headers (`Server: gunicorn/uvicorn/nginx/…`, CDN markers reused from
`audit`). Examples:

- `concurrency_ceiling` → raise worker/thread count; check for a single-threaded
  server or a global lock / serialized resource.
- `connection_pool` → increase the DB/upstream pool size; add pgbouncer; check pool
  timeout.
- `connection_ceiling` → raise the server's connection/backlog limit
  (`worker_connections`, `somaxconn`); add instances behind a LB.
- `overload_shedding` → the proxy is shedding load — add capacity / autoscale.
- `rate_limited` → a 429 limiter kicked in — confirm it's intentional; raise it.
- `slow_endpoint` → slow even at 1 user — profile the query; add an index, cache,
  or pagination.
- `cold_start` → serverless cold start — use min instances / provisioned concurrency.

## Output & persistence (additive; `schema_version` stays 1)

`investigate` persists a Result with an extra **`investigation`** block, so `show`
and the MCP `get_run` see it too:

```jsonc
"investigation": {
  "culprit_route": "/api/search",
  "bottleneck_class": "connection_pool",
  "confidence": "high",
  "summary": "5xx under load while static assets held — likely DB/upstream pool.",
  "evidence": [
    "baseline p95 28ms at 1 VU vs 2.1s at 150 VUs",
    "static /assets/app.js held at <50ms through 150 VUs",
    "errors: 5xx (180), onset at 150 users"
  ],
  "remediation": ["Increase the DB connection pool…", "Add pgbouncer…"],
  "stack": { "server": "gunicorn", "cdn": "Cloudflare" }
}
```

Terminal: the readiness report plus a **"Diagnosis"** panel (class, confidence,
evidence bullets, remediation). `--json` emits the full Result.

## Structure
- `investigate.py` — probes (async, take a `client`/`transport`), the classifier
  (pure, evidence → class+confidence), and the remediation map. The classifier and
  remediation are **pure functions** → fully unit-testable.
- `commands/investigate.py` — the command (ramp → probe → classify → render/persist).
- MCP: add an `investigate` tool in `mcp_server.py` / `mcp_tools.py`.

## Build sub-steps
1. **M3.1** — probe engine (baseline, sweep, static-vs-dynamic, forensics) on the
   `transport=` seam.
2. **M3.2** — taxonomy + classifier (pure), grown from `_bottleneck_hint`.
3. **M3.3** — remediation library (+ header/stack hints).
4. **M3.4** — `prescale investigate <url>` and the no-arg saved-run variant;
   render the Diagnosis panel; persist the `investigation` block; `--json`.
5. **M3.5** — MCP `investigate` tool + README docs + tests.

## Tests
- Classifier: synthetic evidence → expected class + confidence for each taxonomy row.
- Remediation: each class yields non-empty, class-appropriate text; stack hints applied.
- Probes via the `transport=` seam (baseline vs loaded; static-vs-dynamic).
- Command: `investigate <url>` end-to-end against a local mock; `investigation`
  block persisted and round-trips through `show` / `get_run`.

## Decisions (override any)
1. **Active probing** (baseline / sweep / static-vs-dynamic / forensics), not just
   re-analyzing existing run data — more network, materially better diagnosis.
   (The moat is the *accuracy* of the "why".)
2. **Deterministic classifier with explicit confidence** (high/med/low) + evidence
   shown — no LLM; honest about heuristics.
3. **`investigation` stored as an additive Result field** so `show` / MCP reuse it.
4. **`investigate <url>` runs a fresh ramp**; no-arg re-probes the latest saved run.
