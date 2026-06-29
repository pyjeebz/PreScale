"""`prescale investigate` — active root-cause pass on the culprit route.

After a ramp finds what breaks first, investigate probes that route — baseline
vs loaded latency, a static-vs-dynamic comparison, and error/header forensics —
classifies the bottleneck, and prescribes a fix. Fully local and deterministic;
no LLM. The classifier and remediation map are pure functions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx

from prescale_cli.audit import _CDN_MARKERS, extract_assets
from prescale_cli.loadtest import (
    analyze,
    build_targets,
    default_levels,
    measure_route,
    open_client,
    route_label,
    run_loadtest,
)
from prescale_cli.result import build_result, write_result

_PROBE_SECONDS = 2.0
_SLOW_BASELINE_MS = 800.0   # >= 0.8s at 1 VU => intrinsically slow
_LATENCY_WALL_S = 2.0
_ERROR_THRESHOLD = 0.02


@dataclass
class Probes:
    culprit_route: str
    onset_users: int
    baseline_p95_ms: float | None = None
    loaded_p95_ms: float | None = None
    static_route: str | None = None
    static_ok: bool | None = None
    throughput_plateaued: bool = False
    server: str | None = None
    cdn: str | None = None
    error_kinds: dict = field(default_factory=dict)
    status_counts: dict = field(default_factory=dict)


@dataclass
class Diagnosis:
    bottleneck_class: str
    confidence: str          # "high" | "medium" | "low"
    summary: str
    evidence: list[str]


def _evidence(p: Probes) -> list[str]:
    ev: list[str] = []
    if p.baseline_p95_ms is not None and p.loaded_p95_ms is not None:
        ev.append(f"culprit p95 {p.baseline_p95_ms:.0f}ms at 1 user vs "
                  f"{p.loaded_p95_ms:.0f}ms at {p.onset_users} users")
    if p.static_route is not None and p.static_ok is not None:
        held = "held" if p.static_ok else "also degraded"
        ev.append(f"static {p.static_route} {held} at {p.onset_users} users")
    if p.error_kinds:
        worst = sorted(p.error_kinds.items(), key=lambda kv: -kv[1])
        ev.append("errors under load: " + ", ".join(f"{k} ({v})" for k, v in worst))
    if p.throughput_plateaued:
        ev.append("throughput plateaued while users kept rising")
    if p.server:
        ev.append(f"server: {p.server}")
    return ev


def classify(p: Probes) -> Diagnosis:
    """Map probe evidence to a bottleneck class (first match wins)."""
    ev = _evidence(p)
    kinds = p.error_kinds
    dominant = max(kinds, key=kinds.get) if kinds else None
    has_503 = 503 in p.status_counts
    has_other_5xx = any(c >= 500 and c != 503 for c in p.status_counts)

    if dominant == "rate limited (429)":
        return Diagnosis("rate_limited", "high",
                         "A rate limiter (429) is throttling requests under load.", ev)
    if has_503:
        return Diagnosis("overload_shedding", "high",
                         "503s under load — a proxy or load balancer is shedding load.", ev)
    if dominant in ("connection refused", "network"):
        conf = "high" if p.static_ok is False else "medium"
        return Diagnosis("connection_ceiling", conf,
                         "Connections were refused under load — a server connection / "
                         "accept ceiling.", ev)
    if dominant == "timeout":
        if p.static_ok is False:
            return Diagnosis("connection_ceiling", "medium",
                             "Timeouts with static assets degrading too — saturated at "
                             "the connection level.", ev)
        return Diagnosis("connection_pool", "medium",
                         "Requests timed out while infra held — a backend pool or "
                         "downstream dependency is blocking.", ev)
    if has_other_5xx:
        if p.static_ok is True:
            return Diagnosis("connection_pool", "high",
                             "5xx under load while static assets held — the app/backend "
                             "is the wall (often a DB or upstream pool).", ev)
        return Diagnosis("connection_pool", "medium",
                         "5xx under load — an unhandled overload in the app "
                         "(DB pool, worker queue).", ev)
    # latency-only (no error threshold crossed first)
    if p.baseline_p95_ms is not None and p.baseline_p95_ms >= _SLOW_BASELINE_MS:
        return Diagnosis("slow_endpoint", "high",
                         "Slow even at 1 user — an intrinsically slow endpoint "
                         "(slow query / N+1 / heavy compute).", ev)
    if p.throughput_plateaued:
        return Diagnosis("concurrency_ceiling", "high",
                         "Latency climbs while throughput is flat — a concurrency ceiling "
                         "(requests queue once capacity maxes out).", ev)
    if (p.baseline_p95_ms is not None and p.loaded_p95_ms is not None
            and p.loaded_p95_ms >= 3 * max(p.baseline_p95_ms, 1.0)):
        return Diagnosis("concurrency_ceiling", "medium",
                         "Latency balloons under load from a fast baseline — likely "
                         "contention / concurrency.", ev)
    return Diagnosis("unknown", "low",
                     "The target degraded under load, but the signals don't point to a "
                     "single clear cause.", ev)


_REMEDIATION = {
    "rate_limited": [
        "A 429 limiter kicked in — confirm it's intentional.",
        "If it's yours, raise the limit (or exempt internal/health traffic) for spikes.",
    ],
    "overload_shedding": [
        "A proxy/LB is shedding load (503). Add origin capacity or enable autoscaling.",
        "Tune the LB queue/timeout so it sheds later.",
    ],
    "connection_ceiling": [
        "Raise the server's connection/accept limit (e.g. nginx worker_connections, "
        "the OS somaxconn/backlog).",
        "Add instances behind a load balancer to spread connections.",
    ],
    "connection_pool": [
        "Increase the DB/upstream connection-pool size.",
        "Add a pooler (e.g. pgbouncer) and check the pool checkout timeout.",
        "Make sure connections are released promptly under load (no leaks).",
    ],
    "concurrency_ceiling": [
        "Raise the worker/thread count — extra users are just queuing.",
        "Check for a single-threaded server or a global lock / serialized resource.",
        "Scale out (more instances) if one process can't go wider.",
    ],
    "slow_endpoint": [
        "Profile the route — it's slow even at 1 user (likely a slow query or N+1).",
        "Add an index, a cache, or pagination; move heavy work off the request path.",
    ],
    "unknown": [
        "Re-run with --repeat 3 for a tighter read, and inspect the per-route breakdown.",
        "Check app logs and DB/connection metrics around the onset level.",
    ],
}

_SERVER_HINTS = {
    "gunicorn": "gunicorn detected — increase --workers (and/or --threads).",
    "uvicorn": "uvicorn detected — run multiple workers "
               "(gunicorn -k uvicorn.workers.UvicornWorker -w N).",
    "nginx": "nginx in front — check worker_connections and upstream keepalive.",
    "puma": "puma detected — raise the thread pool / worker count.",
}

_CONN_CLASSES = ("concurrency_ceiling", "connection_ceiling", "connection_pool")


def remediate(diag: Diagnosis, stack: dict) -> list[str]:
    """Class-appropriate fixes, enriched with detected-stack hints."""
    lines = list(_REMEDIATION.get(diag.bottleneck_class, _REMEDIATION["unknown"]))
    server = (stack.get("server") or "").lower()
    if diag.bottleneck_class in _CONN_CLASSES:
        for marker, hint in _SERVER_HINTS.items():
            if marker in server:
                lines.append(hint)
                break
    if stack.get("cdn") and diag.bottleneck_class == "connection_ceiling":
        lines.append(f"{stack['cdn']} is in front — the ceiling is likely at your origin.")
    return lines


async def _headers(client, url):
    try:
        r = await client.get(url)
    except httpx.HTTPError:
        return None, None
    h = {k.lower(): v for k, v in r.headers.items()}
    cdn = next((label for marker, label in _CDN_MARKERS.items() if marker in h), None)
    if not cdn and "cloudflare" in h.get("server", "").lower():
        cdn = "Cloudflare"
    return h.get("server"), cdn


async def _static_probe(client, base_url, onset):
    try:
        page = await client.get(base_url)
        assets = extract_assets(page.text, base_url)
    except httpx.HTTPError:
        assets = []
    if not assets:
        return None, None
    stage = await measure_route(client, assets[0], users=onset, seconds=_PROBE_SECONDS)
    ok = stage.error_rate < _ERROR_THRESHOLD and stage.pct(0.95) < _LATENCY_WALL_S
    return route_label(assets[0]), ok


async def gather_probes(base_url, report, stages, targets, *, transport=None) -> Probes:
    """Run the active probes on the culprit route + a static reference."""
    culprit = report.culprit_route
    onset = report.onset_users
    culprit_url = next((t for t in targets if route_label(t) == culprit), base_url)
    onset_stage = next((s for s in stages if s.users == onset), None)
    cstat = onset_stage.routes.get(culprit) if onset_stage else None
    p = Probes(
        culprit_route=culprit, onset_users=onset,
        loaded_p95_ms=(cstat.pct(0.95) * 1000) if (cstat and cstat.latencies) else None,
        throughput_plateaued=report.saturated,
        error_kinds=dict(cstat.error_kinds) if cstat else {},
        status_counts=dict(cstat.status_counts) if cstat else {},
    )
    async with open_client(max_conns=onset + 10, transport=transport) as client:
        base = await measure_route(client, culprit_url, users=1, seconds=_PROBE_SECONDS)
        p.baseline_p95_ms = base.pct(0.95) * 1000 if base.routes else None
        p.server, p.cdn = await _headers(client, culprit_url)
        p.static_route, p.static_ok = await _static_probe(client, base_url, onset)
    return p


async def investigate(url, *, max_users=200, paths=(), stage_seconds=5.0,
                      max_rps=None, store=None, transport=None, progress_cb=None) -> dict:
    """Ramp to find the culprit, probe it, and attach a diagnosis to the Result."""
    targets = build_targets(url, paths=tuple(paths))
    levels = default_levels(max_users)
    stages, warning = await run_loadtest(
        targets, levels=levels, stage_seconds=stage_seconds, max_rps=max_rps,
        transport=transport, progress_cb=progress_cb)
    report = analyze(stages, latency_wall=_LATENCY_WALL_S,
                     error_threshold=_ERROR_THRESHOLD, rate_capped=max_rps is not None)
    config = {"method": "GET", "max_users": max_users, "stage_seconds": stage_seconds,
              "latency_wall_s": _LATENCY_WALL_S, "error_threshold": _ERROR_THRESHOLD,
              "max_rps": max_rps, "warmup": True, "repeat": 1, "think_time_s": 0.0}
    result = build_result(report, url=url, targets=targets, config=config, warning=warning)

    if report.onset_users is not None and report.culprit_route:
        probes = await gather_probes(url, report, stages, targets, transport=transport)
        diag = classify(probes)
        stack = {k: v for k, v in {"server": probes.server, "cdn": probes.cdn}.items() if v}
        result["investigation"] = {
            "culprit_route": report.culprit_route,
            "bottleneck_class": diag.bottleneck_class,
            "confidence": diag.confidence,
            "summary": diag.summary,
            "evidence": diag.evidence,
            "remediation": remediate(diag, stack),
            "stack": stack,
        }

    write_result(result, store=store)
    return result
