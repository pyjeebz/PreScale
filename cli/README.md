# PreScale

**Launch-readiness load testing for developers — find what breaks before your users do.**

Point it at a URL. It ramps real traffic until something gives, then tells you, in plain English, what failed first, at what load — and *why*.

```bash
pip install prescale
prescale run https://staging.myapp.com
```

```
Scale readiness: ⚠️  Survives ~90 (75–110) concurrent users
First failure   errors climb at ~150 users
Likely cause    Server returned 5xx under load — likely a DB connection pool.
```

It isn't a framework you program (like k6 or Locust) — there's nothing to script. Point it, get an answer, fix, repeat.

## Commands

- **`prescale run <url>`** — ramp traffic; what breaks first and at what load, with a confidence band.
- **`prescale investigate <url>`** — probe the culprit route to explain *why* it breaks and how to fix it. Local, deterministic, no LLM.
- **`prescale audit <url>`** — load-free HTTP hygiene check (compression, caching, CDN, HTTP/2).
- **`prescale compare`** — capacity diff of two runs; `--fail-under` / `--fail-on-regression` for CI gating.
- **`prescale run --profile product-hunt`** — frame the verdict as a launch scenario ("would survive a Product Hunt #1 launch").
- **`prescale history` / `show` / `schema`** — saved runs and their versioned JSON contract.
- **`prescale mcp`** — run as an MCP server so a coding agent can load-test mid-build (`pip install 'prescale[mcp]'`).

## Why

- **Zero config** — no test scripts, no account; one command against a URL.
- **Stack-agnostic** — Vercel, Fly, Railway, a VPS, serverless… it just needs a URL.
- **An answer, not a histogram** — "you're good to ~90 users, your DB is the wall," and how to fix it.
- **Safe by default** — won't hammer a non-local host until you confirm you own it.

Requires Python 3.10+. Full docs, examples, and source: **https://github.com/pyjeebz/PreScale**

## License

Apache 2.0 — find what breaks before your users do.
