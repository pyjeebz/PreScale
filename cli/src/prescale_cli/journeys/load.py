"""Load-test journeys: the isolation pass, then the combined pass.

Each journey is first replayed once (`check`). A journey that fails there is
stale or unreachable and isn't ramped: a failure with no load says nothing about
capacity. Every journey that replays is then ramped on its own, so its verdict
(how many users it survives, the step that breaks first, why) doesn't depend on
any traffic mix. The run's overall verdict is the first journey to break.

The combined pass then ramps all of them together, the users split between
journeys by `weight`, to catch interference: journeys competing for something
they share (a database pool, CPU, a cache), which no journey shows on its own.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from prescale_cli.journeys.model import Journey
from prescale_cli.journeys.replay import (
    SEP,
    JourneyCheck,
    apportion,
    client_options,
    journey_vu,
)
from prescale_cli.loadtest import RunReport, StageResult, run_loadtest

# How each non-ok outcome reads in reports.
LABELS = {"stale": "stale", "error": "5xx with one user", "unreachable": "couldn't run"}


class NoJourneyReplaysError(Exception):
    """Every journey was stale or unreachable, so nothing could be load-tested."""

    def __init__(self, runs: list[JourneyRun]) -> None:
        super().__init__("no journey replays against this app")
        self.runs = runs


@dataclass
class JourneyRun:
    journey: Journey
    check: JourneyCheck
    report: RunReport | None = None
    warning: str | None = None

    @property
    def status(self) -> str:
        if self.report is not None:
            return "ok"
        return self.check.outcome


async def ramp(journey: Journey | list[Journey], base_url: str, *, levels: list[int],
               stage_seconds: float,
               timeout: float = 10.0, max_rps: float | None = None, warmup: bool = True,
               repeat: int = 1, headers: dict[str, str] | None = None,
               env: dict[str, str] | None = None, think: float = 0.0, progress_cb=None,
               on_stage=None, transport: httpx.AsyncBaseTransport | None = None,
               ) -> tuple[list[StageResult], str | None]:
    """Ramp virtual users who each walk JOURNEY, through LEVELS; given a list,
    each walk picks one by weight (the combined pass). THINK is the pause for
    steps without their own `think`."""
    return await run_loadtest(
        [base_url], levels=levels, stage_seconds=stage_seconds, timeout=timeout,
        max_rps=max_rps, warmup=warmup, repeat=repeat, headers=headers,
        host_permission=True,  # the caller has already checked the host's rules
        progress_cb=progress_cb, on_stage=on_stage, transport=transport,
        vu=journey_vu(journey, base_url, env, think), client_options=client_options(base_url),
        preflight=False,  # `check` already replayed the journey once
    )


def first_to_break(runs: list[JourneyRun]) -> JourneyRun | None:
    """The ramped journey with the lowest capacity (ties: the one that broke)."""
    ramped = [r for r in runs if r.report is not None]
    if not ramped:
        return None
    return min(ramped, key=lambda r: (r.report.survives_users,
                                      r.report.onset_users is None))


def journeys_block(runs: list[JourneyRun]) -> list[dict]:
    """The Result's `journeys` field: one entry per journey, ramped or not."""
    return [_entry(run) for run in runs]


def _entry(run: JourneyRun) -> dict:
    journey = run.journey
    entry: dict = {"name": journey.name, "type": journey.type, "weight": journey.weight,
                   "status": run.status, "reason": None}
    if run.report is None:
        failed = run.check.failed
        index = run.check.steps.index(failed) + 1 if failed else None
        entry["reason"] = f"step {index} ({failed.step.name}): {failed.problem}" if failed \
            else None
        return entry

    report = run.report
    stage = _stage_at(report)
    culprit = None
    if report.culprit_route:
        index = next((i for i, s in enumerate(journey.steps, 1)
                      if s.label == report.culprit_route), None)
        if index is not None:
            culprit = {"index": index, "name": journey.steps[index - 1].name,
                       "route": report.culprit_route}
    entry.update({
        "survives_users": report.survives_users,
        "max_tested": report.max_tested,
        "onset_users": report.onset_users,
        "onset_reason": report.onset_reason,
        "confidence": {"survives_low": report.survives_low,
                       "survives_high": report.survives_high, "stable": report.stable},
        "culprit_step": culprit,
        "bottleneck": report.bottleneck,
        "steps_at_users": stage.users if stage else None,
        "steps": [_step_stats(i, s, stage) for i, s in enumerate(journey.steps, 1)],
    })
    return entry


def _stage_at(report: RunReport) -> StageResult | None:
    """The stage the step timings come from: where it broke, else the last one."""
    if not report.stages:
        return None
    if report.onset_users is not None:
        for stage in report.stages:
            if stage.users == report.onset_users:
                return stage
    return report.stages[-1]


def _step_stats(index: int, step, stage: StageResult | None) -> dict:
    stat = stage.routes.get(step.label) if stage else None
    if stat is None:
        return {"index": index, "name": step.name, "route": step.label, "requests": 0,
                "p50_ms": None, "p95_ms": None, "error_rate": None}
    has_latency = bool(stat.latencies)
    return {
        "index": index, "name": step.name, "route": step.label, "requests": stat.total,
        "p50_ms": round(stat.pct(0.50) * 1000) if has_latency else None,
        "p95_ms": round(stat.pct(0.95) * 1000) if has_latency else None,
        "error_rate": round(stat.error_rate, 4),
    }


def combined_block(report: RunReport, runs: list[JourneyRun]) -> dict:
    """The Result's `combined` field: the journeys ramped together by weight.
    Users here are the total across journeys, split between them by `apportion`,
    so the number on each journey at any level is exact. If the journey that
    breaks first does so with no more of its own users than it surely held alone
    (the low end of its band), something it shares with the others is the limit:
    interference."""
    ramped = [r for r in runs if r.report is not None]
    weights = [r.journey.weight for r in ramped]
    total = sum(weights)
    share = {r.journey.name: r.journey.weight / total for r in ramped}
    block: dict = {
        "journeys": [r.journey.name for r in ramped],
        "mix": {name: round(part * 100, 1) for name, part in share.items()},
        "survives_users": report.survives_users,
        "max_tested": report.max_tested,
        "onset_users": report.onset_users,
        "onset_reason": report.onset_reason,
        "confidence": {"survives_low": report.survives_low,
                       "survives_high": report.survives_high, "stable": report.stable},
        "culprit_journey": None,
        "culprit_step": None,
        "bottleneck": report.bottleneck,
        "interference": None,
    }
    if report.onset_users is None or not report.culprit_route or SEP not in report.culprit_route:
        return block
    name, label = report.culprit_route.split(SEP, 1)
    run = next((r for r in ramped if r.journey.name == name), None)
    if run is None:
        return block
    index = next((i for i, s in enumerate(run.journey.steps, 1) if s.label == label), None)
    block["culprit_journey"] = name
    if index is not None:
        block["culprit_step"] = {"index": index, "name": run.journey.steps[index - 1].name,
                                 "route": label}
    users_of_it = apportion(report.onset_users, weights)[ramped.index(run)]
    alone = run.report
    if alone.onset_users is None:
        held = alone.max_tested
    else:
        held = alone.survives_low if alone.survives_low is not None else alone.survives_users
    if 0 < users_of_it <= held:
        block["interference"] = {
            "journey": name,
            "users_at_break": users_of_it,
            "held_alone": held,
            "with": [r.journey.name for r in ramped if r.journey.name != name],
        }
    return block
