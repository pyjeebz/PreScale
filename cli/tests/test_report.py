"""Tests for the HTML report renderer."""

from prescale_cli.loadtest import RouteStat, StageResult, analyze
from prescale_cli.report import render_html
from prescale_cli.result import build_result, load_result, write_result


def _stage(users, total, errors, latency):
    rs = RouteStat(total=total, errors=errors)
    rs.latencies = [latency] * (total - errors)
    if errors:
        rs.error_kinds = {"5xx": errors}
        rs.status_counts = {500: errors}
    return StageResult(users=users, duration=1.0, routes={"/": rs})


def _render(stages, url="https://app.com"):
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    result = build_result(
        report, url=url, targets=["https://app.com/"],
        config={"method": "GET", "stage_seconds": 5.0, "max_users": 200,
                "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": None},
        warning=None,
    )
    return render_html(result)


def test_render_html_is_self_contained_document():
    out = _render([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 200, 0.05)])
    assert out.lstrip().startswith("<!doctype html")
    assert "<style>" in out
    assert "http" not in out.split("<style>")[1].split("</style>")[0]  # no external CSS link
    assert "Readiness report" in out


def test_render_html_no_mangled_escapes():
    # guards against octal-escape corruption of ·, →, ←
    out = _render([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 200, 0.05)])
    assert "\x00" not in out
    assert "·" in out and "→" in out


def test_render_html_verdict_and_culprit():
    out = _render([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 200, 0.05)])
    assert "NEEDS ATTENTION" in out
    assert "Survives ~10" in out
    assert "breaks here" not in out or "onset" in out  # onset row present


def test_render_html_held_up():
    out = _render([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 0, 0.05)])
    assert "READY" in out
    assert "Held up" in out


def test_render_html_escapes_url():
    out = _render([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 0, 0.05)],
                  url="https://app.com/<script>x")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_html_is_pure_function_of_result(tmp_path):
    # Rendering depends only on the stored Result: a reloaded run renders
    # identically to the in-memory one (the basis for `run`/`show` parity).
    report = analyze([_stage(10, 1000, 0, 0.05), _stage(50, 1000, 200, 0.05)],
                     latency_wall=2.0, error_threshold=0.02)
    result = build_result(
        report, url="https://app.com", targets=["https://app.com/"],
        config={"method": "GET", "stage_seconds": 5.0, "max_users": 200,
                "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": None},
        warning=None,
    )
    write_result(result, store=tmp_path)
    reloaded = load_result(result["id"], store=tmp_path)
    assert render_html(reloaded) == render_html(result)
