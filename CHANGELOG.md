# Changelog

## 0.2.0 — 2026-06-30

A big release: PreScale grew from a single load-test command into a full toolkit.

### Added
- **Saved runs.** Every `run` is stored under `.prescale/runs/`; `prescale history`
  lists them and `prescale show [id]` re-renders one. A versioned JSON contract
  (`prescale schema`) means `run --json`, the stored file, and `show` all share one
  shape. New flags `--store`, `--no-save`.
- **A trustworthy verdict.** The readiness verdict now carries a deterministic
  **confidence band** — "survives ~90 (80–110)" — with a stable/uncertain flag, at
  no extra cost. A brief warmup runs by default (`--no-warmup` to skip), plus
  `--repeat N` (pool ramps) and `--think-time S` (open-loop arrival).
- **`prescale investigate`.** Finds the route that breaks first, then probes it to
  diagnose *why* (a bottleneck class with confidence + evidence) and prescribe a
  fix. Fully local, no LLM.
- **MCP server (`prescale mcp`).** Load-test from a coding agent (Claude Code,
  Cursor) via `load_test` / `investigate` / `audit` / `history` tools. Optional
  extra: `pip install 'prescale[mcp]'`. Safe by default — local hosts only unless
  allowlisted (`PRESCALE_MCP_ALLOW` / `--allow`).
- **Regression + CI.** `--fail-under N` (an absolute CI gate), `prescale compare`
  (capacity diff of two runs, with the commits behind them), and
  `--fail-on-regression` (band-aware). A copy-paste GitHub Actions workflow is in
  the README.
- **Launch profiles.** `prescale run --profile product-hunt` frames the verdict as
  "would survive a Product Hunt #1 launch"; `prescale profiles` lists the scenarios.

### Changed
- `--json` now emits the full versioned Result and is robust to long lines (no more
  wrap-corruption).

## 0.1.0

Initial release: `prescale run` (zero-config launch-readiness load test) and
`prescale audit` (static scaling-hygiene check), with a shareable `--html` report.
