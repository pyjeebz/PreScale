# Changelog

## 1.0.0 — Unreleased

PreScale 1.0: the CLI can now send runs to your PreScale dashboard and check every
deploy from CI. It still works fully offline, and nothing is uploaded unless you ask.

### Added
- **One-line install**, no Python setup: `curl -fsSL https://prescale.dev/install | sh`
  (macOS, Linux) or `irm https://prescale.dev/install.ps1 | iex` (Windows). Installs into
  its own environment with uv. `pip install prescale` still works.
- **`prescale login` / `logout`**: connect to your dashboard with an API token (saved
  readable only by you). `PRESCALE_TOKEN` / `PRESCALE_URL` for CI.
- **`--upload`** on `run` and `investigate`, and **`prescale upload [run] [--dry-run]`**.
  The upload is the saved Result file, unchanged; `--dry-run` prints exactly that.
- **`-H` / `--header`** on `run`, `investigate` and `ci`: extra request headers (for
  example a Vercel protection bypass). Sent to your site only, never saved or uploaded.
- **`prescale ci`**: check a deploy from CI. Investigates the deploy URL, uploads, compares
  with your baseline branch, writes the job summary and keeps one PR comment up to date.
  `--fail-on-regression` fails the job on a confirmed drop. Skips production deploys.
- **GitHub Action** `pyjeebz/prescale/action@v1`, a thin wrapper around `prescale ci`.
- **`investigate --profile <name>`** (ramps to 1.5x the launch's peak) and **`--audit`**
  (the HTTP hygiene checks in the same run): everything Launch Guard needs in one command.
- `PRESCALE_GIT_COMMIT` / `PRESCALE_GIT_BRANCH` override the detected git info.
- Result schema: optional `audit` findings (still `schema_version: 1`).

### Changed
- **Confidence bands** no longer collapse to 0 on small, error-free early stages, so
  regressions on slow or short runs can be confirmed.
- **`compare`**: a run that held to its max below the old level is reported as
  *inconclusive* instead of a regression. It wasn't pushed far enough to tell.

## 0.2.1 — 2026-06-30

### Fixed
- `prescale mcp` without the optional extra printed the wrong install command
  (`pip install 'prescale'` instead of `'prescale[mcp]'`) — rich was interpreting
  `[mcp]` as console markup.

### Docs
- Rewrote the README and refreshed the PyPI description for the full 0.2.x toolkit.

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
