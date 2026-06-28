# PreScale Roadmap

From a zero-config CLI to a full-fledged product a developer can spin up and use
immediately — without ever giving up the local-first, "point it at a URL" feel.

## Product principles

- **Zero-config.** Point at a URL, get an answer. No scripts, no YAML, no account.
- **Own the answer, not the measurement.** A verdict, the route that breaks first,
  the likely cause, and the fix — in plain English. Not a histogram to decode.
- **Local-first & private.** Your data never leaves your machine by default. The
  load test and the diagnosis run entirely on your box. Any cloud feature is
  **opt-in sharing**, never silent ingest. "Your data never leaves your machine"
  is a headline trust position, not a footnote.
- **Don't become a worse k6.** No scripting hooks, no protocol breadth, no
  distributed load generation. Those drag us onto k6/Locust's turf and dilute the
  wedge.

## Locked decisions

- **Scope:** local-first OSS. Design clean seams for an *optional* cloud layer
  later — but do not build cloud now.
- **`investigate` intelligence:** fully local **and deterministic**. No LLM in the
  core path. BYO-key was rejected (user friction); a hosted LLM was rejected
  (it would mean ingesting user data). A hosted LLM explainer survives only as a
  *deferred, opt-in, zero-retention* cloud add-on — never the default.

---

## Build order

| #  | Milestone                       | Goal                                          | Depends on |
|----|---------------------------------|-----------------------------------------------|------------|
| M0 | Result contract + persistence   | A versioned result written to `.prescale/`    | —          |
| M1 | Harden the verdict              | Make the answer reproducible & honest         | M0         |
| M2 | MCP server                      | Agents load-test mid-build                    | M0         |
| M3 | `prescale investigate`          | Root cause → concrete fix, fully local        | M0, M1     |
| M4 | Regression + CI                 | Catch capacity regressions; gate deploys      | M0, M1     |
| M5 | Launch profiles + onboarding    | Map the answer to a real launch; polish       | M1         |

---

## M0 — Result contract + persistence *(foundation)*

**Why first:** MCP, investigate, regression, and CI all consume the same
structured result. Today it's computed, printed, and thrown away.

- Promote `_report_to_dict` (`cli/src/prescale_cli/commands/run.py`) into a
  versioned `Result` schema: `schema_version`, target, config, timestamp, stages,
  `verdict` (survives / onset / reason / culprit / bottleneck / saturation),
  and audit findings.
- Persist every run to `.prescale/runs/<iso-timestamp>-<short-id>.json`, plus a
  `latest` pointer.
- `prescale history` (list past runs) and `prescale show <id>` (re-render a stored
  run — no re-test).
- Ship a documented JSON Schema so MCP/CI consumers can validate.

## M1 — Harden the verdict *(trust)*

**Why:** One 5-second stage currently decides the answer. A wrong verdict kills
trust, and every downstream feature broadcasts it.

- Warmup stage (discarded) before measurement, to avoid cold-cache/JIT skew.
- Repeat-sampling per level with variance; report a confidence band
  ("survives ~90 ±15"), not false precision.
- Think-time and weighted route mixes (not just round-robin) for realistic traffic.
- A repeatability check: same target twice → consistent verdict.

## M2 — MCP server *(reach)*

**Why:** A coding agent mid-build wants exactly what PreScale returns — point at a
preview URL, get a plain-English verdict, fix, repeat. k6's "write a script" model
is a poor fit for a tool call; ours is a perfect one.

- `prescale mcp` (stdio) exposing tools: `run`, `audit`, `history`, `show`
  (and `investigate` once M3 lands), returning the M0 schema as compact summaries
  with drill-down.
- Hard rails for agent use: same-origin only, non-local targets require an explicit
  allow (reuse the guard in `run.py`), `--max-rps` default cap, robots respected.
  An agent must not be able to hit production by accident.
- One-line setup docs (`claude mcp add prescale …`, Cursor config).
- Can ship before M3, exposing `run`/`audit` first.

## M3 — `prescale investigate` *(the moat)*

**Why:** Not just *what* broke but *why* and *the fix* — the thing k6/Locust
structurally won't do. Fully local and deterministic; no LLM, no data leaving the
machine.

- An active second pass on the culprit route:
  - single-VU baseline vs loaded latency (separates slow query from concurrency
    ceiling),
  - concurrency sweep around the knee,
  - header reads (`Retry-After`, `Server`, timing),
  - static-vs-dynamic route comparison (isolates app from infra).
- A bottleneck-class taxonomy — connection-pool exhaustion, CPU saturation,
  N+1/slow query, cold start, rate limit, downstream dependency, memory/GC —
  grown out of `_bottleneck_hint` (`cli/src/prescale_cli/loadtest.py`).
- A curated remediation library keyed by class (+ stack hints from audit headers).
- **100% local + deterministic.** No LLM in the core path. Any prose-generation
  upgrade is a later, opt-in, zero-retention cloud add-on only.
- Expose through M2 once it lands.

## M4 — Regression + CI *(retention)*

**Why:** Turns a one-off probe into something teams keep installed.

- Branch baselines from M0 history; detect capacity drops
  ("breaking point dropped 200 → 90 since main") with the offending commit.
- `--fail-under <users>` / threshold gating + non-zero exit for CI.
- A GitHub Action and a PR-comment verdict with the delta.

## M5 — Launch profiles + onboarding *(the product finish)*

**Why:** "Survives 90 users" is abstract; "survives a Product Hunt #1" is a
decision.

- `--profile product-hunt | hn-frontpage | black-friday | steady-10k-dau`,
  mapping real spike shapes to the ramp.
- Translate VUs → scenario in the verdict.
- A docs site, the landing page, and a polished first-run experience.

---

## Non-goals (the "worse k6" trap)

Scripting hooks, protocol breadth (gRPC/WebSocket), and distributed load
generation. Every step toward these dilutes the zero-config wedge.

## The cloud-later seam *(not now)*

Designed for, not built yet. When/if it happens, it stays true to the privacy
principle:

- Opt-in publish/share of a single report.
- Opt-in team history sync and dashboards.
- A hosted PR bot.
- Possibly a hosted, **opt-in, zero-retention** LLM explainer for `investigate`.

In every case the user *explicitly chooses* to upload. PreScale never silently
ingests their data.
