# PreScale

**Launch-readiness load testing for developers — find what breaks before your users do.**

Point it at a URL. It ramps simulated traffic until something gives, then tells you, in plain English, what failed first and at what load.

```bash
pip install prescale-cli
prescale run https://staging.myapp.com
```

```
Scale readiness: ⚠️  Survives ~90 concurrent users
First failure   errors climb at ~150 users
Likely cause    Server returned 5xx under load — likely DB pool exhaustion.
```

## Why

- **Zero config** — no test scripts, no account, one command against a URL.
- **Stack-agnostic** — Vercel, Fly, Railway, a VPS, serverless… it just needs a URL.
- **An answer, not a histogram** — "you're good to ~90 users, your DB is the wall."
- **Safe by default** — won't hammer a non-local host until you confirm you own it.

## Usage

```bash
prescale run <url> [-u MAX_USERS] [-s STAGE_SECONDS] [--latency-wall S]
                   [--error-threshold R] [-m METHOD] [--timeout S]
                   [--i-own-this] [--json]
```

Requires Python 3.10+. Full docs and source: https://github.com/pyjeebz/PreScale

## License

Apache 2.0
