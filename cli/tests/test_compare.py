"""Tests for prescale compare — capacity diff + regression gating."""

import json

from click.testing import CliRunner

from prescale_cli.compare import compare_results, resolve, to_markdown
from prescale_cli.loadtest import RouteStat, RunReport, StageResult
from prescale_cli.main import cli
from prescale_cli.result import build_result, write_result


def _result(survives, *, low=None, high=None, peak=100.0, run_id=None, commit="abc1234"):
    rs = RouteStat(total=100, errors=0)
    rs.latencies = [0.02] * 100
    stage = StageResult(users=survives, duration=5.0, routes={"/": rs})
    report = RunReport(stages=[stage], survives_users=survives, max_tested=survives,
                       peak_rps=peak,
                       survives_low=low if low is not None else survives,
                       survives_high=high if high is not None else survives)
    r = build_result(report, url="http://localhost:8000",
                     targets=["http://localhost:8000/"],
                     config={"method": "GET", "max_users": survives}, warning=None)
    if run_id:
        r["id"] = run_id
    r["environment"]["git_commit"] = commit
    return r


# --- compare_results (pure) ---

def test_compare_flags_confident_regression():
    c = compare_results(_result(200, low=180, high=220), _result(90, low=80, high=100))
    assert c["regressed"] and not c["improved"] and c["confident"]
    assert c["survives_delta"] == -110


def test_compare_noisy_regression_not_confident():
    c = compare_results(_result(100, low=70, high=130), _result(75, low=50, high=110))
    assert c["regressed"] and not c["confident"]


def test_compare_improvement_not_flagged():
    c = compare_results(_result(90), _result(200))
    assert c["improved"] and not c["regressed"]


def test_compare_steady_within_threshold():
    c = compare_results(_result(100), _result(95))
    assert not c["regressed"] and not c["improved"]


def test_to_markdown_has_table():
    md = to_markdown(compare_results(_result(200), _result(90)))
    assert "PreScale" in md and "survives" in md and "200" in md and "90" in md


def test_resolve_latest_and_exclude(tmp_path):
    write_result(_result(100, run_id="20260629T140000Z-aaaaaa"), store=tmp_path)
    write_result(_result(90, run_id="20260629T150000Z-bbbbbb"), store=tmp_path)
    assert resolve(None, store=tmp_path)["id"] == "20260629T150000Z-bbbbbb"
    assert resolve(None, store=tmp_path,
                   exclude="20260629T150000Z-bbbbbb")["id"] == "20260629T140000Z-aaaaaa"


# --- command ---

def test_compare_command_defaults_to_latest_two(tmp_path):
    write_result(_result(200, run_id="20260629T140000Z-aaaaaa"), store=tmp_path)
    write_result(_result(90, run_id="20260629T150000Z-bbbbbb"), store=tmp_path)
    res = CliRunner().invoke(cli, ["compare", "--json", "--store", str(tmp_path)])
    assert res.exit_code == 0
    c = json.loads(res.output)
    assert c["new"]["survives_users"] == 90 and c["old"]["survives_users"] == 200
    assert c["regressed"]


def test_compare_command_fail_on_regression(tmp_path):
    write_result(_result(200, run_id="20260629T140000Z-aaaaaa"), store=tmp_path)
    write_result(_result(90, run_id="20260629T150000Z-bbbbbb"), store=tmp_path)
    res = CliRunner().invoke(
        cli, ["compare", "--fail-on-regression", "--store", str(tmp_path)])
    assert res.exit_code == 1


def test_compare_command_needs_two_runs(tmp_path):
    write_result(_result(100, run_id="20260629T140000Z-aaaaaa"), store=tmp_path)
    res = CliRunner().invoke(cli, ["compare", "--store", str(tmp_path)])
    assert res.exit_code == 1
