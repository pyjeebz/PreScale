"""Self-contained launch-readiness load engine for `prescale run`.

Ramps virtual users across one or more routes, captures latency/error signals
per route and per level, and finds where the target starts to fail. Pure
Python on top of httpx + asyncio so it needs no external load tool and no
server.
"""

from __future__ import annotations

import asyncio
import itertools
import math
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse, urlunparse
from urllib.robotparser import RobotFileParser

import httpx

from prescale_cli import __version__


class LoadError(Exception):
    """Raised when the target can't be reached at all (nothing to test)."""


_USER_AGENT = f"prescale/{__version__}"

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


def route_label(url: str) -> str:
    """Short display label for a target URL: its path (+ query), defaulting '/'."""
    parts = urlparse(url)
    label = parts.path or "/"
    if parts.query:
        label = f"{label}?{parts.query}"
    return label


def _normalize(url: str) -> str:
    """Canonical form for de-duping: empty path becomes '/', fragment dropped."""
    u = urlparse(url)
    return urlunparse((u.scheme, u.netloc, u.path or "/", u.params, u.query, ""))


def build_targets(base_url: str, paths=(), extra=()) -> list[str]:
    """De-duplicated, same-origin list of URLs to test: the base URL, plus any
    user paths (joined to the base), plus extras (e.g. sitemap URLs). Cross-origin
    entries are dropped so we only ever hit the host we vetted."""
    base = urlparse(base_url)
    origin = (base.scheme, base.netloc)
    candidates = [base_url, *(urljoin(base_url, p) for p in paths), *extra]
    out: list[str] = []
    seen: set[str] = set()
    for url in candidates:
        u = urlparse(url)
        if (u.scheme, u.netloc) != origin:
            continue
        norm = _normalize(url)
        if norm not in seen:
            seen.add(norm)
            out.append(norm)
    return out


def parse_sitemap(content: str, origin: str) -> list[str]:
    """Extract same-origin <loc> URLs from a sitemap or sitemap index."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return []
    locs: list[str] = []
    for elem in root.iter():
        if elem.tag.rsplit("}", 1)[-1] == "loc" and elem.text:
            url = elem.text.strip()
            if url.startswith(origin):
                locs.append(url)
    return locs


async def discover_sitemap(base_url: str, *, timeout: float = 10.0,
                           cap: int = 20) -> list[str]:
    """Best-effort: fetch sitemap.xml (falling back to robots.txt), follow one
    level of sitemap-index nesting, and return up to `cap` same-origin page URLs."""
    parts = urlparse(base_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    pages: list[str] = []
    nested: list[str] = []

    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
    ) as client:
        async def load(url: str) -> None:
            try:
                resp = await client.get(url)
            except httpx.HTTPError:
                return
            if resp.status_code >= 400:
                return
            for loc in parse_sitemap(resp.text, origin):
                (nested if loc.endswith(".xml") else pages).append(loc)

        await load(f"{origin}/sitemap.xml")
        if not pages and not nested:
            try:
                robots = await client.get(f"{origin}/robots.txt")
            except httpx.HTTPError:
                robots = None
            if robots is not None and robots.status_code < 400:
                for line in robots.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        await load(line.split(":", 1)[1].strip())
        for child in nested[:3]:
            if len(pages) >= cap:
                break
            await load(child)

    out: list[str] = []
    seen: set[str] = set()
    for url in pages:
        if url.endswith(".xml") or url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= cap:
            break
    return out


def disallowed_targets(robots_text: str, targets: list[str], user_agent: str) -> list[str]:
    """Targets that robots.txt disallows for `user_agent` (empty robots = all allowed)."""
    parser = RobotFileParser()
    parser.parse(robots_text.splitlines())
    return [t for t in targets if not parser.can_fetch(user_agent, t)]


async def check_robots(targets: list[str], *, timeout: float = 10.0) -> list[str]:
    """Best-effort: fetch robots.txt and return the disallowed subset of targets.
    Never raises; a missing or unreadable robots.txt means everything is allowed."""
    if not targets:
        return []
    parts = urlparse(targets[0])
    origin = f"{parts.scheme}://{parts.netloc}"
    async with httpx.AsyncClient(
        timeout=timeout, follow_redirects=True, headers={"User-Agent": _USER_AGENT}
    ) as client:
        try:
            resp = await client.get(f"{origin}/robots.txt")
        except httpx.HTTPError:
            return []
    if resp.status_code >= 400:
        return []
    return disallowed_targets(resp.text, targets, _USER_AGENT)


@dataclass
class RouteStat:
    """Per-route outcome within a stage."""

    total: int = 0
    errors: int = 0
    latencies: list[float] = field(default_factory=list)  # successful, seconds
    status_counts: dict[int, int] = field(default_factory=dict)
    error_kinds: dict[str, int] = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        return self.errors / self.total if self.total else 0.0

    def pct(self, p: float) -> float:
        return percentile(sorted(self.latencies), p)


@dataclass
class StageResult:
    """Aggregated outcome of holding `users` concurrent VUs for `duration`s,
    broken down per route."""

    users: int
    duration: float
    routes: dict[str, RouteStat] = field(default_factory=dict)
    samples: int = 1

    @property
    def total(self) -> int:
        return sum(r.total for r in self.routes.values())

    @property
    def errors(self) -> int:
        return sum(r.errors for r in self.routes.values())

    @property
    def error_rate(self) -> float:
        total = self.total
        return self.errors / total if total else 0.0

    @property
    def rps(self) -> float:
        return self.total / self.duration if self.duration else 0.0

    def _merged_latencies(self) -> list[float]:
        merged: list[float] = []
        for route in self.routes.values():
            merged.extend(route.latencies)
        return merged

    def pct(self, p: float) -> float:
        return percentile(sorted(self._merged_latencies()), p)

    def worst_route(self, by: str):
        """(label, RouteStat) of the most-degraded route, or None."""
        if not self.routes:
            return None
        if by == "latency":
            return max(self.routes.items(), key=lambda kv: kv[1].pct(0.95))
        return max(self.routes.items(), key=lambda kv: (kv[1].error_rate, kv[1].errors))


@dataclass
class RunReport:
    stages: list[StageResult]
    survives_users: int
    max_tested: int
    onset_users: int | None = None
    onset_reason: str | None = None  # "errors" | "latency"
    culprit_route: str | None = None
    bottleneck: str | None = None
    latency_wall: float = 2.0
    saturated: bool = False
    saturation_users: int | None = None
    peak_rps: float = 0.0
    marginal: bool = False
    survives_low: int | None = None
    survives_high: int | None = None
    stable: bool = True


@dataclass
class SaturationInfo:
    saturated: bool
    knee_users: int | None
    peak_rps: float


class _Sink:
    """Per-stage accumulator, keyed by route label. A 5xx/429 is a failure;
    everything else with a status code counts toward latency."""

    def __init__(self) -> None:
        self.routes: dict[str, RouteStat] = {}

    def _stat(self, target: str) -> RouteStat:
        label = route_label(target)
        stat = self.routes.get(label)
        if stat is None:
            stat = RouteStat()
            self.routes[label] = stat
        return stat

    def _kind(self, stat: RouteStat, kind: str) -> None:
        stat.error_kinds[kind] = stat.error_kinds.get(kind, 0) + 1

    def record_response(self, target: str, status: int, latency: float) -> None:
        stat = self._stat(target)
        stat.total += 1
        stat.status_counts[status] = stat.status_counts.get(status, 0) + 1
        if status >= 500:
            stat.errors += 1
            self._kind(stat, "5xx")
        elif status == 429:
            stat.errors += 1
            self._kind(stat, "rate limited (429)")
        else:
            stat.latencies.append(latency)

    def record_error(self, target: str, kind: str) -> None:
        stat = self._stat(target)
        stat.total += 1
        stat.errors += 1
        self._kind(stat, kind)

    def to_stage(self, users: int, duration: float) -> StageResult:
        return StageResult(users=users, duration=duration, routes=self.routes)


class _RateGate:
    """Caps the aggregate rate at which requests are *started* across all VUs by
    spacing out start times. No lock needed: the reserve step has no await."""

    def __init__(self, max_rps: float) -> None:
        self.interval = 1.0 / max_rps
        self._next = 0.0

    async def wait(self, deadline: float) -> bool:
        """Reserve the next start slot. Returns False (without sleeping) if that
        slot falls past the stage deadline, so the worker can stop promptly
        instead of sleeping on a slot it will never use."""
        loop = asyncio.get_running_loop()
        now = loop.time()
        scheduled = self._next if self._next > now else now
        if scheduled >= deadline:
            return False
        self._next = scheduled + self.interval
        delay = scheduled - now
        if delay > 0:
            await asyncio.sleep(delay)
        return True


async def _worker(client: httpx.AsyncClient, method: str, deadline: float,
                  sink: _Sink, pick, gate: _RateGate | None = None,
                  think_time: float = 0.0) -> None:
    """Closed-loop VU: pick a route and fire requests until the stage deadline
    (respecting the optional rate gate and any think-time between requests)."""
    loop = asyncio.get_running_loop()
    while loop.time() < deadline:
        if gate is not None and not await gate.wait(deadline):
            break
        target = pick()
        start = time.perf_counter()
        try:
            resp = await client.request(method, target)
            sink.record_response(target, resp.status_code, time.perf_counter() - start)
        except httpx.TimeoutException:
            sink.record_error(target, "timeout")
        except httpx.ConnectError:
            sink.record_error(target, "connection refused")
        except httpx.HTTPError:
            sink.record_error(target, "network")
        if think_time and loop.time() < deadline:
            await asyncio.sleep(think_time)


async def _run_stage(client: httpx.AsyncClient, targets: list[str], method: str,
                     users: int, duration: float, gate: _RateGate | None = None,
                     think_time: float = 0.0) -> StageResult:
    sink = _Sink()
    cycle = itertools.cycle(targets)  # round-robin spreads load evenly across routes
    loop = asyncio.get_running_loop()
    start = loop.time()
    deadline = start + duration
    await asyncio.gather(
        *(_worker(client, method, deadline, sink, lambda: next(cycle), gate, think_time)
          for _ in range(users))
    )
    # Use actual elapsed wall-time (workers finish their in-flight request after the
    # deadline) so rps reflects true throughput instead of inflating with concurrency.
    elapsed = loop.time() - start
    return sink.to_stage(users, elapsed if elapsed > 0 else duration)


def _merge_stages(group: list[StageResult]) -> StageResult:
    """Pool several runs of the same level into one StageResult (used by --repeat)."""
    merged: dict[str, RouteStat] = {}
    for stage in group:
        for label, rs in stage.routes.items():
            m = merged.get(label)
            if m is None:
                m = RouteStat()
                merged[label] = m
            m.total += rs.total
            m.errors += rs.errors
            m.latencies.extend(rs.latencies)
            for code, n in rs.status_counts.items():
                m.status_counts[code] = m.status_counts.get(code, 0) + n
            for kind, n in rs.error_kinds.items():
                m.error_kinds[kind] = m.error_kinds.get(kind, 0) + n
    return StageResult(users=group[0].users, duration=sum(s.duration for s in group),
                       routes=merged, samples=len(group))


def _warmup_plan(levels: list[int], stage_seconds: float) -> tuple[int, float]:
    """A modest, brief warmup: a low concurrency held for up to ~2s, and never
    longer than a real measured stage."""
    return min(10, max(levels)), min(2.0, stage_seconds)


async def run_loadtest(
    targets: list[str],
    *,
    levels: list[int],
    stage_seconds: float,
    method: str = "GET",
    timeout: float = 10.0,
    max_rps: float | None = None,
    hard_stop_rate: float = 0.5,
    warmup: bool = True,
    repeat: int = 1,
    think_time: float = 0.0,
    progress_cb=None,
    on_stage=None,
    transport: httpx.AsyncBaseTransport | None = None,
) -> tuple[list[StageResult], str | None]:
    """Preflight the target, then ramp through `levels`, spreading each stage's
    load across `targets`. Stops early once a stage is more than `hard_stop_rate`
    failed. Returns (stages, warning)."""
    if not targets:
        raise LoadError("No targets to test.")
    max_conns = max(levels) + 50
    limits = httpx.Limits(max_connections=max_conns, max_keepalive_connections=max_conns)
    warning: str | None = None

    gate = _RateGate(max_rps) if max_rps else None
    async with httpx.AsyncClient(
        timeout=timeout, limits=limits, follow_redirects=True,
        headers={"User-Agent": _USER_AGENT}, transport=transport,
    ) as client:
        try:
            preflight = await client.request(method, targets[0])
        except httpx.HTTPError as exc:
            raise LoadError(f"Couldn't reach {targets[0]}: {exc}") from exc
        if preflight.status_code >= 400:
            warning = (
                f"First request returned HTTP {preflight.status_code} — "
                "results may reflect a broken endpoint, not a load limit."
            )

        if warmup:
            # Discarded: warms caches/JIT/connection pools so the first measured
            # level isn't cold. Still rate-gated, since it's real traffic.
            warmup_users, warmup_seconds = _warmup_plan(levels, stage_seconds)
            await _run_stage(client, targets, method, warmup_users, warmup_seconds,
                             gate, think_time)

        # --repeat pools several ramps per level, so run-to-run variance (cache
        # state, GC, noisy neighbours) widens the confidence band honestly.
        by_level: dict[int, list[StageResult]] = {}
        for _ in range(max(1, repeat)):
            for users in levels:
                if progress_cb:
                    progress_cb(users)
                stage = await _run_stage(client, targets, method, users, stage_seconds,
                                         gate, think_time)
                by_level.setdefault(users, []).append(stage)
                if on_stage:
                    on_stage(stage)
                if stage.error_rate >= hard_stop_rate:
                    break

    stages = [_merge_stages(by_level[u]) for u in sorted(by_level)]
    return stages, warning


def open_client(*, timeout: float = 10.0, max_conns: int = 64,
                transport: httpx.AsyncBaseTransport | None = None) -> httpx.AsyncClient:
    """A client with PreScale's standard headers/limits — for `investigate` probes."""
    limits = httpx.Limits(max_connections=max_conns, max_keepalive_connections=max_conns)
    return httpx.AsyncClient(timeout=timeout, limits=limits, follow_redirects=True,
                             headers={"User-Agent": _USER_AGENT}, transport=transport)


async def measure_route(client: httpx.AsyncClient, url: str, *, users: int,
                        seconds: float, method: str = "GET") -> StageResult:
    """Hold `users` VUs against a single URL for `seconds`; return the stage."""
    return await _run_stage(client, [url], method, users, seconds)


def detect_saturation(stages: list[StageResult]) -> SaturationInfo:
    """Throughput plateau: if rps stops climbing while users keep rising, the
    target has hit a concurrency ceiling (capacity) — not just slow responses."""
    rateable = [s for s in stages if s.duration > 0]
    peak = max((s.rps for s in rateable), default=0.0)
    if len(rateable) < 3 or peak <= 0:
        return SaturationInfo(False, None, peak)
    knee = next(s for s in rateable if s.rps >= 0.85 * peak)
    last = rateable[-1]
    plateaued = knee.users < last.users and last.users >= knee.users * 1.5
    return SaturationInfo(plateaued, knee.users if plateaued else None, peak)


def _bottleneck_hint(stat: RouteStat, reason: str, sat: SaturationInfo) -> str:
    if reason == "latency":
        if sat.saturated:
            return (
                "Concurrency ceiling — once throughput maxes out, extra users just "
                "queue, so latency climbs. Check worker/thread pool size, a "
                "single-threaded server, or a serialized resource."
            )
        return (
            "Slow responses, not failures — p95 crosses the wall while throughput is "
            "still climbing. Often a slow query, an N+1, or a missing cache."
        )
    kind = max(stat.error_kinds, key=stat.error_kinds.get) if stat.error_kinds else ""
    if kind == "5xx":
        server_errors = {c: n for c, n in stat.status_counts.items() if c >= 500}
        if server_errors and max(server_errors, key=server_errors.get) == 503:
            return (
                "503 Service Unavailable under load — a proxy or load balancer shed "
                "load, or the app signalled overload (often connection-pool or queue "
                "limits)."
            )
        return (
            "Server returned 5xx under load — likely an unhandled overload "
            "(DB connection pool, worker queue, or an uncaught error path)."
        )
    hints = {
        "rate limited (429)": "A rate limiter kicked in (429). Fine if intentional; "
                              "otherwise it'll throttle real users during a spike.",
        "timeout": "Requests started timing out — the server is saturated or a "
                   "downstream dependency is blocking.",
        "connection refused": "Connections were refused — you hit a connection or "
                              "worker ceiling (or the process fell over).",
        "network": "Network-level errors under load — connection handling is the wall.",
    }
    return hints.get(kind, "The target started failing under load.")


# z for an ~80% central band (10th–90th-percentile edges).
_BAND_Z = 1.2816


def wilson_bounds(successes: int, n: int, z: float = _BAND_Z) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion (e.g. an error rate)."""
    if n == 0:
        return 0.0, 0.0
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def quantile_bounds(sorted_vals: list[float], q: float,
                    z: float = _BAND_Z) -> tuple[float, float]:
    """Approximate CI for the q-quantile via order statistics (normal approx)."""
    n = len(sorted_vals)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return sorted_vals[0], sorted_vals[0]
    mean = n * q
    sd = math.sqrt(n * q * (1 - q))
    lo = max(0, math.floor(mean - z * sd))
    hi = min(n - 1, math.ceil(mean + z * sd))
    return sorted_vals[lo], sorted_vals[hi]


def _onset_with(stages, err_of, p95_of, *, latency_wall, error_threshold):
    """First stage that crosses a threshold, using custom error-rate / p95
    accessors (so we can re-find onset under pessimistic vs optimistic bounds)."""
    for stage in stages:
        if stage.total and err_of(stage) >= error_threshold:
            return stage
        lat = p95_of(stage)
        if lat is not None and lat >= latency_wall:
            return stage
    return None


def _survives_before(stages, onset, max_tested):
    if onset is None:
        return max_tested
    idx = stages.index(onset)
    return stages[idx - 1].users if idx > 0 else 0


def confidence_band(stages, *, latency_wall, error_threshold, survives_point,
                    max_tested) -> tuple[int, int, bool]:
    """A band on survives_users from within-run uncertainty: re-find onset using
    pessimistic (upper-bound) and optimistic (lower-bound) estimates of each
    level's error rate and p95. Deterministic — same data, same band."""
    def err_hi(s):
        return wilson_bounds(s.errors, s.total)[1] if s.total else 0.0

    def err_lo(s):
        return wilson_bounds(s.errors, s.total)[0] if s.total else 0.0

    def p95_hi(s):
        lats = sorted(s._merged_latencies())
        return quantile_bounds(lats, 0.95)[1] if lats else None

    def p95_lo(s):
        lats = sorted(s._merged_latencies())
        return quantile_bounds(lats, 0.95)[0] if lats else None

    onset_lo = _onset_with(stages, err_hi, p95_hi,
                           latency_wall=latency_wall, error_threshold=error_threshold)
    onset_hi = _onset_with(stages, err_lo, p95_lo,
                           latency_wall=latency_wall, error_threshold=error_threshold)
    low = min(_survives_before(stages, onset_lo, max_tested), survives_point)
    high = max(_survives_before(stages, onset_hi, max_tested), survives_point)
    return low, high, low == high


def analyze(stages: list[StageResult], *, latency_wall: float,
            error_threshold: float, rate_capped: bool = False) -> RunReport:
    """Find the first level that crosses the error or latency threshold, and the
    route most responsible for it."""
    onset: StageResult | None = None
    reason: str | None = None
    for stage in stages:
        if stage.total and stage.error_rate >= error_threshold:
            onset, reason = stage, "errors"
            break
        if stage._merged_latencies() and stage.pct(0.95) >= latency_wall:
            onset, reason = stage, "latency"
            break

    sat = detect_saturation(stages)
    if rate_capped:  # the plateau would be our own ceiling, not the app's
        sat = SaturationInfo(False, None, sat.peak_rps)
    max_tested = stages[-1].users if stages else 0
    if onset is None:
        low, high, stable = confidence_band(
            stages, latency_wall=latency_wall, error_threshold=error_threshold,
            survives_point=max_tested, max_tested=max_tested)
        return RunReport(
            stages=stages, survives_users=max_tested, max_tested=max_tested,
            latency_wall=latency_wall, saturated=sat.saturated,
            saturation_users=sat.knee_users, peak_rps=sat.peak_rps,
            survives_low=low, survives_high=high, stable=stable,
        )

    idx = stages.index(onset)
    survives = stages[idx - 1].users if idx > 0 else 0
    worst = onset.worst_route("latency" if reason == "latency" else "errors")
    culprit = worst[0] if worst else None
    bottleneck = _bottleneck_hint(worst[1], reason, sat) if worst else None
    marginal = (onset.users == max_tested and reason == "errors"
                and onset.error_rate < 2 * error_threshold)
    low, high, stable = confidence_band(
        stages, latency_wall=latency_wall, error_threshold=error_threshold,
        survives_point=survives, max_tested=max_tested)
    return RunReport(
        stages=stages,
        survives_users=survives,
        max_tested=max_tested,
        onset_users=onset.users,
        onset_reason=reason,
        culprit_route=culprit,
        bottleneck=bottleneck,
        latency_wall=latency_wall,
        saturated=sat.saturated,
        saturation_users=sat.knee_users,
        peak_rps=sat.peak_rps,
        marginal=marginal,
        survives_low=low, survives_high=high, stable=stable,
    )
