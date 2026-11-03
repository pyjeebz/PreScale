"""Why the journey step that breaks first broke, and how to fix it.

The ramp names the journey and the step that break first. This probes that step
the way `investigate` probes a URL route, but with the journey's own state: its
latency with one user comes from replaying the journey from the start (log in,
add to cart, then the step), so a step that needs a token or a cart id is
measured the way a real user reaches it. The journey's other steps play the part
static assets play for URLs: if they held while this step broke, the limit is
something this step uses (often a database pool), not the whole server.

Classification and fixes are `investigate`'s (`classify`, `remediate`), so a
journey step and a URL route get the same diagnosis for the same evidence. No
model is involved.
"""

from __future__ import annotations

import httpx

from prescale_cli.audit import _CDN_MARKERS
from prescale_cli.investigate import Probes, classify, remediate
from prescale_cli.journeys.load import JourneyRun
from prescale_cli.journeys.replay import check
from prescale_cli.loadtest import RouteStat, edge_blocker

# Replays of the journey at one user, for the step's baseline latency.
BASELINE_WALKS = 10


def _held(stat: RouteStat | None, *, latency_wall: float, error_threshold: float) -> bool:
    return (stat is not None and stat.total > 0 and stat.error_rate < error_threshold
            and (not stat.latencies or stat.pct(0.95) < latency_wall))


def _p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(0.95 * (len(ordered) - 1)))]


async def gather_step_probes(run: JourneyRun, base_url: str, *, latency_wall: float,
                             error_threshold: float, timeout: float = 10.0,
                             headers: dict[str, str] | None = None,
                             env: dict[str, str] | None = None,
                             transport: httpx.AsyncBaseTransport | None = None,
                             walks: int = BASELINE_WALKS) -> Probes | None:
    """Evidence about the step RUN broke at, or None if it didn't break."""
    report = run.report
    if report is None or report.onset_users is None or not report.culprit_route:
        return None
    label = report.culprit_route
    steps = run.journey.steps
    index = next((i for i, s in enumerate(steps) if s.label == label), None)
    if index is None:
        return None
    onset = report.onset_users
    stage = next((s for s in report.stages if s.users == onset), None)
    stat = stage.routes.get(label) if stage else None
    p = Probes(
        culprit_route=label, onset_users=onset,
        loaded_p95_ms=stat.pct(0.95) * 1000 if (stat and stat.latencies) else None,
        throughput_plateaued=report.saturated,
        error_kinds=dict(stat.error_kinds) if stat else {},
        status_counts=dict(stat.status_counts) if stat else {},
        reference="the journey's other steps",
    )

    # The other steps that ran at the onset level: steps after a failing one
    # don't run in that walk, so only the ones with requests count.
    others = [s for i, s in enumerate(steps) if i != index
              and stage is not None and (stage.routes.get(s.label) or RouteStat()).total > 0]
    if others:
        p.static_route = ", ".join(s.name for s in others)
        p.static_ok = all(_held(stage.routes.get(s.label), latency_wall=latency_wall,
                                error_threshold=error_threshold) for s in others)

    # How much of the step a CDN answered from cache, and whether its firewall stepped in.
    step_stats = [s.routes[label] for s in report.stages if label in s.routes]
    served = sum(len(r.latencies) for r in step_stats)
    if served:
        p.cache_share = sum(r.cache_hits for r in step_stats) / served
        p.cache_source = next((r.cache_source for r in step_stats if r.cache_source), None)
    p.edge_blocker = next((kind.removeprefix("blocked by ") for r in step_stats
                           for kind in r.error_kinds if kind.startswith("blocked by ")), None)

    # The step at one user, reached through the journey's earlier steps.
    latencies: list[float] = []
    seen_headers: httpx.Headers | None = None
    for _ in range(walks):
        walk = await check(run.journey, base_url, timeout=timeout, headers=headers, env=env,
                           transport=transport)
        if len(walk.steps) > index and walk.steps[index].ok:
            latencies.append(walk.steps[index].latency)
            seen_headers = walk.steps[index].headers or seen_headers
    baseline = _p95(latencies)
    p.baseline_p95_ms = baseline * 1000 if baseline is not None else None
    if seen_headers is not None:
        lower = {k.lower(): v for k, v in seen_headers.items()}
        p.server = lower.get("server")
        p.cdn = next((name for marker, name in _CDN_MARKERS.items() if marker in lower), None)
        if not p.cdn and "cloudflare" in (p.server or "").lower():
            p.cdn = "Cloudflare"
        p.edge_blocker = p.edge_blocker or edge_blocker(seen_headers)
    return p


def diagnose_step(run: JourneyRun, probes: Probes, *,
                  interference: dict | None = None) -> dict:
    """The Result's `investigation` block for a journey step: the URL fields
    (culprit_route, class, confidence, summary, evidence, remediation, stack),
    plus the journey and step, and the combined run's interference if it was
    this journey that a mix starved."""
    diag = classify(probes)
    stack = {k: v for k, v in {"server": probes.server, "cdn": probes.cdn}.items() if v}
    index = next(i for i, s in enumerate(run.journey.steps, 1)
                 if s.label == probes.culprit_route)
    name = run.journey.name
    evidence = list(diag.evidence)
    starved = interference if interference and interference.get("journey") == name else None
    if starved:
        others = ", ".join(starved["with"])
        evidence.append(f"with {others} running too, {name} broke at "
                        f"{starved['users_at_break']} of its own users; alone it held "
                        f"{starved['held_alone']}: they compete for something they share")
    return {
        "culprit_route": probes.culprit_route,
        "culprit_journey": name,
        "culprit_step": {"index": index, "name": run.journey.steps[index - 1].name,
                         "route": probes.culprit_route},
        "bottleneck_class": diag.bottleneck_class,
        "confidence": diag.confidence,
        "summary": diag.summary,
        "evidence": evidence,
        "remediation": remediate(diag, stack),
        "stack": stack,
        "interference": starved,
    }
