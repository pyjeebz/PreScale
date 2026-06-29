# M2 — MCP server

Status: **spec / not started**
Depends on: M0 (returns the `Result` envelope), M1 (a trustworthy verdict to return).

## Goal

Let a coding agent (Claude Code, Cursor, …) **load-test mid-build**: point it at
the local preview URL, get a plain-English verdict back, fix, repeat. This is the
timely wedge — k6's "write a script" model is a poor fit for a tool call;
PreScale's "point at a URL, get an answer" is a perfect one. `prescale mcp`
exposes run / audit / history as MCP tools that return the M0 `Result`.

## Why now

M0 gave a stable, compact result contract; M1 made the verdict trustworthy. An
agent loop is only as good as the answer it gets, so MCP rides on both.

## Surface

`prescale mcp` launches a **stdio** MCP server (the transport coding agents use).
One-line install:
- Claude Code: `claude mcp add prescale -- prescale mcp`
- Cursor: a small JSON snippet (documented).

### Tools
- `load_test(url, max_users=100, paths=[], stage_seconds=3, …)` → a **compact**
  summary (verdict, survives band, culprit, bottleneck, peak rps, run id).
  Persists the full Result to `.prescale/runs/`.
- `audit(url)` → hygiene findings (pass / warn / fail + fixes).
- `list_runs()` → recent saved runs (id, when, host, verdict one-liner).
- `get_run(id)` → the full Result envelope (to drill in when the summary isn't enough).

### Resource
- `prescale://schema` → the Result JSON Schema.

## Safety rails (the important part)

An agent calls tools with no human in the loop, so the interactive `--i-own-this`
confirm doesn't apply. Instead:

- **Local-only by default.** `load_test` only targets local hosts
  (`localhost` / `127.0.0.1` / `::1`) unless explicitly allowed — exactly the
  "agent tests the app it's building" case, safe out of the box.
- **Explicit allowlist for non-local.** `PRESCALE_MCP_ALLOW=staging.myapp.com,…`
  (or `prescale mcp --allow host`) opts specific hosts in. Anything else is
  refused with a clear message. `*` is supported but discouraged.
- **Default rate ceiling.** MCP mode applies a conservative `--max-rps` by default
  so even allowed hosts aren't hammered.
- Same-origin target building and robots awareness still apply.

Net: an agent can freely load-test the local dev server, and can only reach a
staging/prod host the human **explicitly allowed** when installing the server.

## Token efficiency

Tool results are **compact summaries**, not the full stage-by-stage envelope —
agents pay for every token of tool output. The full Result is one `get_run(id)`
away when needed. (This is also why PreScale fits an agent loop where k6's raw
metrics don't.)

## Packaging

- `mcp` is an **optional dependency**: `pip install 'prescale[mcp]'`. The core CLI
  stays lean.
- `prescale mcp` errors helpfully if the extra isn't installed.

## Structure

- `mcp_tools.py` — pure logic + async impls (summarize, host-allow, run / audit /
  list / get). **No `mcp` import** → always unit-testable.
- `mcp_server.py` — thin FastMCP wiring (`@mcp.tool`), imports `mcp` lazily.
- `commands/mcp.py` — the `prescale mcp` command; lazy-imports the server so the
  core install works without the extra.

## Build sub-steps
1. **M2.1** — `prescale mcp` + FastMCP skeleton; `load_test` + `audit` tools;
   `[mcp]` extra; stdio transport.
2. **M2.2** — safety rails (local-only default + allowlist + rate ceiling) +
   compact summaries + persist runs.
3. **M2.3** — `list_runs` + `get_run` + the schema resource.
4. **M2.4** — setup docs (Claude Code, Cursor) + tests.

## Schema
No new result fields. The `load_test` summary is a projection of the existing
Result; `result.schema.json` is unchanged.

## Tests
- `summarize_result` projection (pure).
- `host_allowed` / allowlist parsing: local allowed by default; non-local refused
  unless listed; `*` allows.
- Engine path via the M1 `transport=` seam where useful.
- FastMCP wiring behind `pytest.importorskip("mcp")` (skips where the extra isn't
  installed).

## Decisions (override any)
1. **Safety = local-only by default + `PRESCALE_MCP_ALLOW` for non-local + a
   default rate ceiling.** (Agent tests localhost freely; prod needs explicit
   opt-in.)
2. **Compact summaries by default; full Result via `get_run`.** (Token-efficient.)
3. **`mcp` is an optional extra** (`prescale[mcp]`); core install unchanged.
4. **stdio transport** for M2 (the coding-agent default); SSE/HTTP later if needed.
