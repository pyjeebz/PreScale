"""The PreScale `Result` contract and its on-disk store.

A `Result` is the single, versioned envelope produced by a run: metadata,
config, verdict, and per-stage/per-route measurements. It is written once and
rendered everywhere — `run --json`, `.prescale/runs/<id>.json`, `show`, and
(later) the MCP server all speak this exact shape.

Everything here is local-only: results live under `.prescale/` on the user's
machine and are never uploaded.
"""

from __future__ import annotations

import importlib.resources
import json
import os
import secrets
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from prescale_cli import __version__
from prescale_cli.loadtest import RunReport, StageResult, route_label

SCHEMA_VERSION = 1

_DEFAULT_STORE = ".prescale"
_RUNS_SUBDIR = "runs"


class ResultError(Exception):
    """Base class for store lookup failures."""


class ResultNotFoundError(ResultError):
    """No stored result matched the given id."""


class AmbiguousResultError(ResultError):
    """An id prefix matched more than one stored result."""


# --- building -------------------------------------------------------------

def build_result(report: RunReport, *, url: str, targets: list[str],
                 config: dict, warning: str | None) -> dict:
    """Turn a finished `RunReport` plus its inputs into the `Result` envelope."""
    now = datetime.now(timezone.utc)
    parsed = urlparse(url)
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": "run",
        "id": f"{now.strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}",
        "tool_version": __version__,
        "created_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target": {
            "url": url,
            "host": parsed.hostname or "",
            "routes": [route_label(t) for t in targets],
        },
        "config": config,
        "verdict": {
            "survives_users": report.survives_users,
            "max_tested": report.max_tested,
            "onset_users": report.onset_users,
            "onset_reason": report.onset_reason,
            "culprit_route": report.culprit_route,
            "bottleneck": report.bottleneck,
            "saturated": report.saturated,
            "saturation_users": report.saturation_users,
            "peak_rps": round(report.peak_rps, 1),
            "marginal": report.marginal,
            "confidence": {
                "survives_low": report.survives_low,
                "survives_high": report.survives_high,
                "stable": report.stable,
            },
        },
        "stages": [_stage_dict(s) for s in report.stages],
        "warning": warning,
        "environment": _git_environment(),
    }


def _stage_dict(stage: StageResult) -> dict:
    return {
        "users": stage.users,
        "rps": round(stage.rps, 1),
        "p50_ms": round(stage.pct(0.50) * 1000),
        "p95_ms": round(stage.pct(0.95) * 1000),
        "p99_ms": round(stage.pct(0.99) * 1000),
        "error_rate": round(stage.error_rate, 4),
        "errors": stage.errors,
        "total": stage.total,
        "samples": stage.samples,
        "routes": {
            label: {
                "total": r.total,
                "errors": r.errors,
                "error_rate": round(r.error_rate, 4),
                "rps": round(r.total / stage.duration, 1) if stage.duration else 0.0,
                "p50_ms": round(r.pct(0.50) * 1000),
                "p95_ms": round(r.pct(0.95) * 1000),
                "p99_ms": round(r.pct(0.99) * 1000),
            }
            for label, r in stage.routes.items()
        },
    }


def _git_environment() -> dict:
    return {
        "git_commit": _git("rev-parse", "--short", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
    }


def _git(*args: str) -> str | None:
    """Best-effort `git` read. Any failure (no git, no repo) returns None and
    never blocks a run."""
    try:
        proc = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=2, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# --- store ----------------------------------------------------------------

def store_dir(override: str | Path | None = None) -> Path:
    """Resolve the `.prescale` root: explicit override, else $PRESCALE_HOME,
    else `.prescale` in the current directory."""
    if override is not None:
        return Path(override)
    env = os.environ.get("PRESCALE_HOME")
    return Path(env) if env else Path(_DEFAULT_STORE)


def _runs_dir(store: str | Path | None = None) -> Path:
    return store_dir(store) / _RUNS_SUBDIR


def write_result(result: dict, *, store: str | Path | None = None) -> Path:
    """Write a result to `<store>/runs/<id>.json`, creating dirs as needed."""
    runs = _runs_dir(store)
    runs.mkdir(parents=True, exist_ok=True)
    path = runs / f"{result['id']}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return path


def load_result(id_or_path: str, *, store: str | Path | None = None) -> dict:
    """Load a result by full id, unique id prefix, or path.

    Raises `ResultNotFoundError` / `AmbiguousResultError`. A stored result whose
    `schema_version` is newer than ours is loaded anyway, with a stderr warning.
    """
    direct = Path(id_or_path)
    if direct.suffix == ".json" and direct.exists():
        return _read(direct)

    runs = _runs_dir(store)
    exact = runs / f"{id_or_path}.json"
    if exact.exists():
        return _read(exact)

    matches = sorted(runs.glob(f"{id_or_path}*.json")) if runs.exists() else []
    if not matches:
        raise ResultNotFoundError(f"No saved run matching '{id_or_path}'.")
    if len(matches) > 1:
        raise AmbiguousResultError(
            f"'{id_or_path}' matches {len(matches)} runs — use a longer id."
        )
    return _read(matches[0])


def list_results(*, store: str | Path | None = None) -> list[dict]:
    """Lightweight metadata for every stored result, newest-first."""
    runs = _runs_dir(store)
    if not runs.exists():
        return []
    out: list[dict] = []
    for path in sorted(runs.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        verdict = data.get("verdict", {})
        target = data.get("target", {})
        out.append({
            "id": data.get("id", path.stem),
            "created_at": data.get("created_at"),
            "host": target.get("host"),
            "kind": data.get("kind", "run"),
            "survives_users": verdict.get("survives_users"),
            "onset_users": verdict.get("onset_users"),
            "onset_reason": verdict.get("onset_reason"),
        })
    return out


def latest_id(*, store: str | Path | None = None) -> str | None:
    """The id of the most recent stored result, or None if the store is empty."""
    runs = _runs_dir(store)
    if not runs.exists():
        return None
    files = sorted(runs.glob("*.json"), reverse=True)
    return files[0].stem if files else None


def schema_warning(result: dict) -> str | None:
    """A human message if `result` looks version-incompatible, else None."""
    version = result.get("schema_version")
    if version is None:
        return "saved run has no schema_version; it may be from an incompatible build."
    if isinstance(version, int) and version > SCHEMA_VERSION:
        return (
            f"saved run uses schema_version {version}, newer than this prescale "
            f"(supports {SCHEMA_VERSION}); some fields may not render."
        )
    return None


def schema_json() -> str:
    """The packaged JSON Schema for the Result envelope, as a string."""
    return (importlib.resources.files("prescale_cli.schema")
            .joinpath("result.schema.json").read_text(encoding="utf-8"))


def _read(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    warning = schema_warning(data)
    if warning:
        print(f"warning: {warning}", file=sys.stderr)
    return data
