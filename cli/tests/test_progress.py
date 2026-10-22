"""Progress while the ramp runs: live in a terminal, one line per stage in CI logs
and pipes, nothing with --json."""

import io

from rich.console import Console

from prescale_cli.live import LiveRamp, PlainRamp, QuietRamp, ramp_progress
from prescale_cli.loadtest import RouteStat, StageResult


def _stage(users, latency, errors=0):
    route = RouteStat(total=100, errors=errors)
    route.latencies = [latency] * (100 - errors)
    return StageResult(users=users, duration=5.0, routes={"/": route})


def test_the_display_matches_the_output():
    assert isinstance(ramp_progress(Console(file=io.StringIO()), as_json=True), QuietRamp)
    assert isinstance(ramp_progress(Console(file=io.StringIO())), PlainRamp)
    assert isinstance(ramp_progress(Console(file=io.StringIO(), force_terminal=True)), LiveRamp)


def test_ci_logs_get_one_line_per_stage():
    out = io.StringIO()
    with PlainRamp(Console(file=out, width=120), latency_wall=2.0) as progress:
        progress.finished(_stage(10, 0.05))
        progress.finished(_stage(50, 2.5))
        progress.diagnosing()
    lines = out.getvalue().splitlines()
    assert lines[0] == "Ramping load…"
    assert lines[1] == "    10 users · 20 req/s · p95 50ms · 0% errors"
    assert "50 users" in lines[2] and "p95 2500ms" in lines[2]
    assert lines[3] == "  diagnosing the culprit route…"
