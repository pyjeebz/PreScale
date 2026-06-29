"""Tests for the MCP tool logic (no `mcp` package needed) and the server wiring."""

import asyncio

import httpx
import pytest

from prescale_cli.loadtest import RouteStat, RunReport, StageResult
from prescale_cli.mcp_tools import (
    HostNotAllowedError,
    audit_summary,
    get_run,
    host_allowed,
    investigate_summary,
    list_runs,
    parse_allow,
    run_summary,
    summarize_result,
)
from prescale_cli.result import build_result, write_result


def _mock_ok(counter):
    def handler(request):
        counter.append(1)
        return httpx.Response(200, text="ok")
    return httpx.MockTransport(handler)


def _result(**over):
    rs = RouteStat(total=100, errors=0)
    rs.latencies = [0.02] * 100
    stage = StageResult(users=10, duration=5.0, routes={"/": rs})
    report = RunReport(stages=[stage], survives_users=10, max_tested=10, peak_rps=20.0)
    r = build_result(report, url="http://localhost:8000",
                     targets=["http://localhost:8000/"],
                     config={"method": "GET", "max_users": 10}, warning=None)
    r.update(over)
    return r


# --- allowlist ---

def test_parse_allow():
    assert parse_allow("a.com, b.com ,,") == {"a.com", "b.com"}
    assert parse_allow(None) == set()


def test_host_allowed():
    assert host_allowed("localhost", set())
    assert host_allowed("127.0.0.1", set())
    assert not host_allowed("evil.com", set())
    assert host_allowed("staging.app", {"staging.app"})
    assert host_allowed("anything.com", {"*"})


# --- summarize ---

def test_summarize_result_is_compact():
    s = summarize_result(_result())
    assert s["target"] == "http://localhost:8000"
    assert "verdict" in s and "survives_users" in s and "id" in s
    assert "stages" not in s            # the heavy data is intentionally omitted
    assert "get_run" in s["hint"]


# --- run_summary: safety + happy path ---

def test_run_summary_refuses_non_local_without_allow():
    with pytest.raises(HostNotAllowedError):
        asyncio.run(run_summary("https://evil.com/", allow=set()))


def test_run_summary_rejects_non_url():
    with pytest.raises(ValueError):
        asyncio.run(run_summary("not-a-url", allow=set()))


def test_run_summary_local_runs_and_persists(tmp_path):
    counter = []
    s = asyncio.run(run_summary(
        "http://localhost:9/", allow=set(), max_users=2, stage_seconds=0.02,
        store=tmp_path, transport=_mock_ok(counter)))
    assert s["target"] == "http://localhost:9/"
    assert len(counter) > 0                       # the engine actually ran
    assert len(list_runs(store=tmp_path)) == 1    # persisted


def test_run_summary_allows_listed_host(tmp_path):
    s = asyncio.run(run_summary(
        "https://staging.app/", allow={"staging.app"}, max_users=2, stage_seconds=0.02,
        store=tmp_path, transport=_mock_ok([])))
    assert s["target"] == "https://staging.app/"


def test_get_run_roundtrips(tmp_path):
    r = _result(id="20260629T120000Z-aaa111")
    write_result(r, store=tmp_path)
    assert get_run("20260629T120000Z-aaa111", store=tmp_path)["id"] == r["id"]


def test_audit_summary_rejects_non_url():
    with pytest.raises(ValueError):
        asyncio.run(audit_summary("not-a-url"))


def test_investigate_summary_refuses_non_local():
    with pytest.raises(HostNotAllowedError):
        asyncio.run(investigate_summary("https://evil.com/", allow=set()))


def test_investigate_summary_local_includes_diagnosis(tmp_path):
    transport = httpx.MockTransport(lambda req: httpx.Response(500, text="x"))
    s = asyncio.run(investigate_summary(
        "http://localhost:9/", allow=set(), max_users=2, stage_seconds=0.02,
        store=tmp_path, transport=transport))
    assert s["investigation"] is not None
    assert s["investigation"]["bottleneck_class"] == "connection_pool"


# --- server wiring (needs the optional extra) ---

def test_build_server_registers_tools():
    pytest.importorskip("mcp")
    from prescale_cli.mcp_server import build_server
    assert build_server(set()) is not None
