"""A CDN in front of the target: its firewall blocking a one-IP load test, or its
cache answering instead of the app. Either way the result must say so, not blame
the app (found dogfooding prescale.dev on Vercel)."""

import asyncio
import itertools

import httpx

from prescale_cli.investigate import Probes, classify, investigate, remediate
from prescale_cli.loadtest import _Sink, cache_source, edge_blocker

VERCEL_CHALLENGE = {"x-vercel-mitigated": "challenge", "server": "Vercel"}


def _headers(**values) -> httpx.Headers:
    return httpx.Headers({key.replace("_", "-"): value for key, value in values.items()})


def test_cache_hits_are_recognised_across_cdns():
    assert cache_source(_headers(x_vercel_cache="HIT")) == "Vercel"
    assert cache_source(_headers(x_vercel_cache="PRERENDER")) == "Vercel"
    assert cache_source(_headers(cf_cache_status="HIT")) == "Cloudflare"
    assert cache_source(_headers(x_cache="Hit from cloudfront")) == "the CDN"
    assert cache_source(_headers(x_cache="TCP_HIT")) == "the CDN"


def test_misses_and_dynamic_responses_are_not_cache_hits():
    for headers in (_headers(x_vercel_cache="MISS"), _headers(cf_cache_status="DYNAMIC"),
                    _headers(x_cache="Miss from cloudfront"), _headers(), None):
        assert cache_source(headers) is None


def test_firewall_pages_are_recognised():
    assert edge_blocker(httpx.Headers(VERCEL_CHALLENGE)) == "Vercel's firewall"
    assert edge_blocker(_headers(cf_mitigated="challenge")) == "Cloudflare's firewall"
    assert edge_blocker(_headers(server="Vercel")) is None


def test_a_challenge_page_is_an_error_not_a_fast_success():
    sink = _Sink()
    sink.record_response("https://x.test/", 403, 0.01, httpx.Headers(VERCEL_CHALLENGE))
    route = sink.routes["/"]
    assert route.errors == 1 and route.latencies == []
    assert route.error_kinds == {"blocked by Vercel's firewall": 1}


def _run(handler, tmp_path):
    return asyncio.run(investigate("https://x.test/", max_users=10, stage_seconds=0.05,
                                   store=tmp_path, transport=httpx.MockTransport(handler)))


def test_cached_site_is_reported_as_the_cdn_not_the_app(tmp_path):
    def handler(request):
        # Every response comes from the CDN's cache: the app never sees the test.
        return httpx.Response(200, headers={"x-vercel-cache": "HIT"}, text="ok")

    result = _run(handler, tmp_path)
    assert "came from Vercel's cache" in result["warning"]
    probes = Probes(culprit_route="/", onset_users=10, baseline_p95_ms=20.0,
                    loaded_p95_ms=900.0, throughput_plateaued=True,
                    cache_share=1.0, cache_source="Vercel")
    assert classify(probes).bottleneck_class == "edge_protection"


def test_firewall_that_starts_mid_ramp_is_named_with_the_fix(tmp_path):
    counter = itertools.count()

    def handler(request):
        if next(counter) < 40:
            return httpx.Response(200, text="ok")
        return httpx.Response(403, headers=VERCEL_CHALLENGE, text="<html>challenge</html>")

    result = _run(handler, tmp_path)
    assert result["verdict"]["onset_reason"] == "errors"
    assert "Vercel's firewall started blocking this test" in result["warning"]
    assert "vercel firewall system-bypass add" in result["warning"]
    investigation = result["investigation"]
    assert investigation["bottleneck_class"] == "edge_protection"
    assert any("system-bypass" in line for line in investigation["remediation"])


def test_firewall_seen_only_by_the_probe_still_wins(tmp_path):
    """prescale.dev's case: the ramp was slowed, not blocked; the challenge came after."""
    probes = Probes(culprit_route="/", onset_users=200, baseline_p95_ms=25.0,
                    loaded_p95_ms=2965.0, throughput_plateaued=True,
                    edge_blocker="Vercel's firewall", server="Vercel")
    diagnosis = classify(probes)
    assert diagnosis.bottleneck_class == "edge_protection" and diagnosis.confidence == "high"
    assert "Vercel's firewall answered instead of your app" in diagnosis.evidence
    assert remediate(diagnosis, {"server": "Vercel"})[0].startswith("Exempt your IP")


def test_app_errors_on_a_cached_route_still_blame_the_app():
    probes = Probes(culprit_route="/api", onset_users=50, error_kinds={"5xx": 20},
                    status_counts={500: 20}, static_ok=True, cache_share=0.95,
                    cache_source="Vercel")
    assert classify(probes).bottleneck_class == "connection_pool"


def test_likely_cause_on_a_cached_route_names_the_cdn():
    from prescale_cli.loadtest import RouteStat, SaturationInfo, _bottleneck_hint

    stat = RouteStat(total=100, latencies=[0.5] * 100, cache_hits=97, cache_source="Vercel")
    hint = _bottleneck_hint(stat, "latency", SaturationInfo(True, 20, 500.0))
    assert hint.startswith("Served from Vercel's cache") and "Concurrency" not in hint


def test_an_uncached_app_gets_no_edge_warnings(tmp_path):
    result = _run(lambda request: httpx.Response(200, text="ok"), tmp_path)
    warning = result["warning"] or ""
    assert "firewall" not in warning and "cache" not in warning


def test_a_firewall_on_the_first_request_stops_before_any_load(tmp_path):
    import pytest

    from prescale_cli.loadtest import LoadError

    calls = itertools.count()

    def handler(request):
        next(calls)
        return httpx.Response(403, headers=VERCEL_CHALLENGE, text="<html>challenge</html>")

    with pytest.raises(LoadError, match="Vercel's firewall is blocking requests from this machine"):
        _run(handler, tmp_path)
    assert next(calls) == 1  # only the preflight was sent
