"""Tests for prescale investigate — the deterministic classifier, remediation,
and the end-to-end probe path."""

import asyncio

import httpx

from prescale_cli.investigate import (
    Diagnosis,
    Probes,
    classify,
    investigate,
    remediate,
)


def _p(**kw) -> Probes:
    base = dict(culprit_route="/api", onset_users=100)
    base.update(kw)
    return Probes(**base)


# --- classifier (the deterministic heart) ---

def test_classify_rate_limited():
    d = classify(_p(error_kinds={"rate limited (429)": 50}, status_counts={429: 50}))
    assert d.bottleneck_class == "rate_limited" and d.confidence == "high"


def test_classify_overload_shedding():
    d = classify(_p(error_kinds={"5xx": 50}, status_counts={503: 50}))
    assert d.bottleneck_class == "overload_shedding"


def test_classify_connection_pool_app_level():
    d = classify(_p(error_kinds={"5xx": 50}, status_counts={500: 50}, static_ok=True))
    assert d.bottleneck_class == "connection_pool" and d.confidence == "high"


def test_classify_connection_ceiling_when_static_also_fails():
    d = classify(_p(error_kinds={"connection refused": 30}, static_ok=False))
    assert d.bottleneck_class == "connection_ceiling" and d.confidence == "high"


def test_classify_slow_endpoint_when_slow_at_one_user():
    d = classify(_p(baseline_p95_ms=1200.0, loaded_p95_ms=2500.0))
    assert d.bottleneck_class == "slow_endpoint"


def test_classify_concurrency_ceiling_on_plateau():
    d = classify(_p(baseline_p95_ms=30.0, loaded_p95_ms=2500.0, throughput_plateaued=True))
    assert d.bottleneck_class == "concurrency_ceiling" and d.confidence == "high"


def test_classify_unknown_when_no_clear_signal():
    d = classify(_p(baseline_p95_ms=30.0, loaded_p95_ms=40.0))
    assert d.bottleneck_class == "unknown" and d.confidence == "low"


# --- remediation ---

def test_remediate_adds_stack_hint():
    lines = remediate(Diagnosis("concurrency_ceiling", "high", "x", []),
                      {"server": "gunicorn/20.1"})
    assert any("gunicorn" in ln for ln in lines)


def test_remediate_always_nonempty():
    assert remediate(Diagnosis("unknown", "low", "x", []), {})


# --- end-to-end probe path ---

def test_investigate_attaches_diagnosis_on_failure(tmp_path):
    transport = httpx.MockTransport(lambda req: httpx.Response(500, text="err"))
    result = asyncio.run(investigate(
        "http://localhost:9/", max_users=2, stage_seconds=0.02, store=tmp_path,
        transport=transport))
    inv = result.get("investigation")
    assert inv is not None
    assert inv["bottleneck_class"] == "connection_pool"
    assert inv["culprit_route"] == "/"
    assert inv["evidence"]


def test_investigate_no_diagnosis_when_held_up(tmp_path):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="ok"))
    result = asyncio.run(investigate(
        "http://localhost:9/", max_users=2, stage_seconds=0.02, store=tmp_path,
        transport=transport))
    assert result.get("investigation") is None


def test_investigate_profile_and_audit_attach_to_the_result(tmp_path):
    import asyncio

    import httpx

    from prescale_cli.investigate import investigate
    from prescale_cli.profiles import lookup

    page = '<html><link rel="stylesheet" href="/app.css"></html>'
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text=page))
    # The audit makes its own client; point it at a dead port so it reports, never raises.
    result = asyncio.run(investigate(
        "http://127.0.0.1:9/", stage_seconds=0.05, store=tmp_path, transport=transport,
        profile=lookup("product-hunt"), audit=True))
    assert result["profile"]["name"] == "product-hunt"
    assert result["profile"]["peak_users"] == 100
    assert result["config"]["profile"] == "product-hunt"
    assert isinstance(result["audit"], list) and result["audit"]
    assert {"name", "status", "detail"} <= set(result["audit"][0])


def test_investigate_rejects_unknown_profile():
    from click.testing import CliRunner

    from prescale_cli.main import cli

    out = CliRunner().invoke(cli, ["investigate", "http://localhost:1", "--profile", "nope"])
    assert out.exit_code == 1
    assert "unknown profile" in out.output
