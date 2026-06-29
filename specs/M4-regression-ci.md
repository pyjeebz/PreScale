# M4 — Regression + CI

Status: **spec / not started**
Depends on: M0 (saved Results with `environment.git_commit/branch`), M1 (confidence
bands — used for regression *confidence*).

## Goal

Turn PreScale from a one-off probe into something a team keeps installed: **catch
capacity regressions** ("breaking point dropped 200 → 90 since main") and **gate
deploys** in CI. It rides on the `.prescale/runs/` history and the commit captured
in each Result.

## Pieces

### 1. Absolute gate — `--fail-under N`
`prescale run <url> --fail-under N` (and `investigate`) exits **non-zero** when
`survives_users < N`. The simplest CI gate: "fail the build if we can't hold N
concurrent users." No history needed.

### 2. `prescale compare [NEW] [OLD]`
Diff two saved Results (each operand is a run **id**, a unique prefix, or a Result
**`.json` path** — `load_result` already handles all three):
- No args → the two most recent runs (`NEW` = latest, `OLD` = previous).
- `--baseline PATH` → use that as `OLD` (overrides the positional).

Reports the **capacity delta** (`survives_users`, `peak_rps`, onset), the commits
behind each run, and per-route changes. `--json` / `--markdown` (PR-comment-ready).

### 3. Regression detection — `compare --fail-on-regression`
Flag a regression when `survives_users` dropped by more than
`--regression-threshold` (default **0.2** = 20%). **Confidence comes from M1's
bands:** a regression is *confident* when the bands don't overlap
(`new.survives_high < old.survives_low`) — otherwise it's flagged as possibly
noise. `--fail-on-regression` exits non-zero on a regression.

### 4. CI: a documented GitHub Actions workflow
Two copy-paste patterns (README + an example workflow file):
- **Gate:** `prescale run $STAGING --fail-under 100`.
- **Regression vs a committed baseline:** a Result JSON committed on `main`
  (`prescale run … --json > prescale-baseline.json`); PRs run and
  `prescale compare <new> --baseline prescale-baseline.json --fail-on-regression
  --markdown`, posting the markdown via `gh pr comment`.

The baseline is just a **Result file** — no new format, and committing it is the
explicit opt-in that fits the local-first / no-silent-ingest principle.

## Schema
No new Result fields (compare is a derived view). `config` gains an optional
`fail_under` for record-keeping (additive; `schema_version` stays 1).

## Structure
- `compare.py` — `compare_results(old, new, *, threshold) -> dict` (pure) + a small
  loader that resolves an operand to a Result (id / prefix / path) and to defaults.
- `commands/compare.py` — the command (resolve operands, render table / `--json` /
  `--markdown`, exit code).
- `run` / `investigate` gain `--fail-under`.

## Build sub-steps
1. **M4.1** — `--fail-under N` on `run` + `investigate` (+ `config.fail_under`).
2. **M4.2** — `compare_results` (pure) + `prescale compare` (table / `--json` /
   `--markdown`; default latest-vs-previous; `--baseline`).
3. **M4.3** — `--fail-on-regression` / `--regression-threshold`, band-overlap
   confidence, non-zero exit.
4. **M4.4** — example GitHub Actions workflow(s) + README "CI" section.
5. **M4.5** — tests.

## Tests
- `--fail-under`: exit 0 when survives ≥ N, exit non-zero when below (via the
  `transport=` seam or a saved Result).
- `compare_results`: delta math; regression at/over threshold; confident vs
  noisy (band overlap); improvement (negative regression) not flagged.
- `compare` command: defaults to latest-vs-previous; `--baseline` path; `--json`
  and `--markdown` shapes; `--fail-on-regression` exit code.

## Decisions (override any)
1. **Regression = >20% drop in `survives_users`, with M1-band overlap deciding
   confidence** (confident when bands don't overlap). Threshold tunable.
2. **Baseline = a committed Result JSON** (reuse the existing format; explicit
   opt-in), not a new baseline store or silent upload.
3. **CI = documented workflow + `compare --markdown`**, not a packaged
   marketplace action (keep it copy-paste and dependency-free).
4. **Two gates:** absolute (`run --fail-under N`) and relative
   (`compare --fail-on-regression`).
