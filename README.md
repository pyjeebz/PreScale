# PreScale

**Launch-readiness load testing for solo & indie devs — find what breaks before your users do.**

[![CI](https://github.com/pyjeebz/prescale/actions/workflows/ci.yml/badge.svg)](https://github.com/pyjeebz/prescale/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

You ship to Hacker News / Product Hunt / Reddit, the traffic spikes, and your app falls over — 500s, exhausted DB connections, a surprise bill, or just dead during the one hour that mattered. PreScale tells you what breaks **before** that happens.

Point it at a URL. It ramps simulated traffic until something gives, then tells you, in plain English, what failed first and at what load.

```bash
prescale run https://staging.myapp.com
```

```
Scale readiness: ⚠️  Survives ~90 concurrent users

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

## Why PreScale

- **Zero config.** No test scripts, no YAML, no account. One command against a URL.
- **Stack-agnostic.** It tests a URL, so it doesn't care if you're on Vercel, Fly, Railway, a $5 VPS, Supabase, or serverless.
- **An answer, not a histogram.** "You're good to ~90 users, your DB is the wall" — not a wall of percentiles you have to interpret.
- **Safe by default.** It won't hammer a non-local host until you confirm you own it.

## Install

Requires Python 3.10+.

```bash
# From source
git clone https://github.com/pyjeebz/PreScale.git
cd PreScale
pip install ./cli

# …or in one line
pip install "git+https://github.com/pyjeebz/PreScale.git#subdirectory=cli"
```

_(PyPI release coming soon.)_

## Usage

```bash
prescale run <url> [options]
```

| Option | Default | Description |
|---|---|---|
| `-u, --max-users` | `200` | Peak virtual users to ramp to |
| `-s, --stage-seconds` | `5` | Seconds to hold each load level |
| `--path` | — | Extra route to test, relative to URL (repeatable) |
| `--from-sitemap` | off | Also pull GET routes from the site's `sitemap.xml` |
| `--latency-wall` | `2.0` | p95 latency (s) treated as failure |
| `--error-threshold` | `0.02` | Error rate (0–1) treated as failure |
| `-m, --method` | `GET` | HTTP method to fire |
| `--timeout` | `10` | Per-request timeout (s) |
| `--max-rps` | — | Cap aggregate requests/sec (a safety ceiling) |
| `--i-own-this` | off | Skip the confirmation prompt for non-local targets |
| `--ignore-robots` | off | Skip the `robots.txt` courtesy check |
| `--json` | off | Emit the raw report as JSON |

```bash
# Local app, quick check
prescale run http://localhost:8000

# Specific routes, gently, on staging
prescale run https://staging.myapp.com --path /api/search --path /pricing --max-rps 200 --i-own-this

# Ramp harder, skip the prompt, machine-readable
prescale run https://staging.myapp.com -u 500 --i-own-this --json
```

## How it works

1. **Preflight** — one request to confirm the URL is reachable.
2. **Ramp** — increase virtual users step by step (1 → max), holding each level briefly.
3. **Measure** — throughput, latency percentiles, and error kinds at every level.
4. **Report** — find the first level that crosses the error or latency threshold, and explain the likely cause in plain English.

It's self-contained (httpx + asyncio) — no external load tool or server required.

## ⚠️ Use it on what you own

Load testing sends real traffic and can cause real outages or bills. PreScale defaults to safe — it prompts before hitting any non-local host. Point it at a **staging / preview** URL, not production, unless you know what you're doing.

## Roadmap

- [x] `prescale run` — ramp, error-onset detection, plain-English readiness verdict
- [x] Multi-route testing — `--path` and opportunistic `--from-sitemap`
- [x] Saturation detection (throughput plateau) + richer bottleneck inference
- [x] Safety rails — `--max-rps` ceiling, `robots.txt` awareness, identifiable User-Agent
- [ ] `prescale audit` — static scan for scaling footguns
- [ ] PyPI release + demo GIF

## Contributing

Issues and PRs welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 — see [LICENSE](LICENSE).
