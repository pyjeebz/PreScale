<div align="center">

<img src="docs/logo.svg" alt="PreScale" width="64" />

# PreScale

**The open-source load tester that tells you why.**

Point it at a URL — it finds what breaks first, at what traffic, and how to fix it.
No scripts. No account. Runs on your machine.

[![CI](https://github.com/pyjeebz/prescale/actions/workflows/ci.yml/badge.svg)](https://github.com/pyjeebz/prescale/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/prescale.svg)](https://pypi.org/project/prescale/)
[![Python](https://img.shields.io/pypi/pyversions/prescale.svg)](https://pypi.org/project/prescale/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

<img src="docs/demo.gif" alt="PreScale ramps load against a URL, finds the route that breaks first, and prints a plain-English diagnosis" width="820" />

<sub><em>A real run against a fragile demo app — ramp → first break → diagnosis.</em></sub>

</div>

---

A launch, a marketing push, a Hacker News front page, a feature-flag flip — traffic spikes and your app falls over: 500s, exhausted DB connections, a surprise bill, or just dead during the hour that mattered. PreScale tells you what breaks **before** that happens.

Point it at a URL. It ramps real traffic until something gives, then tells you, in plain English, what failed first, at what load — and *why*.

```bash
pip install prescale
prescale investigate https://staging.myapp.com
```

```
Scale readiness: ⚠️  Survives ~90 (75–110) concurrent users

            Load ramp
 Users   Req/s    p50    p95    p99   Errors
    10     520   18ms   31ms   44ms      0%
    50     610   46ms  120ms  210ms      0%
    90     590   80ms  240ms  900ms      0%
   150     410  180ms   2.1s   3.4s      7%   <- breaks here

First failure   errors climb at ~150 users
Latency wall    p95 crosses 2s at ~150 users
Likely cause    Server returned 5xx under load — likely an unhandled overload
                (DB connection pool, worker queue, or an uncaught error path).
```

> Illustrative output — your numbers depend on your app.

It isn't a framework you program (like k6 or Locust) — there's nothing to script. Point it, get an answer, fix, repeat.

## Why PreScale

- **Zero config.** No test scripts, no YAML, no account. One command against a URL.
- **Stack-agnostic.** It tests a URL, so it doesn't care what's behind it — Vercel, Fly, Railway, Kubernetes, a VPS, serverless, anything.
- **An answer, not a histogram.** "You're good to ~90 users, your DB is the wall" — and [`investigate`](#investigate--and-why) tells you how to fix it.
- **Honest about uncertainty.** The verdict is a calibrated range with a stable/uncertain flag, not false precision.
- **Safe by default.** It won't hammer a non-local host until you confirm you own it.

## Install

Requires Python 3.10+.

```bash
pip install prescale             # the CLI
pip install 'prescale[mcp]'      # + the MCP server for coding agents
```

From source: `git clone https://github.com/pyjeebz/PreScale.git && pip install ./PreScale/cli`

## Commands

| Command | What it does |
|---|---|
| [`run <url>`](#run--what-breaks-first) | Ramp traffic; report what breaks first and at what load |
| [`investigate <url>`](#investigate--and-why) | …and *why* it breaks, plus how to fix it |
| [`audit <url>`](#audit--hygiene-no-load) | Load-free HTTP hygiene check (compression, caching, CDN, HTTP/2) |
| [`compare`](#ci--gate-on-capacity) | Capacity diff of two runs; regression gating for CI |
| [`profiles`](#frame-it-as-a-launch) | Launch scenarios for `--profile` |
| [`history` / `show`](#saved-runs-and-the-json-contract) | List and re-open saved runs |
| `schema` | Print the JSON Schema for a saved run |
| [`mcp`](#coding-agents-mcp) | Run as an MCP server for coding agents |

### `run` — what breaks first

```bash
# Local app, quick check
prescale run http://localhost:8000

# Specific routes, gently, on staging
prescale run https://staging.myapp.com --path /api/search --path /pricing --max-rps 200 --i-own-this

# Ramp harder, machine-readable
prescale run https://staging.myapp.com -u 500 --i-own-this --json

# A shareable, self-contained HTML report
prescale run https://staging.myapp.com --i-own-this --html report.html
```

<details>
<summary>All <code>run</code> options</summary>

| Option | Default | Description |
|---|---|---|
| `-u, --max-users` | `200` | Peak virtual users to ramp to |
| `-s, --stage-seconds` | `5` | Seconds to hold each load level |
| `--path` | — | Extra route to test, relative to URL (repeatable) |
| `--from-sitemap` | off | Also pull GET routes from the site's `sitemap.xml` |
| `--profile` | — | Frame the run as a launch scenario (see `prescale profiles`) |
| `--latency-wall` | `2.0` | p95 latency (s) treated as failure |
| `--error-threshold` | `0.02` | Error rate (0–1) treated as failure |
| `-m, --method` | `GET` | HTTP method to fire |
| `--timeout` | `10` | Per-request timeout (s) |
| `--max-rps` | — | Cap aggregate requests/sec (a safety ceiling) |
| `--no-warmup` | (warmup on) | Skip the brief warmup before measuring |
| `--repeat N` | `1` | Run the whole ramp N times and pool results (tightens the band) |
| `--think-time S` | `0` | Seconds each virtual user pauses between requests |
| `--fail-under N` | — | Exit non-zero if it survives fewer than N users (a CI gate) |
| `--i-own-this` | off | Skip the confirmation prompt for non-local targets |
| `--ignore-robots` | off | Skip the `robots.txt` courtesy check |
| `--json` | off | Emit the full versioned Result as JSON |
| `--html PATH` | — | Write a shareable HTML report (single self-contained file) |
| `--store DIR` | `./.prescale` | Directory for saved runs |
| `--no-save` | off | Don't save this run to `.prescale/runs/` |

</details>

### `investigate` — and why

`run` tells you *what* breaks; `investigate` tells you *why* and *how to fix it*. It finds the culprit route, then probes it — baseline vs loaded latency, a static-vs-dynamic comparison, error/header forensics — to classify the bottleneck and prescribe a fix. Fully local, deterministic, no LLM.

```bash
prescale investigate http://localhost:8000
prescale investigate          # re-investigate the latest saved run
```

```
🔬 Diagnosis
Likely cause: 5xx under load while static assets held — the app/backend is the wall (often a DB or upstream pool).
Bottleneck  connection_pool (high confidence)  ·  culprit /api/search
Evidence
  • culprit p95 28ms at 1 user vs 2100ms at 150 users
  • static /assets/app.js held at 150 users
  • errors under load: 5xx (180)
Try this
  → Increase the DB/upstream connection-pool size.
  → Add a pooler (e.g. pgbouncer) and check the pool checkout timeout.
```

### `audit` — hygiene, no load

A fast, load-free check of the HTTP-level footguns that decide how you scale — compression, static-asset caching, CDN, HTTP version, cookies on assets. Cheap enough to run on every commit.

```bash
prescale audit https://myapp.com
```

```
✓ Compression           Responses are compressed (br).
⚠ HTTP version          Served over HTTP/1.1.
⚠ Static asset caching  2 of 6 sampled assets have no caching headers.
✓ CDN / edge cache      Detected (Cloudflare).
```

### Frame it as a launch

Abstract user counts are hard to act on, so name the scenario with `--profile`:

```bash
prescale run https://staging.myapp.com --i-own-this --profile product-hunt
prescale profiles      # list scenarios
```

```
Launch  🛑 a Product Hunt #1 launch: unlikely (peaks ~100, you break at ~90).
```

Profiles (`steady-10k-dau`, `product-hunt`, `reddit`, `hn-frontpage`, `black-friday`) set a realistic peak concurrency + think-time and frame the verdict against it.

### Saved runs, and the JSON contract

Every run is saved to `./.prescale/runs/<id>.json` — a single versioned record (config, verdict, and per-level/per-route metrics). Re-open or share past runs without re-testing:

```bash
prescale history                  # list saved runs, newest first
prescale show                     # re-render the most recent run
prescale show <id> --html r.html  # re-render a specific run to HTML
prescale schema                   # the JSON Schema for a saved run
```

`prescale run --json` and the saved `.json` are the **same shape**, so a result is easy to script against or hand to another tool. Use `--store DIR` to change where runs are kept, `--no-save` to skip saving, and gitignore `.prescale/`.

### CI — gate on capacity

Fail a build if capacity drops below a floor:

```yaml
- run: pip install prescale
- run: prescale run https://staging.myapp.com --i-own-this --fail-under 100
```

Or catch regressions against a committed baseline (just a saved Result JSON):

```yaml
# on main — refresh and commit the baseline
- run: prescale run https://staging.myapp.com --i-own-this --json > prescale-baseline.json

# on PRs — run, compare, and comment
- run: prescale run https://staging.myapp.com --i-own-this
- run: prescale compare --baseline prescale-baseline.json --fail-on-regression --markdown > cmp.md
- run: gh pr comment "${{ github.event.number }}" --body-file cmp.md
  env:
    GH_TOKEN: ${{ github.token }}
```

`compare` diffs the latest saved run against the baseline; the regression check uses the confidence band, so it won't fail the build on noise.

### Coding agents (MCP)

PreScale ships an MCP server so an AI coding agent can load-test **mid-build** — point it at your local preview URL, get a verdict, fix, repeat.

```bash
pip install 'prescale[mcp]'
claude mcp add prescale -- prescale mcp     # Claude Code
```

It exposes `load_test`, `investigate`, `audit`, `list_runs`, and `get_run` tools that return the same compact verdict you get on the CLI. **Safe by default:** the agent can only load-test local hosts unless you allowlist others with `PRESCALE_MCP_ALLOW=staging.myapp.com` (or `prescale mcp --allow staging.myapp.com`).

## How it works

1. **Preflight** — one request to confirm the URL is reachable, then a brief warmup.
2. **Ramp** — increase virtual users step by step (1 → max), holding each level briefly.
3. **Measure** — throughput, latency percentiles, and error kinds at every level.
4. **Report** — find the first level that crosses the error or latency threshold, put a confidence band on it, and explain the likely cause in plain English. `investigate` then probes the culprit for a root cause.

It's self-contained (httpx + asyncio) — no external load tool or server required.

## ⚠️ Use it on what you own

Load testing sends real traffic and can cause real outages or bills. PreScale defaults to safe — it prompts before hitting any non-local host (and the MCP server refuses non-local hosts unless you allowlist them). Point it at a **staging / preview** URL, not production, unless you know what you're doing.

## Changelog

See [CHANGELOG.md](CHANGELOG.md). Latest: **0.2.0**.

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
