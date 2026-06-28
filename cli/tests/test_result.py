"""Tests for the Result contract and its on-disk store."""

import pytest
from prescale_cli.loadtest import RouteStat, RunReport, StageResult
from prescale_cli.result import (
    SCHEMA_VERSION,
    AmbiguousResultError,
    ResultNotFoundError,
    build_result,
    latest_id,
    list_results,
    load_result,
    schema_warning,
    write_result,
)


def _report() -> RunReport:
    rs = RouteStat(total=100, errors=2)
    rs.latencies = [0.01, 0.02, 0.03, 0.05]
    rs.status_counts = {200: 98, 500: 2}
    rs.error_kinds = {"5xx": 2}
    stage = StageResult(users=10, duration=5.0, routes={"/": rs})
    return RunReport(stages=[stage], survives_users=10, max_tested=10,
                     onset_users=None, peak_rps=20.0)


def _result(**over) -> dict:
    result = build_result(_report(), url="http://localhost:8000",
                          targets=["http://localhost:8000/"],
                          config={"method": "GET", "max_users": 10}, warning=None)
    result.update(over)
    return result


def test_build_result_envelope_shape():
    r = _result()
    assert r["schema_version"] == SCHEMA_VERSION
    assert r["kind"] == "run"
    assert r["id"]
    assert r["created_at"].endswith("Z")
    assert r["target"]["host"] == "localhost"
    assert r["target"]["routes"] == ["/"]
    assert r["config"]["method"] == "GET"
    assert r["verdict"]["survives_users"] == 10
    assert len(r["stages"]) == 1
    assert set(r["stages"][0]) >= {"users", "rps", "p50_ms", "p95_ms", "p99_ms",
                                   "error_rate", "errors", "total", "routes"}
    assert set(r["environment"]) == {"git_commit", "git_branch"}


def test_write_then_load_roundtrips(tmp_path):
    r = _result()
    path = write_result(r, store=tmp_path)
    assert path.exists()
    assert load_result(r["id"], store=tmp_path) == r


def test_id_sorts_chronologically(tmp_path):
    a = _result(id="20260628T140000Z-aaaaaa")
    b = _result(id="20260628T150000Z-bbbbbb")
    write_result(a, store=tmp_path)
    write_result(b, store=tmp_path)
    assert latest_id(store=tmp_path) == b["id"]
    assert [m["id"] for m in list_results(store=tmp_path)] == [b["id"], a["id"]]


def test_load_by_unique_prefix(tmp_path):
    r = _result(id="20260628T140000Z-abc123")
    write_result(r, store=tmp_path)
    assert load_result("20260628T140000Z-abc", store=tmp_path)["id"] == r["id"]


def test_load_ambiguous_prefix_raises(tmp_path):
    write_result(_result(id="20260628T140000Z-aaaaaa"), store=tmp_path)
    write_result(_result(id="20260628T140000Z-aaaaab"), store=tmp_path)
    with pytest.raises(AmbiguousResultError):
        load_result("20260628T140000Z-aaaaa", store=tmp_path)


def test_load_missing_raises(tmp_path):
    with pytest.raises(ResultNotFoundError):
        load_result("nope", store=tmp_path)


def test_empty_store(tmp_path):
    assert list_results(store=tmp_path) == []
    assert latest_id(store=tmp_path) is None


def test_schema_warning():
    assert schema_warning(_result()) is None
    assert schema_warning({"schema_version": SCHEMA_VERSION + 1}) is not None
    assert schema_warning({}) is not None
