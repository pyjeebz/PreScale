"""Tests for the pure logic of the prescale run load engine."""

from prescale_cli.loadtest import (
    StageResult,
    analyze,
    default_levels,
    percentile,
)


def _stage(users, total, errors, latency, kind="5xx"):
    """Build a StageResult with `total` successful requests at `latency` seconds
    plus `errors` failures of `kind`."""
    s = StageResult(users=users, duration=5.0)
    s.total = total
    s.errors = errors
    s.latencies = [latency] * (total - errors)
    if errors:
        s.error_kinds = {kind: errors}
    return s


def test_percentile_basic():
    vals = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(vals, 0.0) == 1.0
    assert percentile(vals, 1.0) == 5.0
    assert percentile(vals, 0.5) == 3.0


def test_percentile_edges():
    assert percentile([], 0.95) == 0.0
    assert percentile([7.0], 0.95) == 7.0


def test_default_levels_caps_and_ends_at_max():
    levels = default_levels(50)
    assert levels[-1] == 50
    assert all(u <= 50 for u in levels)
    assert levels == sorted(levels)


def test_default_levels_custom_max_appended():
    assert default_levels(42)[-1] == 42


def test_analyze_detects_error_onset():
    stages = [
        _stage(10, 1000, 0, 0.05),
        _stage(50, 1000, 0, 0.08),
        _stage(100, 1000, 200, 0.10),  # 20% errors -> onset
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 100
    assert report.onset_reason == "errors"
    assert report.survives_users == 50
    assert "5xx" in report.bottleneck


def test_analyze_detects_latency_wall():
    stages = [
        _stage(10, 1000, 0, 0.05),
        _stage(50, 1000, 0, 3.0),  # p95 = 3s > 2s wall -> onset
    ]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 50
    assert report.onset_reason == "latency"
    assert report.survives_users == 10


def test_analyze_survives_everything():
    stages = [_stage(10, 1000, 0, 0.05), _stage(100, 1000, 0, 0.06)]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users is None
    assert report.survives_users == 100
    assert report.bottleneck is None


def test_analyze_fails_immediately():
    stages = [_stage(10, 1000, 500, 0.05)]
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_users == 10
    assert report.survives_users == 0
