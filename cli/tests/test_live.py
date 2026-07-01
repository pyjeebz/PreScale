"""Tests for the live ramp table (prescale_cli.live)."""

from __future__ import annotations

from io import StringIO

from rich.console import Console

from prescale_cli.live import LiveRamp, _ramp_table
from prescale_cli.loadtest import RouteStat, StageResult


def _text(renderable) -> str:
    buf = StringIO()
    Console(file=buf, width=90, force_terminal=False).print(renderable)
    return buf.getvalue()


def _stage(users: int, *, total: int, errors: int, p95_s: float = 0.1) -> StageResult:
    rs = RouteStat(
        total=total, errors=errors,
        latencies=[p95_s] * (total - errors),
        status_counts={500: errors, 200: total - errors},
        error_kinds={"5xx": errors} if errors else {},
    )
    return StageResult(users=users, duration=1.0, routes={"/checkout": rs})


def test_ramp_table_shows_running_placeholder():
    text = _text(_ramp_table([(50, None)], latency_wall=2.0))
    assert "running…" in text
    assert "50" in text


def test_ramp_table_renders_error_rate_for_finished_stage():
    stage = _stage(150, total=100, errors=30)
    text = _text(_ramp_table([(150, stage)], latency_wall=2.0))
    assert "150" in text
    assert "30%" in text  # errors climbed


def test_live_ramp_records_order_and_stage_non_tty():
    console = Console(file=StringIO(), force_terminal=False)
    with LiveRamp(console, latency_wall=2.0) as live:
        live.starting(20)
        live.finished(_stage(20, total=40, errors=0))
        live.starting(150)
        live.finished(_stage(150, total=100, errors=30))

    assert live._order == [20, 150]
    assert live._stage[20] is not None
    assert live._stage[150].error_rate == 0.3


def test_live_ramp_marks_start_before_finish():
    console = Console(file=StringIO(), force_terminal=False)
    with LiveRamp(console, latency_wall=2.0) as live:
        live.starting(75)
        assert live._order == [75]
        assert live._stage[75] is None  # in flight until finished
