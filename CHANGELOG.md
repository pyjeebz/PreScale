# Changelog

## 1.0.0 — 2026-10-20

PreScale 1.0: the CLI can now send runs to your PreScale dashboard and check every
deploy from CI. It still works fully offline, and nothing is uploaded unless you ask.

### Highlights
- **A capacity check on every pull request.** The GitHub Action load-tests each preview
  deploy and keeps one comment on the PR: how many users this deploy survives compared with
  `main`, what breaks first, why, and the fix.
- **A free dashboard at [prescale.dev/dashboard](https://prescale.dev/dashboard).** Each site
  gets a capacity timeline that names the commit where a regression started. Runs are private
  until you share one.
- **Launch Guard.** Pick a launch (Product Hunt, Hacker News, Black Friday) and get GO, RISKY
  or NO-GO, with the fix when it isn't GO. Sign off a GO and add a live README badge that
  turns red if capacity drops.
- **Capacity as traffic.** Every verdict says what "survives ~N users" means in requests per
  second and roughly how many real visitors that is.
- **One-line install, one-click login.** No Python setup, and `prescale login` is approved
  in your browser.
- **Still local first.** Nothing is uploaded unless you ask, and
  `prescale upload --dry-run` shows the exact payload first.

### Added
- **One-line install**, no Python setup: `curl -fsSL https://prescale.dev/install | sh`
  (macOS, Linux) or `irm https://prescale.dev/install.ps1 | iex` (Windows). Installs into
  its own environment with uv. `pip install prescale` still works.
- **`prescale login` / `logout`**: connect to your dashboard by approving the login in your
  browser, no token to copy (`--no-browser` prints the link; over SSH it does by default).
  `--paste` takes a token from Connect instead, `--token` for scripts. The token is saved
  readable only by you. `PRESCALE_TOKEN` / `PRESCALE_URL` for CI.
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
- **Capacity as traffic:** every verdict now says what "survives ~N users" means in load:
  requests per second at the highest stage that held, and a rough real-visitor equivalent
  (assuming one request per visitor every 10s). In the readiness report, `compare` and the PR
  comment (with the baseline's figure alongside).
- **PreScale's bars in text** (`░` → `▒` → `█`, `┆` for a threshold): the load-ramp and
  per-route tables gain a p95 bar toward the latency wall (live and final), the readiness
  panel shows how far up the ramp you got (and capacity vs a launch's peak), `compare` and
  `compare --md` draw old vs new, and the PR comment draws the baseline vs this deploy plus
  the routes at the breaking stage.
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
