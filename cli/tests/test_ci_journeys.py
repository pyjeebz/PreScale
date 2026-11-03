"""`prescale ci` with journeys: the comment, stale handling, and the safe comparison."""

import json

import pytest
from click.testing import CliRunner

from prescale_cli import ci as ci_mod
from prescale_cli.journeys.load import JourneyRun, NoJourneyReplaysError
from prescale_cli.journeys.model import parse
from prescale_cli.journeys.replay import JourneyCheck, StepCheck
from prescale_cli.main import cli

CHECKOUT = {"version": 1, "name": "checkout", "type": "checkout",
            "steps": [{"name": "place order",
                       "request": {"method": "POST", "path": "/api/orders"}}]}
BROWSE = {"version": 1, "name": "browse", "steps": [{"name": "home", "request": {"path": "/"}}]}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("GITHUB_ACTIONS", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REPOSITORY",
                 "GITHUB_SHA", "GITHUB_REF", "GITHUB_HEAD_REF", "GITHUB_TOKEN",
                 "GITHUB_STEP_SUMMARY", "PRESCALE_HEADERS", "PRESCALE_PATHS",
                 "PRESCALE_GIT_COMMIT", "PRESCALE_GIT_BRANCH", "PRESCALE_TARGET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PRESCALE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PRESCALE_TOKEN", "psk_test")
    monkeypatch.setenv("GITHUB_ACTIONS", "true")


def _journey_result(stale=False):
    journeys = [
        {"name": "checkout", "type": "checkout", "weight": 5, "status": "ok", "reason": None,
         "survives_users": 20, "max_tested": 100, "onset_users": 30, "onset_reason": "errors",
         "confidence": {"survives_low": 20, "survives_high": 30, "stable": False},
         "culprit_step": {"index": 1, "name": "place order", "route": "POST /api/orders"},
         "bottleneck": "5xx under load"},
        {"name": "browse", "type": "browse", "weight": 60,
         "status": "stale" if stale else "ok",
         "reason": "step 1 (home): returned 404, expected a status below 400" if stale else None,
         **({} if stale else {"survives_users": 100, "max_tested": 100, "onset_users": None,
                              "onset_reason": None, "confidence": {}, "culprit_step": None,
                              "bottleneck": None})},
    ]
    return {
        "id": "r1", "target": {"url": "http://localhost:3000", "host": "localhost"},
        "config": {"mode": "journeys", "replica": True},
        "verdict": {"survives_users": 20, "max_tested": 100, "onset_users": 30,
                    "onset_reason": "errors", "culprit_route": "POST /api/orders",
                    "culprit_journey": "checkout", "peak_rps": 120.0,
                    "confidence": {"survives_low": 20, "survives_high": 30, "stable": False}},
        "environment": {"git_commit": "a41f9c2"},
        "journeys": journeys,
        "combined": {"interference": {"journey": "checkout", "users_at_break": 15,
                                      "held_alone": 20, "with": ["browse"]}},
    }


def _upload(mode=None, kind="regressed"):
    comparison = {"kind": kind, "pct": -0.5, "confident": True, "against": "main @ 71aa0c9",
                  "baseline": {"survives": 40, "low": 35, "high": 45, "peakRps": 200.0,
                               "commit": "71aa0c9"}}
    if mode:
        comparison["mode"] = mode
    return {"url": "https://prescale.dev/dashboard/runs/x", "comparison": comparison,
            "target": {"baselineBranch": "main", "verified": True}}


# --- the comment -----------------------------------------------------------------

def test_a_journey_run_ignores_a_comparison_that_may_be_against_a_url_run():
    assert ci_mod.comparison_for(_journey_result(), _upload()) is None
    assert ci_mod.comparison_for(_journey_result(), _upload(mode="journeys"))["kind"] == "regressed"
    url_run = {**_journey_result(), "config": {}}
    assert ci_mod.comparison_for(url_run, _upload())["kind"] == "regressed"

    body = ci_mod.render_comment(_journey_result(), _upload(), target="myapp.com", sha=None)
    assert "Capacity regressed" not in body
    assert "### ⚪ Capacity: survives ~20 users" in body
    assert "may have tested URLs" in body


def test_journey_comment_lists_journeys_stale_ones_and_interference():
    body = ci_mod.render_comment(_journey_result(stale=True), _upload(mode="journeys"),
                                 target="myapp.com", sha=None)
    assert "### 🔴" in body or "Capacity regressed" in body
    assert "**Breaks first:** checkout › `POST /api/orders`" in body
    assert "| checkout | ~20 | 1. place order `POST /api/orders` | 5xx under load |" in body
    assert "- ⚠️ **browse** (stale): step 1 (home): returned 404" in body
    assert "checkout broke with 15 of its own users, but held 20 alone" in body


def test_stale_only_comment():
    runs = []
    for doc in (CHECKOUT, BROWSE):
        j = parse(doc)
        c = JourneyCheck(j)
        c.steps = [StepCheck(j.steps[0], status=404, problem="returned 404, expected 201")]
        runs.append(JourneyRun(j, c))
    body = ci_mod.render_stale_only(runs, target="myapp.com")
    assert body.startswith(ci_mod.comment_marker("myapp.com"))
    assert "no journey replays against this build" in body
    assert "- **checkout** (stale): step 1 (place order): returned 404, expected 201" in body


# --- the command ------------------------------------------------------------------

def _dir(tmp_path):
    d = tmp_path / "journeys"
    d.mkdir(exist_ok=True)
    for doc in (CHECKOUT, BROWSE):
        (d / f"{doc['name']}.yaml").write_text(json.dumps(doc))
    return str(d)


def _wire(monkeypatch, *, result=None, raises=None, upload=None):
    seen = {}

    def fake_run_journeys(journeys, url, config, **kwargs):
        seen["journeys"] = [j.name for j in journeys]
        seen["url"], seen["replica"] = url, kwargs["replica"]
        if raises:
            raise raises
        return None, result, False

    def fake_upsert(ctx, token, pr_number, body, marker):
        seen["comment"] = body
        return "created"

    monkeypatch.setattr("prescale_cli.commands.ci.run_journeys", fake_run_journeys)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result",
                        lambda *a, **k: upload or _upload())
    monkeypatch.setattr("prescale_cli.commands.ci.upsert_pr_comment", fake_upsert)
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request",
                        lambda ctx, token: {"number": 7, "head": {"ref": "feat/x"}})
    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate",
                        lambda *a, **k: pytest.fail("journey runs don't investigate URLs"))

    async def no_rule(url, **kwargs):
        return None
    monkeypatch.setattr("prescale_cli.commands.ci.probe_host", no_rule)
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_x")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/shop")
    return seen


def _ci(tmp_path, *extra):
    return CliRunner().invoke(cli, ["ci", "http://localhost:3000", "--target", "myapp.com",
                                    "--dir", _dir(tmp_path), "--store", str(tmp_path / "s"),
                                    *extra])


def test_ci_replays_journeys_and_warns_on_stale(monkeypatch, tmp_path):
    seen = _wire(monkeypatch, result=_journey_result(stale=True))
    res = _ci(tmp_path)
    assert res.exit_code == 0, res.output
    assert seen["journeys"] == ["browse", "checkout"]
    assert "::warning::PreScale: browse no longer replays" in res.output
    assert "Not load-tested" in seen["comment"]


def test_ci_stale_fail_fails_the_job(monkeypatch, tmp_path):
    _wire(monkeypatch, result=_journey_result(stale=True))
    res = _ci(tmp_path, "--stale", "fail")
    assert res.exit_code == 1
    assert "::error::PreScale: browse no longer replays" in res.output


def test_ci_never_fails_a_journey_run_on_an_unmarked_comparison(monkeypatch, tmp_path):
    _wire(monkeypatch, result=_journey_result())
    assert _ci(tmp_path, "--fail-on-regression").exit_code == 0
    _wire(monkeypatch, result=_journey_result(), upload=_upload(mode="journeys"))
    assert _ci(tmp_path, "--fail-on-regression").exit_code == 1


def test_ci_comments_when_no_journey_replays(monkeypatch, tmp_path):
    seen = _wire(monkeypatch, raises=NoJourneyReplaysError([]))
    res = _ci(tmp_path)
    assert res.exit_code == 0
    assert "no journey replays against this build" in seen["comment"]
    assert "::warning::PreScale: no journey replays" in res.output
    _wire(monkeypatch, raises=NoJourneyReplaysError([]))
    assert _ci(tmp_path, "--stale", "fail").exit_code == 1


def test_ci_refuses_journey_writes_on_a_preview_host(monkeypatch, tmp_path):
    _wire(monkeypatch, result=_journey_result())
    res = CliRunner().invoke(cli, ["ci", "https://preview.example.com", "--target", "myapp.com",
                                   "--dir", _dir(tmp_path)])
    assert res.exit_code == 2
    assert "--allow-writes preview.example.com" in " ".join(res.output.split())


# --- review fixes --------------------------------------------------------------------

def _runs(outcomes):
    runs = []
    for name, status in outcomes:
        j = parse({**BROWSE, "name": name})
        c = JourneyCheck(j)
        c.steps = [StepCheck(j.steps[0], status=status, problem=f"returned {status}"
                             if status else "couldn't reach the app (ConnectError)")]
        runs.append(JourneyRun(j, c))
    return runs


def test_an_app_that_doesnt_answer_fails_the_check_even_with_stale_warn(monkeypatch, tmp_path):
    _wire(monkeypatch, raises=NoJourneyReplaysError(_runs([("a", None), ("b", 404)])))
    res = _ci(tmp_path)
    assert res.exit_code == 1
    assert "::error::PreScale: a failed with a single user" in res.output


def test_a_5xx_with_one_user_fails_the_check(monkeypatch, tmp_path):
    _wire(monkeypatch, raises=NoJourneyReplaysError(_runs([("a", 500)])))
    assert _ci(tmp_path).exit_code == 1
    result = _journey_result()
    result["journeys"][1] = {"name": "browse", "type": "browse", "weight": 60,
                             "status": "error", "reason": "step 1 (home): returned 500"}
    _wire(monkeypatch, result=result)
    res = _ci(tmp_path)
    assert res.exit_code == 1
    assert "::error::PreScale: browse failed with a single user" in res.output


def test_only_stale_follows_the_stale_policy(monkeypatch, tmp_path):
    _wire(monkeypatch, raises=NoJourneyReplaysError(_runs([("a", 404)])))
    assert _ci(tmp_path).exit_code == 0


def test_comment_text_from_files_and_apps_cant_mention_render_html_or_break_code():
    result = _journey_result(stale=True)
    result["journeys"][1]["reason"] = "returned 422 for @octocat <img src=x> | ok"
    result["journeys"][0]["culprit_step"]["route"] = "POST /a`b"
    body = ci_mod.render_comment(result, _upload(mode="journeys"), target="t", sha=None)
    assert "@octocat" not in body and "@​octocat" in body
    assert "<img" not in body and "&lt;img src=x&gt;" in body
    assert "\\| ok" in body
    assert "`POST /a'b`" in body


def test_refusals_are_annotated(monkeypatch, tmp_path):
    _wire(monkeypatch, result=_journey_result())
    res = CliRunner().invoke(cli, ["ci", "https://preview.example.com", "--target", "t",
                                   "--dir", _dir(tmp_path)])
    assert res.exit_code == 2
    assert "::error::PreScale refused to replay the journeys" in res.output
