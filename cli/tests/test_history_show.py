"""Tests for `prescale history` and `prescale show`."""

import json

from click.testing import CliRunner

from prescale_cli.loadtest import RouteStat, RunReport, StageResult
from prescale_cli.main import cli
from prescale_cli.result import build_result, write_result


def _write(store, *, survives=10, onset=None, run_id=None):
    rs = RouteStat(total=100, errors=0)
    rs.latencies = [0.02] * 100
    stage = StageResult(users=survives, duration=5.0, routes={"/": rs})
    report = RunReport(stages=[stage], survives_users=survives, max_tested=survives,
                       onset_users=onset, peak_rps=20.0)
    result = build_result(
        report, url="http://localhost:8000", targets=["http://localhost:8000/"],
        config={"method": "GET", "max_users": survives, "stage_seconds": 5.0,
                "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": None},
        warning=None,
    )
    if run_id:
        result["id"] = run_id
    write_result(result, store=store)
    return result


def test_history_empty(tmp_path):
    res = CliRunner().invoke(cli, ["history", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert "No saved runs" in res.output


def test_history_table_renders(tmp_path):
    _write(tmp_path, run_id="20260628T140000Z-aaaaaa")
    res = CliRunner().invoke(cli, ["history", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert "Saved runs" in res.output


def test_history_json_newest_first(tmp_path):
    _write(tmp_path, run_id="20260628T140000Z-aaaaaa")
    _write(tmp_path, run_id="20260628T150000Z-bbbbbb")
    res = CliRunner().invoke(cli, ["history", "--json", "--store", str(tmp_path)])
    assert res.exit_code == 0
    ids = [d["id"] for d in json.loads(res.output)]
    assert ids == ["20260628T150000Z-bbbbbb", "20260628T140000Z-aaaaaa"]


def test_show_latest(tmp_path):
    _write(tmp_path, run_id="20260628T140000Z-aaaaaa")
    _write(tmp_path, run_id="20260628T150000Z-bbbbbb")
    res = CliRunner().invoke(cli, ["show", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert "bbbbbb" in res.output          # latest run
    assert "Scale readiness" in res.output  # rendered verdict panel


def test_show_by_prefix(tmp_path):
    _write(tmp_path, run_id="20260628T140000Z-abc123")
    res = CliRunner().invoke(cli, ["show", "20260628T140000Z-abc", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert "abc123" in res.output


def test_show_json(tmp_path):
    r = _write(tmp_path, run_id="20260628T140000Z-abc123")
    res = CliRunner().invoke(cli, ["show", r["id"], "--json", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert json.loads(res.output)["id"] == r["id"]


def test_show_missing_exits_1(tmp_path):
    res = CliRunner().invoke(cli, ["show", "nope", "--store", str(tmp_path)])
    assert res.exit_code == 1


def test_show_empty_store(tmp_path):
    res = CliRunner().invoke(cli, ["show", "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert "No saved runs" in res.output


def test_show_html(tmp_path):
    _write(tmp_path, run_id="20260628T140000Z-abc123")
    out = tmp_path / "r.html"
    res = CliRunner().invoke(cli, ["show", "--html", str(out), "--store", str(tmp_path)])
    assert res.exit_code == 0
    assert out.read_text().lstrip().startswith("<!doctype html")
