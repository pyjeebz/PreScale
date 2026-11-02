"""Load-test journeys: the isolation pass.

Each journey is first replayed once (`check`). A journey that fails there is
stale or unreachable and isn't ramped: a failure with no load says nothing about
capacity. Every journey that replays is then ramped on its own, so its verdict
(how many users it survives, the step that breaks first, why) doesn't depend on
any traffic mix. The run's overall verdict is the first journey to break.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from prescale_cli.journeys.model import Journey
from prescale_cli.journeys.replay import JourneyCheck, client_options, journey_vu
from prescale_cli.loadtest import RunReport, StageResult, run_loadtest


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
        return "stale" if self.check.stale else "unreachable"


async def ramp(journey: Journey, base_url: str, *, levels: list[int], stage_seconds: float,
               timeout: float = 10.0, max_rps: float | None = None, warmup: bool = True,
               repeat: int = 1, headers: dict[str, str] | None = None,
               env: dict[str, str] | None = None, think: float = 0.0, progress_cb=None,
               on_stage=None, transport: httpx.AsyncBaseTransport | None = None,
               ) -> tuple[list[StageResult], str | None]:
    """Ramp virtual users who each walk JOURNEY, through LEVELS. THINK is the
    pause for steps without their own `think`."""
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
