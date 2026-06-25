"""Tests for the pure logic of the prescale run load engine."""

from prescale_cli.loadtest import (
    RouteStat,
    StageResult,
    analyze,
    build_targets,
    default_levels,
    parse_sitemap,
    percentile,
    route_label,
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
