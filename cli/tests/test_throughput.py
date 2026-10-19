"""Capacity in req/s and its rough real-visitor equivalent."""

from prescale_cli import ci as ci_mod
from prescale_cli.throughput import capacity_rps, describe, visitors_for


def _result(survives=100, stages=((50, 320.0), (100, 640.0), (150, 589.0))):
    return {"verdict": {"survives_users": survives},
            "stages": [{"users": users, "rps": rps} for users, rps in stages]}


def test_throughput_is_taken_at_the_highest_stage_that_held():
    # 150 users was the failing stage; capacity is the 100-user stage, not the peak.
    assert capacity_rps(_result()) == 640.0


def test_survives_between_stages_uses_the_stage_below():
    assert capacity_rps(_result(survives=120)) == 640.0


def test_no_stage_at_or_below_capacity_means_unknown():
    assert capacity_rps(_result(survives=10)) is None
    assert describe(_result(survives=10)) is None


def test_visitors_round_to_two_significant_figures():
    assert [visitors_for(r) for r in (6.4, 64, 640, 960, 1280, 12345)] == \
        [64, 640, 6400, 9600, 13000, 120000]


def test_description_reads_as_traffic():
    assert describe(_result()) == "≈ 640 req/s, roughly 6,400 real visitors"


def test_pr_comment_states_traffic_and_the_baselines():
    result = _result()
    result.update({
        "id": "r", "target": {"url": "https://s.test", "host": "s.test"},
        "environment": {"git_commit": "a41f9c2"},
    })
    result["verdict"].update({"max_tested": 150, "onset_users": 150, "onset_reason": "errors",
                              "culprit_route": None, "peak_rps": 640.0,
                              "confidence": {"survives_low": 90, "survives_high": 115}})
    upload = {"comparison": {"kind": "regressed", "pct": -0.333, "against": "main @ 71aa0c9",
                             "baseline": {"survives": 150, "low": 130, "high": 170,
                                          "peakRps": 960.0, "capacityRps": 960.0}},
              "target": {"baselineBranch": "main"}}
    body = ci_mod.render_comment(result, upload, target="s.test", sha="a41f9c2")
    assert "≈ 640 req/s, roughly 6,400 real visitors (was ≈ 960 req/s, roughly 9,600)" in body
    assert "one request per visitor every 10s" in body
