"""Journey results everywhere: compare, the HTML report, and the MCP summary."""

import copy

from prescale_cli.compare import compare_results, to_markdown
from prescale_cli.mcp_tools import summarize_result
from prescale_cli.report import render_html


def _journey(name, survives, onset, low=None, high=None, step=None, status="ok"):
    if status != "ok":
        return {"name": name, "type": "browse", "weight": 5, "status": status,
                "reason": "step 1 (home): returned 404, expected 200"}
    return {"name": name, "type": "checkout", "weight": 5, "status": "ok", "reason": None,
            "survives_users": survives, "max_tested": 200, "onset_users": onset,
            "onset_reason": "errors" if onset else None,
            "confidence": {"survives_low": low if low is not None else survives,
                           "survives_high": high if high is not None else survives,
                           "stable": True},
            "culprit_step": ({"index": 3, "name": step, "route": "POST /api/orders"}
                             if step else None),
            "bottleneck": "5xx under load" if onset else None}


def _run(journeys, survives=20, culprit="checkout"):
    return {
        "id": "r1", "created_at": "2026-11-02T10:00:00Z", "tool_version": "1.1.3",
        "target": {"url": "http://shop.test", "host": "shop.test", "routes": ["GET /"]},
        "config": {"method": "GET", "max_users": 200, "stage_seconds": 2,
                   "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": None,
                   "mode": "journeys"},
        "verdict": {"survives_users": survives, "max_tested": 200, "onset_users": survives + 10,
                    "onset_reason": "errors", "culprit_route": "POST /api/orders",
                    "culprit_journey": culprit, "bottleneck": "5xx under load",
                    "saturated": False, "saturation_users": None, "peak_rps": 300.0,
                    "marginal": False,
                    "confidence": {"survives_low": survives, "survives_high": survives,
                                   "stable": True}},
        "stages": [{"users": 1, "rps": 3.0, "p50_ms": 20, "p95_ms": 30, "p99_ms": 40,
                    "error_rate": 0.0, "errors": 0, "total": 6, "routes": {}}],
        "environment": {"git_commit": "abc1234"},
        "journeys": journeys,
    }


def test_compare_flags_a_drop_in_any_journey():
    old = _run([_journey("browse", 200, None), _journey("checkout", 40, 50, step="place order")],
               survives=40)
    new = _run([_journey("browse", 200, None), _journey("checkout", 20, 30, step="place order")],
               survives=20)
    cmp = compare_results(old, new)
    rows = {j["name"]: j for j in cmp["journeys"]}
    assert rows["checkout"]["regressed"] and rows["checkout"]["confident"]
    assert rows["checkout"]["pct"] == -0.5 and rows["checkout"]["breaks_at"] == "place order"
    assert not rows["browse"]["regressed"]
    assert cmp["regressed"]
    assert "| checkout | ~40 | ~20 | -50% 🔴 | place order |" in to_markdown(cmp)


def test_a_drop_in_a_journey_that_isnt_the_weakest_is_still_a_regression():
    # search is the weakest both times; checkout drops but stays above it
    old = _run([_journey("search", 10, 20), _journey("checkout", 100, 120)], survives=10,
               culprit="search")
    new = _run([_journey("search", 10, 20), _journey("checkout", 50, 60)], survives=10,
               culprit="search")
    cmp = compare_results(old, new)
    assert cmp["survives_delta"] == 0
    assert cmp["regressed"] and cmp["confident"]
    assert cmp["summary"] == "Capacity regressed: checkout 100 → 50 users (-50%)."


def test_new_removed_and_stale_journeys_are_listed_not_counted():
    old = _run([_journey("browse", 200, None), _journey("gone", 30, 40)])
    new = _run([_journey("browse", 200, None, status="stale"), _journey("fresh", 30, 40)])
    rows = {j["name"]: j["status"] for j in compare_results(old, new)["journeys"]}
    assert rows == {"browse": "ok → stale", "gone": "removed", "fresh": "new"}
    assert not any(j["regressed"] for j in compare_results(old, new)["journeys"])


def test_html_report_shows_journeys_combined_and_expect():
    run = _run([_journey("checkout", 20, 30, low=20, high=30, step="place order"),
                _journey("old", 0, None, status="stale")])
    run["combined"] = {"mix": {"checkout": 50.0, "quickbuy": 50.0}, "survives_users": 20,
                       "max_tested": 200, "onset_users": 30, "culprit_journey": "checkout",
                       "interference": {"journey": "checkout", "users_at_break": 15,
                                        "held_alone": 20, "with": ["quickbuy"]}}
    run["expect"] = {"users": 60, "meets": False, "survives_users": 20,
                     "journeys": [{"name": "checkout", "users": 30.0, "survives_users": 20,
                                   "meets": False}],
                     "combined": {"survives_users": 20, "meets": False}, "untested": ["old"]}
    html = render_html(run)
    assert "<h3>Journeys</h3>" in html
    assert "~20 (20–30)" in html and "3. place order" in html
    assert "checkout broke with 15 of its own users, but held 20 alone" in html
    assert "Expected ~60 users: no" in html and "old: not load-tested" in html


def test_html_escapes_journey_names_and_reasons():
    j = _journey("x", 20, 30, step="<script>alert(1)</script>")
    html = render_html(_run([j]))
    assert "<script>alert(1)</script>" not in html


def test_url_runs_render_and_compare_as_before():
    run = _run([])
    del run["journeys"]
    run["config"].pop("mode")
    assert "<h3>Journeys</h3>" not in render_html(run)
    assert "journeys" not in compare_results(run, copy.deepcopy(run))
    assert "journeys" not in summarize_result(run)


def test_mcp_summary_lists_journeys_compactly():
    run = _run([_journey("checkout", 20, 30, step="place order"),
                _journey("old", 0, None, status="stale")])
    s = summarize_result(run)
    assert s["culprit_journey"] == "checkout"
    assert s["journeys"][0]["breaks_at_step"] == "3. place order (POST /api/orders)"
    assert s["journeys"][1] == {"name": "old", "status": "stale",
                                "reason": "step 1 (home): returned 404, expected 200"}
