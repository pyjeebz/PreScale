"""Logic for the PreScale MCP server: host allowlisting, result summarization,
and the async tool implementations.

This module deliberately imports no `mcp` package, so it's fully unit-testable
without the optional `prescale[mcp]` extra installed. The thin FastMCP wiring
lives in `mcp_server.py`.
"""

from __future__ import annotations

from urllib.parse import urlparse

import httpx

from prescale_cli.audit import run_audit
from prescale_cli.loadtest import analyze, build_targets, default_levels, run_loadtest
from prescale_cli.result import build_result, list_results, load_result, write_result

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

# Conservative defaults for unattended (agent) use.
MCP_DEFAULT_MAX_USERS = 100
MCP_DEFAULT_STAGE_SECONDS = 3.0
MCP_DEFAULT_MAX_RPS = 200.0  # applied to non-local targets only


class HostNotAllowedError(Exception):
    """A load_test target host is neither local nor allowlisted."""


def parse_allow(value: str | None) -> set[str]:
    """Parse a comma-separated host allowlist (e.g. PRESCALE_MCP_ALLOW)."""
    if not value:
        return set()
    return {h.strip().lower() for h in value.split(",") if h.strip()}


def host_allowed(host: str, allow: set[str]) -> bool:
    """Local hosts are always allowed; others only if listed (or `*`)."""
    host = (host or "").lower()
    return host in _LOCAL_HOSTS or "*" in allow or host in allow


def summarize_result(result: dict) -> dict:
    """A compact, token-lean projection of a Result for an agent tool reply."""
    v = result["verdict"]
    conf = v.get("confidence") or {}
    return {
        "id": result["id"],
        "target": result["target"]["url"],
        "verdict": _verdict_line(v, conf),
        "survives_users": v["survives_users"],
        "survives_range": [conf.get("survives_low"), conf.get("survives_high")],
        "stable": conf.get("stable"),
        "max_tested": v["max_tested"],
        "onset_users": v["onset_users"],
        "onset_reason": v["onset_reason"],
        "culprit_route": v["culprit_route"],
        "bottleneck": v["bottleneck"],
        "peak_rps": v["peak_rps"],
        "saturated": v["saturated"],
        "warning": result.get("warning"),
        "hint": "Call get_run(id) for the full per-level / per-route breakdown.",
    }


def _verdict_line(v: dict, conf: dict) -> str:
    if v["onset_users"] is None:
        return f"Held up through {v['max_tested']} concurrent users (the most tested)."
    lo, hi = conf.get("survives_low"), conf.get("survives_high")
    band = ""
    if lo is not None and hi is not None and not (lo == v["survives_users"] == hi):
        band = f" ({lo}-{hi})"
    line = f"Survives ~{v['survives_users']}{band} concurrent users."
    if v["bottleneck"]:
        line += f" First failure: {v['culprit_route'] or 'the app'} - {v['bottleneck']}"
    return line


async def run_summary(url: str, *, allow: set[str], max_users: int = MCP_DEFAULT_MAX_USERS,
                      paths: tuple[str, ...] = (),
                      stage_seconds: float = MCP_DEFAULT_STAGE_SECONDS,
                      max_rps: float | None = None, store=None,
                      transport: httpx.AsyncBaseTransport | None = None) -> dict:
    """Load-test `url` (host must be local or allowlisted), persist the Result,
    and return a compact summary. Non-local targets get a default rate ceiling."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"'{url}' is not a URL (expected e.g. http://localhost:8000).")
    host = (parsed.hostname or "").lower()
    if not host_allowed(host, allow):
        raise HostNotAllowedError(
            f"Refusing to load-test non-local host '{host}'. Set "
            f"PRESCALE_MCP_ALLOW={host} (or pass --allow {host} to `prescale mcp`) "
            "if you own it."
        )
    if max_rps is None and host not in _LOCAL_HOSTS:
        max_rps = MCP_DEFAULT_MAX_RPS  # safety ceiling for non-local hosts

    targets = build_targets(url, paths=tuple(paths))
    levels = default_levels(max_users)
    stages, warning = await run_loadtest(
        targets, levels=levels, stage_seconds=stage_seconds, max_rps=max_rps,
        transport=transport,
    )
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02,
                     rate_capped=max_rps is not None)
    config = {
        "method": "GET", "max_users": max_users, "stage_seconds": stage_seconds,
        "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": max_rps,
        "warmup": True, "repeat": 1, "think_time_s": 0.0,
    }
    result = build_result(report, url=url, targets=targets, config=config, warning=warning)
    write_result(result, store=store)
    return summarize_result(result)


async def audit_summary(url: str) -> dict:
    """Static scaling-hygiene findings for `url` (no load)."""
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"'{url}' is not a URL (expected e.g. https://myapp.com).")
    findings = await run_audit(url)
    return {
        "target": url,
        "findings": [
            {"name": f.name, "status": f.status, "detail": f.detail, "fix": f.fix}
            for f in findings
        ],
    }


def list_runs(store=None) -> list[dict]:
    """Saved-run summaries, newest first."""
    return list_results(store=store)


def get_run(run_id: str, store=None) -> dict:
    """The full saved Result for a run id (or unique prefix)."""
    return load_result(run_id, store=store)
