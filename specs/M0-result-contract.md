# M0 — Result contract + persistence

Status: **spec / not started**
Depends on: nothing. This is the foundation for M2 (MCP), M3 (investigate),
M4 (regression + CI).

## Goal

Give PreScale a single, versioned, on-disk **result** — so a run can be stored,
re-rendered, diffed, and consumed by other tools. Today every run is computed,
printed, and thrown away, and `--json` is an ad-hoc shape with no version.

### The headline

After M0, one envelope is the same everywhere:

```
prescale run --json   ==   .prescale/runs/<id>.json   ==   prescale show --json   ==   what MCP returns
```

One `Result` object, written once, rendered everywhere. No drift between what you
see live, what gets stored, and what an agent reads.

## In scope

- A versioned `Result` envelope (schema_version 1) unifying run metadata, config,
  verdict, and per-stage/per-route measurements.
- Persistence to `.prescale/runs/<id>.json` on every `prescale run`.
- `prescale history` and `prescale show [id]`.
- A published JSON Schema file + `prescale schema` to print it.
- Refactor so `run`, `show`, `--html`, and `--json` all render from the same
  `Result`.

## Out of scope (later milestones, but designed-for here)

- Confidence band / variance fields — **M1**. Additive; will not bump the schema.
- Persisting `audit` results — later. The envelope carries `kind` so audit slots
  in without a schema change.
- Regression/diff between runs — **M4**. We capture `environment.git_commit` now
  so M4 has what it needs.
- MCP exposure — **M2**. The `Result` dict *is* the MCP return shape.

---

## The `Result` envelope (schema_version 1)

```jsonc
{
  "schema_version": 1,
  "kind": "run",                         // "run" now; "audit" reserved
  "id": "20260628T140532Z-a1b2c3",       // = filename stem, sorts chronologically
  "tool_version": "0.1.0",               // prescale_cli.__version__ at write time
  "created_at": "2026-06-28T14:05:32Z",  // UTC, ISO-8601

  "target": {
    "url": "https://staging.myapp.com",
    "host": "staging.myapp.com",
    "routes": ["/", "/api/search", "/pricing"]
  },

  "config": {
    "method": "GET",
    "max_users": 200,
    "stage_seconds": 5.0,
    "latency_wall_s": 2.0,
    "error_threshold": 0.02,
    "max_rps": null
  },

  "verdict": {
    "survives_users": 90,
    "max_tested": 200,
    "onset_users": 150,
    "onset_reason": "errors",            // "errors" | "latency" | null
    "culprit_route": "/api/search",
    "bottleneck": "Server returned 5xx under load — likely an unhandled overload…",
    "saturated": true,
    "saturation_users": 100,
    "peak_rps": 610.0,
    "marginal": false
  },

  "stages": [
    {
      "users": 10, "rps": 520.0,
      "p50_ms": 28, "p95_ms": 31, "p99_ms": 44,
      "error_rate": 0.0, "errors": 0, "total": 2600,
      "routes": {
        "/api/search": {
          "total": 866, "errors": 0, "error_rate": 0.0,
          "p50_ms": 30, "p95_ms": 33, "p99_ms": 47
        }
      }
    }
  ],

  "warning": null,

  "environment": {
    "git_commit": "1c0e2c3",             // best-effort; null outside a git repo
    "git_branch": "main"                 // best-effort; null if undetectable
  }
}
```

### What changed vs today's `_report_to_dict`

- **Separated concerns:** `config` (inputs) / `verdict` (conclusions) / `stages`
  (measurements) instead of one flat blob. `latency_wall` moves into
  `config.latency_wall_s`.
- **Added envelope:** `schema_version`, `kind`, `id`, `tool_version`,
  `created_at`, `target`, `environment`.
- **Richer per-route:** `p50_ms` + `p99_ms` added (today only `p95_ms`).
- This is a breaking change to the current ad-hoc `--json` shape. That's fine
  pre-1.0 — `--json` had no stability promise, and now it does.

## Schema versioning rules

- `schema_version` is an integer, starts at **1**.
- **Additive** changes (new optional fields) do **not** bump it (so M1's
  confidence fields are free).
- **Breaking** changes (rename/remove/retype) bump it.
- Loaders are **lenient**: an unknown-but-newer `schema_version` produces a
  warning, not a crash; a missing field renders as "n/a".

---

## Storage layout

```
.prescale/
└── runs/
    ├── 20260628T140532Z-a1b2c3.json
    ├── 20260628T141090Z-9f0e1d.json
    └── …
```

- **Location:** `.prescale/` in the current working directory. Override with
  `PRESCALE_HOME` env or `--store DIR`.
- **ID / filename:** `<UTC-compact-timestamp>-<6 hex>`. Timestamp gives
  chronological lexical sort; hex suffix avoids same-second collisions. `id` ==
  filename stem.
- **"Latest"** is derived by sorting filenames descending — no symlink, no
  pointer file to keep in sync (Windows-safe).
- `.prescale/` is **git-ignored by default** (local artifacts, may contain your
  infra's URLs). Add it to the repo `.gitignore`.

---

## New module: `cli/src/prescale_cli/result.py`

Owns the envelope and the store. `RunReport` (the in-memory analysis object)
stays as is; `Result` is the serialized form.

```python
def build_result(report: RunReport, *, url: str, targets: list[str],
                 config: dict, warning: str | None) -> dict: ...
    # RunReport + run inputs  ->  the Result dict above (incl. id, timestamps,
    # best-effort git_commit/git_branch).

def write_result(result: dict, *, store: Path | None = None) -> Path: ...
    # Writes .prescale/runs/<id>.json. Returns the path.

def load_result(id_or_path: str, *, store: Path | None = None) -> dict: ...
    # Accepts a full id, a unique id prefix, or a path. Raises on
    # missing/ambiguous. Warns (does not raise) on newer schema_version.

def list_results(*, store: Path | None = None) -> list[dict]: ...
    # Cheap metadata for `history`, newest-first:
    # {id, created_at, host, kind, survives_users, onset_users, onset_reason}.

def store_dir() -> Path: ...
    # Resolves --store / PRESCALE_HOME / default ".prescale".

def latest_id(*, store=None) -> str | None: ...
```

Git capture is best-effort (`git rev-parse --short HEAD` / `--abbrev-ref HEAD`
with a short timeout); any failure → `null`. Never block a run on git.

## Rendering unification

Today `run.py` renders from a live `RunReport` (which holds raw latency lists)
and serializes separately — two code paths that can drift. M0 makes the `Result`
dict the single source for all rendering:

```
run_loadtest -> analyze -> RunReport
                              │
                  build_result(...) -> Result(dict)
                              ├─ write_result            (-> .prescale/runs/<id>.json)
                              ├─ render_terminal(Result) (was run.py:_render/_render_routes)
                              ├─ render_html(Result)     (report.py:render_html)
                              └─ --json: print(Result)

show -> load_result(id) -> Result(dict) -> same render_terminal / render_html / --json
```

- Move `_render` / `_render_routes` into a shared `render.py` (or keep in `run.py`
  but have them take the `Result` dict, not `RunReport`). They only ever display
  the summarized numbers (users/rps/p50/p95/p99/error_rate), all of which live in
  `Result.stages` — so `show` re-renders perfectly **without** needing the raw
  per-request latencies (which we don't persist).
- `report.py:render_html` is refactored to consume `Result` instead of
  `RunReport`. Same output, fed from the envelope.

This guarantees `run` output and `show` output are byte-identical for the same
result.

---

## Command changes

### `prescale run` (modified)

- Persists a `Result` to `.prescale/runs/<id>.json` by default; prints the saved
  path in the terminal footer (next to the existing `--html` line).
- New flags:
  - `--no-save` — run without writing a result (ephemeral / CI / privacy one-off).
  - `--store DIR` — override the store location.
- `--json` now emits the full `Result` envelope (identical to the stored file).

### `prescale history` (new)

```
prescale history [-n N] [--json] [--store DIR]
```

Lists stored runs newest-first as a rich table: id (short), when (relative),
host, verdict one-liner ("survives ~90"), onset. `--json` emits the
`list_results` array. Empty store → a friendly "no runs yet" hint.

### `prescale show` (new)

```
prescale show [ID] [--json] [--html PATH] [--store DIR]
```

- No `ID` → latest run.
- `ID` accepts a full id or a unique prefix; ambiguous/missing → clear error.
- Default: re-render the stored result to the terminal (via `render_terminal`).
- `--json` → print the stored envelope. `--html PATH` → re-render HTML.

### `prescale schema` (new, small)

```
prescale schema            # prints the JSON Schema to stdout
```

Emits the packaged `result.schema.json` so MCP/CI consumers can validate.

---

## JSON Schema artifact

- `cli/src/prescale_cli/schema/result.schema.json` — JSON Schema (draft 2020-12)
  describing the envelope. Shipped as package data (add to
  `setuptools.package-data` / `MANIFEST`).
- `load_result` does a **lenient** check (presence of `schema_version`, known
  top-level keys) — warn, don't crash. Full strict validation is the consumer's
  choice via the published schema.

## Privacy (per locked decision)

Results stay on the user's machine. The envelope may contain their infra's URLs
and route paths — fine, because nothing is uploaded. No telemetry. `history` and
`show` are local reads. `.prescale/` is git-ignored so results aren't committed by
accident. (A future M4 may let a team *opt in* to committing baselines.)

---

## Tests (`cli/tests/`)

- `build_result` produces a schema-1 envelope; `write_result` → `load_result`
  round-trips equal.
- ID/filename format is valid and sorts chronologically; same-second writes don't
  collide.
- `load_result` resolves full id, unique prefix; errors on missing/ambiguous;
  warns (no raise) on a higher `schema_version`.
- `latest_id` / `show` (no arg) pick the newest.
- `history` lists newest-first; empty store handled.
- **Render parity:** a fresh run and the reloaded result render identical terminal
  output and identical `--json`.
- Git capture degrades to `null` outside a repo.

## Build sub-steps (suggested order)

1. **M0.1** `result.py` (build/write/load/list/store + id + git capture). Wire
   `run` to build + persist; add `--no-save` / `--store`. `--json` emits the
   envelope.
2. **M0.2** Unify rendering: `render_terminal(Result)` + `render_html(Result)`;
   `run` renders from the `Result`.
3. **M0.3** `prescale history` + `prescale show` (register in `main.py`).
4. **M0.4** `result.schema.json` + `prescale schema` + lenient load check.
5. **M0.5** Tests, `.gitignore` entry, README note on `.prescale/`.

## Files touched

- **new** `cli/src/prescale_cli/result.py`
- **new** `cli/src/prescale_cli/render.py` (or fold into `run.py`)
- **new** `cli/src/prescale_cli/schema/result.schema.json`
- **new** `cli/src/prescale_cli/commands/history.py`, `commands/show.py`
- **edit** `cli/src/prescale_cli/commands/run.py` (build/persist/render; new flags)
- **edit** `cli/src/prescale_cli/report.py` (`render_html` consumes `Result`)
- **edit** `cli/src/prescale_cli/main.py` (register `history`, `show`, `schema`)
- **edit** `pyproject.toml` (package-data for the schema)
- **edit** `.gitignore` (`.prescale/`)
- **new** `cli/tests/test_result.py`, `cli/tests/test_history_show.py`

---

## Decisions I made (override any of these)

1. **Store = CWD `.prescale/`** (+ `PRESCALE_HOME` / `--store`). Simple and
   predictable. Alternative: walk up to the git root so history is per-repo —
   deferred to M4 if wanted.
2. **`.prescale/` git-ignored by default.** Results are local artifacts.
3. **Persist `run` only in M0;** envelope is `kind`-ready so `audit` can persist
   later with no schema bump.
4. **`--json` becomes the `Result` envelope** (breaks the current ad-hoc shape).
   Pre-1.0, and it buys one consistent contract everywhere.
5. **Capture `git_commit` / `git_branch` now** (best-effort, local only) so M4
   regression has the commit that moved the number.
