"""PreScale's bar in text (░ sparse → ▒ checkerboard → █ solid end, ┆ marker), in the
terminal, `compare --md` and the PR comment."""

import io

import pytest
from rich.console import Console

from prescale_cli import ci as ci_mod
from prescale_cli import render
from prescale_cli.bars import CHECKER, MARKER, SOLID, SPARSE, bar_rows, route_rows, text_bar
from prescale_cli.compare import compare_results, to_markdown


@pytest.mark.parametrize("value", [0, 1, 37, 150, 250, 999])
def test_bar_is_always_exactly_its_width(value):
    assert len(text_bar(value, 250, width=20)) == 20
    assert len(text_bar(value, 250, width=20, marker=200)) == 20


def test_bar_runs_sparse_then_checker_then_solid():
    bar = text_bar(150, 250, width=20).rstrip()
    assert bar == SPARSE * 7 + CHECKER * 3 + SOLID * 2


def test_any_measured_value_shows_at_least_one_solid_cell():
    assert text_bar(1, 10_000, width=20).rstrip() == SOLID
    assert text_bar(0, 10_000, width=20).strip() == ""


def test_values_past_the_scale_fill_the_bar():
    assert " " not in text_bar(5_000, 2_500, width=16)


def test_marker_sits_on_empty_track_and_never_hides_the_bar():
    assert text_bar(100, 250, width=20, marker=200)[16] == MARKER
    passed = text_bar(240, 250, width=20, marker=200)
    assert MARKER not in passed and passed.rstrip().endswith(SOLID)


def test_bar_rows_line_up_on_one_scale():
    rows = bar_rows([("main @ 71aa0c9", 150, "~150"), ("this deploy", 100, "~100")], 165)
    starts = {row.index(SPARSE) for row in rows}
    assert len(starts) == 1  # bars start in the same column
    assert len(rows[0].split()[2]) > len(rows[1].split()[1])  # the bigger value is longer


def test_route_rows_are_slowest_first_with_the_wall_marked():
    stage = {"routes": {"/": {"p95_ms": 57, "total": 10},
                        "/api/search": {"p95_ms": 1047, "total": 10},
                        "/pricing": {"p95_ms": 88, "total": 10}}}
    rows = route_rows(stage, 2.0)
    assert [row.split()[0] for row in rows] == ["/api/search", "/pricing", "/"]
    assert all(MARKER in row for row in rows)
    assert rows[0].endswith("1.0s") and rows[1].endswith("88ms")


def test_pr_comment_draws_baseline_and_deploy_as_bars():
    result = _comment_result()
    body = ci_mod.render_comment(result, _comment_upload(), target="staging.myapp.com",
                                 sha="a41f9c2")
    block = body.split("```text\n", 1)[1].split("```", 1)[0]
    baseline, deploy = block.strip().splitlines()
    assert baseline.startswith("main @ 71aa0c9") and baseline.endswith("~150")
    assert deploy.startswith("this deploy") and "~100" in deploy and "−33%" in deploy
    assert baseline.count(SOLID) and deploy.count(SOLID)


def test_pr_comment_shows_routes_at_the_breaking_stage():
    result = _comment_result()
    result["config"] = {"latency_wall_s": 2.0}
    result["stages"] = [{"users": 150, "routes": {
        "/api/search": {"p95_ms": 1047, "total": 50}, "/": {"p95_ms": 57, "total": 50}}}]
    body = ci_mod.render_comment(result, _comment_upload(), target="staging.myapp.com",
                                 sha="a41f9c2")
    assert f"{MARKER} = the 2s latency wall" in body
    assert "/api/search" in body.split("p95 per route", 1)[1]


def test_compare_markdown_includes_the_bars():
    md = to_markdown(compare_results(_saved(200), _saved(90)))
    assert "```text" in md and SOLID in md


def test_terminal_ramp_and_panel_use_the_bars(monkeypatch):
    buffer = io.StringIO()
    monkeypatch.setattr(render, "console", Console(file=buffer, width=120, color_system=None))
    render.render_terminal({
        "target": {"url": "https://x.test", "routes": ["/"]},
        "config": {"latency_wall_s": 2.0},
        "verdict": {"survives_users": 100, "max_tested": 300, "onset_users": 150,
                    "onset_reason": "errors", "culprit_route": None, "peak_rps": 640,
                    "saturated": False, "saturation_users": None, "bottleneck": None,
                    "marginal": False, "confidence": {"survives_low": 90, "survives_high": 115}},
        "stages": [
            {"users": 100, "rps": 640, "p50_ms": 30, "p95_ms": 88, "p99_ms": 119,
             "error_rate": 0.0, "total": 3000},
            {"users": 150, "rps": 589, "p50_ms": 126, "p95_ms": 1047, "p99_ms": 1413,
             "error_rate": 0.06, "total": 3000},
        ],
    })
    out = buffer.getvalue()
    assert "vs 2s wall" in out and MARKER in out
    assert "Ramp" in out and "~100 of 300 users tested" in out


# --- fixtures -----------------------------------------------------------------

def _comment_result():
    return {
        "id": "20261015T120000Z-abc123",
        "target": {"url": "https://staging.myapp.com", "host": "staging.myapp.com"},
        "verdict": {"survives_users": 100, "max_tested": 300, "onset_users": 150,
                    "onset_reason": "errors", "culprit_route": "/api/search", "peak_rps": 640,
                    "confidence": {"survives_low": 90, "survives_high": 115, "stable": True}},
        "environment": {"git_commit": "a41f9c2", "git_branch": "feat/search"},
    }


def _comment_upload():
    return {"url": "https://prescale.dev/dashboard/runs/x", "comparison": {
        "kind": "regressed", "pct": -0.333, "confident": True, "against": "main @ 71aa0c9",
        "baseline": {"survives": 150, "low": 130, "high": 170, "peakRps": 960.0,
                     "commit": "71aa0c9"}},
        "target": {"baselineBranch": "main", "verified": True}}


def _saved(survives):
    return {"id": f"r{survives}", "created_at": "2026-10-18T00:00:00Z",
            "target": {"url": "https://x.test"},
            "verdict": {"survives_users": survives, "peak_rps": 100.0, "onset_users": survives,
                        "max_tested": 300,
                        "confidence": {"survives_low": survives - 10,
                                       "survives_high": survives + 10}},
            "environment": {"git_commit": "abc1234"}}
