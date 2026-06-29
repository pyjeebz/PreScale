"""Tests for the pure logic of the prescale run load engine."""

import asyncio

import httpx

from prescale_cli.loadtest import (
    RouteStat,
    StageResult,
    _RateGate,
    _warmup_plan,
    analyze,
    build_targets,
    default_levels,
    detect_saturation,
    disallowed_targets,
    parse_sitemap,
    percentile,
    route_label,
    run_loadtest,
)


def _route(total, errors, latency, kind="5xx"):
    """A RouteStat with `total` requests, `errors` failures of `kind`, the rest
    successful at `latency` seconds."""
    rs = RouteStat(total=total, errors=errors)
    rs.latencies = [latency] * (total - errors)
    if errors:
        rs.error_kinds = {kind: errors}
    return rs


def _stage(users, routes):
    return StageResult(users=users, duration=5.0, routes=routes)


# --- percentile ---

def test_percentile_basic():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(vals, 0.0) == 1.0
    assert percentile(vals, 1.0) == 5.0
    assert percentile(vals, 0.5) == 3.0


def test_percentile_edges():
    assert percentile([], 0.95) == 0.0
    assert percentile([7.0], 0.95) == 7.0


# --- ramp ladder ---

def test_default_levels_caps_and_ends_at_max():
    levels = default_levels(50)
    assert levels[-1] == 50
    assert all(u <= 50 for u in levels)
    assert levels == sorted(levels)


def test_default_levels_custom_max_appended():
    assert default_levels(42)[-1] == 42


# --- route helpers (M3) ---

def test_route_label():
    assert route_label("https://app.com") == "/"
    assert route_label("https://app.com/api/search") == "/api/search"
    assert route_label("https://app.com/api/search?q=1") == "/api/search?q=1"


def test_build_targets_joins_dedupes_and_drops_cross_origin():
    targets = build_targets(
        "https://app.com",
        paths=["/a", "/b", "/a"],
        extra=["https://app.com/c", "https://evil.com/x"],
    )
    assert targets == [
        "https://app.com/",
        "https://app.com/a",
        "https://app.com/b",
        "https://app.com/c",
    ]


def test_build_targets_single_when_no_paths():
    assert build_targets("https://app.com") == ["https://app.com/"]


def test_build_targets_dedupes_root_slash_variants():
    targets = build_targets("https://app.com", extra=["https://app.com/"])
    assert targets == ["https://app.com/"]


def test_parse_sitemap_filters_same_origin():
    xml = (
        '<?xml version="1.0"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        "<url><loc>https://app.com/</loc></url>"
        "<url><loc>https://app.com/pricing</loc></url>"
        "<url><loc>https://other.com/x</loc></url>"
        "</urlset>"
    )
    assert parse_sitemap(xml, "https://app.com") == [
        "https://app.com/",
        "https://app.com/pricing",
    ]


def test_parse_sitemap_handles_garbage():
    assert parse_sitemap("not xml", "https://app.com") == []


# --- analysis ---

def test_analyze_detects_error_onset():
    stages = [
        _stage(10, {"/": _route(1000, 0, 0.05)}),
        _stage(50, {"/": _route(1000, 0, 0.08)}),
        _stage(100, {"/": _route(1000, 200, 0.10)}),  # 20% errors -> onset
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 100
    assert report.onset_reason == "errors"
    assert report.survives_users == 50
    assert report.culprit_route == "/"
    assert "5xx" in report.bottleneck


def test_analyze_detects_latency_wall():
    stages = [
        _stage(10, {"/": _route(1000, 0, 0.05)}),
        _stage(50, {"/": _route(1000, 0, 3.0)}),  # p95 = 3s > 2s wall -> onset
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 50
    assert report.onset_reason == "latency"
    assert report.survives_users == 10


def test_analyze_survives_everything():
    stages = [_stage(10, {"/": _route(1000, 0, 0.05)}),
              _stage(100, {"/": _route(1000, 0, 0.06)})]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users is None
    assert report.survives_users == 100
    assert report.bottleneck is None


def test_analyze_fails_immediately():
    stages = [_stage(10, {"/": _route(1000, 500, 0.05)})]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 10
    assert report.survives_users == 0


def test_analyze_attributes_culprit_route():
    # one healthy route, one failing route in the same stage
    stages = [
        _stage(10, {"/": _route(500, 0, 0.05), "/api/search": _route(500, 0, 0.05)}),
        _stage(50, {"/": _route(500, 0, 0.05),
                    "/api/search": _route(500, 300, 0.05)}),  # this route breaks
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 50
    assert report.culprit_route == "/api/search"
    assert report.survives_users == 10


# --- saturation + richer inference (M4) ---

def _lvl(users, rps, latency=0.05, errors=0, kind="5xx"):
    """A stage with a known rps (duration=1s) and uniform latency."""
    rs = RouteStat(total=rps, errors=errors)
    rs.latencies = [latency] * (rps - errors)
    if errors:
        rs.error_kinds = {kind: errors}
    return StageResult(users=users, duration=1.0, routes={"/": rs})


def test_detect_saturation_plateau():
    stages = [_lvl(1, 100), _lvl(5, 400), _lvl(10, 440), _lvl(20, 450)]
    info = detect_saturation(stages)
    assert info.saturated
    assert info.knee_users == 5
    assert info.peak_rps == 450


def test_detect_saturation_still_climbing():
    stages = [_lvl(1, 100), _lvl(5, 250), _lvl(10, 500), _lvl(20, 1000)]
    assert detect_saturation(stages).saturated is False


def test_detect_saturation_needs_three_levels():
    assert detect_saturation([_lvl(1, 100), _lvl(5, 400)]).saturated is False


def test_analyze_saturation_refines_latency_hint():
    stages = [
        _lvl(1, 100, latency=0.05),
        _lvl(5, 400, latency=0.1),
        _lvl(10, 440, latency=0.5),
        _lvl(20, 450, latency=3.0),  # p95 3s > wall -> latency onset; rps plateaued
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_reason == "latency"
    assert report.saturated
    assert "ceiling" in report.bottleneck.lower()


def test_503_refinement():
    bad = RouteStat(total=1000, errors=200)
    bad.latencies = [0.05] * 800
    bad.error_kinds = {"5xx": 200}
    bad.status_counts = {200: 800, 503: 200}
    stages = [
        _lvl(10, 500), _lvl(50, 500),
        StageResult(users=100, duration=1.0, routes={"/api": bad}),
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert "503" in report.bottleneck


def test_marginal_when_only_top_level_wobbles():
    stages = [_lvl(10, 1000), _lvl(20, 1000, errors=30)]  # 3% errors at top only
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 20
    assert report.max_tested == 20
    assert report.marginal is True


def test_rate_capped_suppresses_saturation():
    stages = [_lvl(1, 100), _lvl(5, 400), _lvl(10, 440), _lvl(20, 450)]  # would plateau
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02, rate_capped=True)
    assert report.saturated is False


# --- M5 safety rails ---

def test_rate_gate_paces_starts():
    gate = _RateGate(50)  # 50 rps -> 20ms between starts

    async def fire_five():
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 100
        t0 = loop.time()
        for _ in range(5):
            await gate.wait(deadline)
        return loop.time() - t0

    elapsed = asyncio.run(fire_five())
    assert elapsed >= 0.06  # 4 gaps * 20ms, with slack for scheduling


def test_robots_disallowed_filtering():
    robots = "User-agent: *\nDisallow: /api\n"
    targets = [
        "https://app.com/",
        "https://app.com/api/search",
        "https://app.com/pricing",
    ]
    assert disallowed_targets(robots, targets, "prescale/0.1.0") == [
        "https://app.com/api/search",
    ]


def test_robots_empty_allows_all():
    targets = ["https://app.com/", "https://app.com/api"]
    assert disallowed_targets("", targets, "prescale/0.1.0") == []


# --- warmup (M1.1) ---

def test_warmup_plan_is_low_and_brief():
    assert _warmup_plan([1, 5, 200], 5.0) == (10, 2.0)   # low level, capped at ~2s
    assert _warmup_plan([2], 0.5) == (2, 0.5)            # never longer than a stage


def _counting_transport(counter):
    def handler(request):
        counter.append(1)
        return httpx.Response(200, text="ok")
    return httpx.MockTransport(handler)


def test_warmup_sends_extra_traffic_but_is_discarded():
    targets = ["http://t/"]
    with_warmup, without = [], []
    s1, _ = asyncio.run(run_loadtest(
        targets, levels=[2], stage_seconds=0.02, warmup=True,
        transport=_counting_transport(with_warmup)))
    s2, _ = asyncio.run(run_loadtest(
        targets, levels=[2], stage_seconds=0.02, warmup=False,
        transport=_counting_transport(without)))
    assert len(s1) == 1 and len(s2) == 1        # warmup is never a returned stage
    assert len(with_warmup) > len(without)      # but it did send extra traffic
