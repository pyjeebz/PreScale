"""Self-contained launch-readiness load engine for `prescale run`.

Ramps virtual users against a single URL, captures latency/error signals at
each level, and finds the point where the target starts to fail. Pure-Python
on top of httpx + asyncio so it needs no external load tool and no server.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import httpx


class LoadError(Exception):
    """Raised when the target can't be reached at all (nothing to test)."""


# Concurrency levels we step through. Filtered against --max-users at runtime.
_LADDER = [1, 2, 5, 10, 20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000]


def default_levels(max_users: int) -> list[int]:
    """Build the ramp ladder, capped at and ending exactly at max_users."""
    levels = [u for u in _LADDER if u < max_users]
    levels.append(max_users)
    return levels


def percentile(sorted_vals: list[float], p: float) -> float:
    """Linear-interpolated percentile. `p` in [0, 1], `sorted_vals` ascending."""
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


@dataclass
class StageResult:
    """Aggregated outcome of holding `users` concurrent VUs for `duration`s."""

    users: int
    duration: float
    total: int = 0
    errors: int = 0
    latencies: list[float] = field(default_factory=list)  # successful responses, seconds
    status_counts: dict[int, int] = field(default_factory=dict)
    error_kinds: dict[str, int] = field(default_factory=dict)

    @property
    def rps(self) -> float:
        return self.total / self.duration if self.duration else 0.0

    @property
    def error_rate(self) -> float:
        return self.errors / self.total if self.total else 0.0

    def pct(self, p: float) -> float:
        return percentile(sorted(self.latencies), p)


@dataclass
class RunReport:
    stages: list[StageResult]
    survives_users: int
    max_tested: int
    onset_users: int | None = None
    onset_reason: str | None = None  # "errors" | "latency"
    bottleneck: str | None = None
    latency_wall: float = 2.0


class _Sink:
    """Per-stage accumulator. A 5xx/429 is a failure; everything else with a
    status code counts toward latency."""

    def __init__(self) -> None:
        self.total = 0
        self.errors = 0
        self.latencies: list[float] = []
        self.status_counts: dict[int, int] = {}
        self.error_kinds: dict[str, int] = {}

    def _kind(self, k: str) -> None:
        self.error_kinds[k] = self.error_kinds.get(k, 0) + 1

    def record_response(self, status: int, latency: float) -> None:
        self.total += 1
        self.status_counts[status] = self.status_counts.get(status, 0) + 1
        if status >= 500:
            self.errors += 1
            self._kind("5xx")
        elif status == 429:
            self.errors += 1
            self._kind("rate limited (429)")
        else:
            self.latencies.append(latency)

    def record_error(self, kind: str) -> None:
        self.total += 1
        self.errors += 1
        self._kind(kind)

    def to_stage(self, users: int, duration: float) -> StageResult:
        return StageResult(
            users=users,
            duration=duration,
            total=self.total,
            errors=self.errors,
            latencies=self.latencies,
            status_counts=self.status_counts,
            error_kinds=self.error_kinds,
        )


async def _worker(client: httpx.AsyncClient, url: str, method: str,
                  deadline: float, sink: _Sink) -> None:
    """Closed-loop VU: fire requests back-to-back until the stage deadline."""
    loop = asyncio.get_running_loop()
    while loop.time() < deadline:
        start = time.perf_counter()
        try:
            resp = await client.request(method, url)
            sink.record_response(resp.status_code, time.perf_counter() - start)
        except httpx.TimeoutException:
            sink.record_error("timeout")
        except httpx.ConnectError:
            sink.record_error("connection refused")
        except httpx.HTTPError:
            sink.record_error("network")


async def _run_stage(client: httpx.AsyncClient, url: str, method: str,
                     users: int, duration: float) -> StageResult:
    sink = _Sink()
    deadline = asyncio.get_running_loop().time() + duration
    await asyncio.gather(
        *(_worker(client, url, method, deadline, sink) for _ in range(users))
    )
    return sink.to_stage(users, duration)


async def run_loadtest(
    url: str,
    *,
    levels: list[int],
    stage_seconds: float,
    method: str = "GET",
    timeout: float = 10.0,
    hard_stop_rate: float = 0.5,
    progress_cb=None,
) -> tuple[list[StageResult], str | None]:
    """Preflight the URL, then ramp through `levels`. Stops early once a stage
    is more than `hard_stop_rate` failed. Returns (stages, warning)."""
    max_conns = max(levels) + 50
    limits = httpx.Limits(max_connections=max_conns, max_keepalive_connections=max_conns)
    warning: str | None = None

    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, follow_redirects=True
    ) as client:
        try:
            preflight = await client.request(method, url)
        except httpx.HTTPError as exc:
            raise LoadError(f"Couldn't reach {url}: {exc}") from exc
        if preflight.status_code >= 400:
            warning = (
                f"First request returned HTTP {preflight.status_code} — "
                "results may reflect a broken endpoint, not a load limit."
            )

        stages: list[StageResult] = []
        for users in levels:
            if progress_cb:
                progress_cb(users)
            stage = await _run_stage(client, url, method, users, stage_seconds)
            stages.append(stage)
            if stage.error_rate >= hard_stop_rate:
                break

    return stages, warning


def _bottleneck_hint(onset: StageResult, reason: str, latency_wall: float) -> str:
    if reason == "latency":
        return (
            f"No errors yet, but p95 crosses {latency_wall:g}s — users feel it "
            "before anything 500s. Often a slow query, N+1, or missing cache."
        )
    kind = max(onset.error_kinds, key=onset.error_kinds.get) if onset.error_kinds else ""
    hints = {
        "5xx": "Server returned 5xx under load — likely an unhandled overload "
               "(DB connection pool, worker queue, or an uncaught error path).",
        "rate limited (429)": "A rate limiter kicked in (429). Fine if intentional; "
                              "otherwise it'll throttle real users during a spike.",
        "timeout": "Requests started timing out — the server is saturated or a "
                   "downstream dependency is blocking.",
        "connection refused": "Connections were refused — you hit a connection or "
                              "worker ceiling (or the process fell over).",
        "network": "Network-level errors under load — connection handling is the wall.",
    }
    return hints.get(kind, "The target started failing under load.")


def analyze(stages: list[StageResult], *, latency_wall: float,
            error_threshold: float) -> RunReport:
    """Find the first level that crosses the error or latency threshold."""
    onset: StageResult | None = None
    reason: str | None = None
    for stage in stages:
        if stage.total and stage.error_rate >= error_threshold:
            onset, reason = stage, "errors"
            break
        if stage.latencies and stage.pct(0.95) >= latency_wall:
            onset, reason = stage, "latency"
            break

    max_tested = stages[-1].users if stages else 0
    if onset is None:
        survives = max_tested
        bottleneck = None
    else:
        idx = stages.index(onset)
        survives = stages[idx - 1].users if idx > 0 else 0
        bottleneck = _bottleneck_hint(onset, reason, latency_wall)

    return RunReport(
        stages=stages,
        survives_users=survives,
        max_tested=max_tested,
        onset_users=onset.users if onset else None,
        onset_reason=reason,
        bottleneck=bottleneck,
        latency_wall=latency_wall,
    )
