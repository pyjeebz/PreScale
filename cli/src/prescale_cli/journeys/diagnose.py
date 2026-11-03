"""Why the journey step that breaks first broke, and how to fix it.

The ramp names the journey and the step that break first. This probes that step
the way `investigate` probes a URL route, but with the journey's own state: its
latency with one user comes from replaying the journey from the start (log in,
add to cart, then the step), so a step that needs a token or a cart id is
measured the way a real user reaches it. The journey's other steps play the part
static assets play for URLs: if they held while this step broke, the limit is
something this step uses (often a database pool), not the whole server.

When every journey held on its own but they broke ramped together, the step that
broke in the combined run is diagnosed instead, from the combined run's numbers:
that's the case where journeys compete for something they share.

Classification and fixes are `investigate`'s (`classify`, `remediate`), so a
journey step and a URL route get the same diagnosis for the same evidence. No
model is involved.
"""

from __future__ import annotations

import asyncio
import statistics
import time
from dataclasses import dataclass, field

import httpx

from prescale_cli.audit import _CDN_MARKERS
from prescale_cli.investigate import Probes, classify, remediate
from prescale_cli.journeys.load import JourneyRun
from prescale_cli.journeys.model import Journey
from prescale_cli.journeys.replay import SEP, check
from prescale_cli.loadtest import LAG_THRESHOLD_MS, RouteStat, RunReport, edge_blocker

# The 1-user baseline: replay the journey for about this long, at least
# MIN_WALKS and at most MAX_WALKS times, after a short pause so the app can
# recover from the ramp. Fewer than MIN_SAMPLES walks that reach the step and
# there is no baseline (rather than one built on an outlier).
BASELINE_SECONDS = 2.0
COOLDOWN_SECONDS = 1.0
MIN_WALKS, MAX_WALKS = 5, 50
MIN_SAMPLES = 5
# Below this many samples a p95 is just the slowest one, so use the median.
P95_SAMPLES = 20
# The step's completions per second count as stopped rising when, from the
# level before the onset to the onset, they stayed within this band (a drop
# below it is a collapse, not a ceiling).
PLATEAU_BAND = (0.85, 1.15)
# ...and only if requests queued at this step: under load they took at least
# this many times their 1-user time. A cheap step that just completes at the
# pace of a busier step before it never queues, so it isn't counted.
QUEUE_FACTOR = 3.0


@dataclass
class StepProbes:
    """Evidence about one journey step: the probes `classify` reads, plus what
    only a journey has."""
    probes: Probes
    journey: Journey
    index: int                                   # 1-based, first step with this route
    shared: list[int] = field(default_factory=list)  # every step with this route, if >1
    together: bool = False                       # from the combined run
    walks: int = 0
    samples: int = 0


def _held(stat: RouteStat | None, *, latency_wall: float, error_threshold: float) -> bool:
    return (stat is not None and stat.total > 0 and stat.error_rate < error_threshold
            and (not stat.latencies or stat.pct(0.95) < latency_wall))


def _completions(stage, label: str) -> float:
    stat = stage.routes.get(label)
    return len(stat.latencies) / stage.duration if stat and stage.duration > 0 else 0.0


def _peak_completions(report: RunReport, label: str) -> float | None:
    """LABEL's successful completions per second at the onset level, if they
    had stopped rising there (neither rising nor collapsing) while users kept
    rising, and PreScale's own machine kept up; else None."""
    stages = sorted(report.stages, key=lambda s: s.users)
    at = next((i for i, s in enumerate(stages) if s.users == report.onset_users), None)
    if at is None or at == 0:
        return None
    onset, prev = stages[at], stages[at - 1]
    if max(onset.loop_lag_ms, prev.loop_lag_ms) >= LAG_THRESHOLD_MS:
        return None  # the load generator was the limit, not the app
    rate, before = _completions(onset, label), _completions(prev, label)
    if rate <= 0 or before <= 0 or onset.users <= prev.users:
        return None
    low, high = PLATEAU_BAND
    return rate if low * before <= rate <= high * before else None


def _baseline(samples: list[float]) -> float | None:
    if len(samples) < MIN_SAMPLES:
        return None
    if len(samples) < P95_SAMPLES:
        return statistics.median(samples)
    ordered = sorted(samples)
    return ordered[round(0.95 * (len(ordered) - 1))]


async def gather_step_probes(journey: Journey, report: RunReport | None, base_url: str, *,
                             latency_wall: float, error_threshold: float, prefix: str = "",
                             timeout: float = 10.0, headers: dict[str, str] | None = None,
                             env: dict[str, str] | None = None, max_rps: float | None = None,
                             transport: httpx.AsyncBaseTransport | None = None,
                             seconds: float = BASELINE_SECONDS,
                             cooldown: float = COOLDOWN_SECONDS) -> StepProbes | None:
    """Evidence about the step of JOURNEY that REPORT broke at, or None if it
    didn't break there. PREFIX is how REPORT labels this journey's steps
    (`checkout › ` in the combined run)."""
    if report is None or report.onset_users is None or not report.culprit_route:
        return None
    if not report.culprit_route.startswith(prefix):
        return None
    label = report.culprit_route[len(prefix):]
    steps = journey.steps
    # Steps with the same method and path share one set of numbers under load.
    shared = [i for i, s in enumerate(steps, 1) if s.label == label]
    if not shared:
        return None
    index = shared[0]
    onset = report.onset_users
    stage = next((s for s in report.stages if s.users == onset), None)
    stat = stage.routes.get(prefix + label) if stage else None
    p = Probes(
        culprit_route=label, onset_users=onset,
        loaded_p95_ms=stat.pct(0.95) * 1000 if (stat and stat.latencies) else None,
        throughput_plateaued=report.saturated,
        error_kinds=dict(stat.error_kinds) if stat else {},
        status_counts=dict(stat.status_counts) if stat else {},
        reference="the journey's other steps",
        users_label="users in total" if prefix else "users",
    )

    # The other steps (other routes) that ran at the onset level: steps after a
    # failing one don't run in that walk, so only the ones with requests count.
    others: dict[str, list[str]] = {}
    if stage is not None:
        for s in steps:
            ran = (stage.routes.get(prefix + s.label) or RouteStat()).total > 0
            if s.label != label and ran:
                others.setdefault(s.label, []).append(s.name)
    if others:
        p.static_route = ", ".join(n for names in others.values() for n in names)
        p.static_ok = all(_held(stage.routes.get(prefix + lbl), latency_wall=latency_wall,
                                error_threshold=error_threshold) for lbl in others)

    # How much of the step a CDN answered from cache, and whether its firewall stepped in.
    step_stats = [s.routes[prefix + label] for s in report.stages if prefix + label in s.routes]
    served = sum(len(r.latencies) for r in step_stats)
    if served:
        p.cache_share = sum(r.cache_hits for r in step_stats) / served
        p.cache_source = next((r.cache_source for r in step_stats if r.cache_source), None)
    p.edge_blocker = next((kind.removeprefix("blocked by ") for r in step_stats
                           for kind in r.error_kinds if kind.startswith("blocked by ")), None)

    # The step at one user, reached through the journey's earlier steps.
    await asyncio.sleep(cooldown)
    samples: list[float] = []
    seen_headers: httpx.Headers | None = None
    walks = 0
    start = time.monotonic()
    while walks < MAX_WALKS and (walks < MIN_WALKS or time.monotonic() - start < seconds):
        walk = await check(journey, base_url, timeout=timeout, headers=headers, env=env,
                           transport=transport)
        walks += 1
        if len(walk.steps) >= index and walk.steps[index - 1].ok:
            samples.append(walk.steps[index - 1].latency)
            seen_headers = walk.steps[index - 1].headers or seen_headers
        if max_rps:
            # Stay under --max-rps: one walk is one request per step it ran.
            await asyncio.sleep(len(walk.steps) / max_rps)
    baseline = _baseline(samples)
    p.baseline_p95_ms = baseline * 1000 if baseline is not None else None
    # How many it serves at once: completions/s at the wall x the time each takes.
    # Not under --max-rps: the cap, not the app, would be what stopped it rising.
    peak = None if max_rps else _peak_completions(report, prefix + label)
    if peak is not None and len(samples) >= MIN_SAMPLES and stat and stat.latencies:
        service = statistics.median(samples)
        if statistics.fmean(stat.latencies) >= QUEUE_FACTOR * service:
            p.peak_completions, p.service_ms = peak, service * 1000
            p.in_flight = peak * service
    p.baseline_stat = "p95" if len(samples) >= P95_SAMPLES else "median"
    if seen_headers is not None:
        lower = {k.lower(): v for k, v in seen_headers.items()}
        p.server = lower.get("server")
        p.cdn = next((name for marker, name in _CDN_MARKERS.items() if marker in lower), None)
        if not p.cdn and "cloudflare" in (p.server or "").lower():
            p.cdn = "Cloudflare"
        p.edge_blocker = p.edge_blocker or edge_blocker(seen_headers)
    return StepProbes(p, journey, index, shared if len(shared) > 1 else [],
                      together=bool(prefix), walks=walks, samples=len(samples))


def _names(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def diagnose_step(found: StepProbes, *, interference: dict | None = None,
                  held_alone: int | None = None) -> dict:
    """The Result's `investigation` block for a journey step: the URL fields
    (culprit_route, class, confidence, summary, evidence, remediation, stack),
    plus the journey and step, and the combined run's interference when it was
    this journey that the mix starved."""
    p = found.probes
    diag = classify(p)
    stack = {k: v for k, v in {"server": p.server, "cdn": p.cdn}.items() if v}
    name = found.journey.name
    evidence = list(diag.evidence)
    starved = interference if interference and interference.get("journey") == name else None
    if found.together and not starved:
        alone = f" (it held {held_alone} users alone)" if held_alone is not None else ""
        evidence.insert(0, f"{name} held up on its own{alone} but broke when the journeys "
                           f"ran together: {p.onset_users} users in total")
    if found.shared:
        evidence.append(f"steps {_names([str(i) for i in found.shared])} all call "
                        f"{p.culprit_route}, so their numbers under load are combined")
    if found.samples < MIN_SAMPLES:
        evidence.append(f"no 1-user baseline: only {found.samples} of {found.walks} replays "
                        "reached this step after the ramp")
    if starved:
        evidence.append(f"with {', '.join(starved['with'])} running too, {name} broke at "
                        f"{starved['users_at_break']} of its own users; alone it held "
                        f"{starved['held_alone']}: they compete for something they share")
    elif interference:
        evidence.append(f"also: with {', '.join(interference['with'])} running too, "
                        f"{interference['journey']} broke at {interference['users_at_break']} "
                        f"of its own users; alone it held {interference['held_alone']}")
    return {
        "culprit_route": p.culprit_route,
        "culprit_journey": name,
        "culprit_step": {"index": found.index,
                         "name": found.journey.steps[found.index - 1].name,
                         "route": p.culprit_route},
        "bottleneck_class": diag.bottleneck_class,
        "confidence": diag.confidence,
        "summary": diag.summary,
        "evidence": evidence,
        "remediation": remediate(diag, stack),
        "stack": stack,
        "interference": starved,
    }


async def diagnose_run(worst: JourneyRun, runs: list[JourneyRun], base_url: str, *,
                       together: RunReport | None = None, combined: dict | None = None,
                       **kwargs) -> dict | None:
    """The `investigation` block for a journey run: the step of the first
    journey to break alone; if every journey held alone but they broke ramped
    together, the step that broke in the combined run. None if nothing broke."""
    interference = (combined or {}).get("interference")
    if worst.report is not None and worst.report.onset_users is not None:
        found = await gather_step_probes(worst.journey, worst.report, base_url, **kwargs)
        held_alone = None
    elif together is not None and together.onset_users is not None and combined \
            and combined.get("culprit_journey"):
        name = combined["culprit_journey"]
        run = next((r for r in runs if r.journey.name == name and r.report is not None), None)
        if run is None:
            return None
        found = await gather_step_probes(run.journey, together, base_url,
                                         prefix=f"{name}{SEP}", **kwargs)
        held_alone = run.report.max_tested
    else:
        return None
    if found is None:
        return None
    return diagnose_step(found, interference=interference, held_alone=held_alone)
