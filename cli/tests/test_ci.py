"""Tests for `prescale ci`: GitHub context, PR lookup, the comment, the command."""

import json

import httpx
import pytest
from click.testing import CliRunner

from prescale_cli import ci as ci_mod
from prescale_cli.main import cli
from prescale_cli.result import _git_environment

SHA = "a41f9c2" + "0" * 33


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    for name in ("GITHUB_ACTIONS", "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_REPOSITORY",
                 "GITHUB_SHA", "GITHUB_REF", "GITHUB_HEAD_REF", "GITHUB_TOKEN",
                 "GITHUB_STEP_SUMMARY", "PRESCALE_HEADERS", "PRESCALE_PATHS",
                 "PRESCALE_GIT_COMMIT", "PRESCALE_GIT_BRANCH", "PRESCALE_TARGET"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PRESCALE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.setenv("PRESCALE_TOKEN", "psk_test")


def _event(tmp_path, payload):
    path = tmp_path / "event.json"
    path.write_text(json.dumps(payload))
    return str(path)


def _deployment(environment="Preview", state="success", ref="feat/search"):
    return {
        "deployment_status": {"state": state,
                              "environment_url": "https://myapp-a1b2c3-acme.vercel.app"},
        "deployment": {"sha": SHA, "ref": ref, "environment": environment},
    }


def _result(survives=100, onset=150, investigation=True):
    result = {
        "id": "20261015T120000Z-abc123",
        "target": {"url": "https://myapp-a1b2c3-acme.vercel.app",
                   "host": "myapp-a1b2c3-acme.vercel.app"},
        "verdict": {"survives_users": survives, "max_tested": 300, "onset_users": onset,
                    "onset_reason": "errors" if onset else None,
                    "culprit_route": "/api/search" if onset else None, "peak_rps": 588.4,
                    "confidence": {"survives_low": 85, "survives_high": 115, "stable": True}},
        "environment": {"git_commit": "a41f9c2", "git_branch": "feat/search"},
    }
    if investigation:
        result["investigation"] = {
            "bottleneck_class": "connection_pool", "confidence": "high",
            "summary": "5xx under load while static assets held.",
            "remediation": ["Increase the DB/upstream connection-pool size."],
        }
    return result


def _upload(kind="regressed", pct=-0.333, verified=True):
    comparison = None if kind is None else {
        "kind": kind, "pct": pct, "delta": -50, "confident": kind == "regressed",
        "against": "main @ 71aa0c9",
        "baseline": {"id": "b", "survives": 150, "low": 130, "high": 170, "peakRps": 640.0,
                     "commit": "71aa0c9", "branch": "main"},
    }
    return {"id": "20261015T120000Z-abc123", "url": "https://prescale.dev/dashboard/runs/x",
            "created": True, "comparison": comparison,
            "target": {"hostname": "staging.myapp.com", "verified": verified,
                       "url": "https://prescale.dev/dashboard/targets/t",
                       "baselineBranch": "main", "status": "critical"}}


# --- context ----------------------------------------------------------------------

def test_deployment_status_context(tmp_path):
    ctx = ci_mod.github_context({
        "GITHUB_EVENT_NAME": "deployment_status", "GITHUB_REPOSITORY": "acme/app",
        "GITHUB_EVENT_PATH": _event(tmp_path, _deployment()),
    })
    assert ctx.deployment_url == "https://myapp-a1b2c3-acme.vercel.app"
    assert (ctx.sha, ctx.short_sha, ctx.branch) == (SHA, "a41f9c2", "feat/search")
    assert ctx.deployment_state == "success" and not ctx.is_production


def test_deployment_ref_that_is_a_sha_is_not_a_branch(tmp_path):
    ctx = ci_mod.github_context({
        "GITHUB_EVENT_NAME": "deployment_status",
        "GITHUB_EVENT_PATH": _event(tmp_path, _deployment(ref=SHA)),
    })
    assert ctx.branch is None


def test_production_deploy_is_recognized(tmp_path):
    ctx = ci_mod.github_context({
        "GITHUB_EVENT_NAME": "deployment_status",
        "GITHUB_EVENT_PATH": _event(tmp_path, _deployment(environment="Production")),
    })
    assert ctx.is_production


def test_pull_request_and_push_contexts(tmp_path):
    pr = ci_mod.github_context({
        "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_EVENT_PATH": _event(tmp_path, {"pull_request": {
            "number": 42, "head": {"sha": SHA, "ref": "fix/pool"}}}),
    })
    assert (pr.pr_number, pr.branch, pr.sha) == (42, "fix/pool", SHA)
    push = ci_mod.github_context({"GITHUB_EVENT_NAME": "push", "GITHUB_REF": "refs/heads/main",
                                  "GITHUB_SHA": SHA})
    assert (push.branch, push.pr_number) == ("main", None)


# --- GitHub API ------------------------------------------------------------------

CTX = ci_mod.GitHubContext(repository="acme/app", sha=SHA)


def test_find_pull_request_prefers_the_open_pr_for_this_head():
    def handler(request):
        assert request.url.path == f"/repos/acme/app/commits/{SHA}/pulls"
        return httpx.Response(200, json=[
            {"number": 7, "state": "closed", "head": {"sha": SHA}},
            {"number": 41, "state": "open", "head": {"sha": "other"}},
            {"number": 42, "state": "open", "head": {"sha": SHA, "ref": "fix/pool"}},
        ])

    pr = ci_mod.find_pull_request(CTX, "ghs_x", transport=httpx.MockTransport(handler))
    assert pr["number"] == 42


def test_upsert_creates_then_updates_one_comment():
    comments: list[dict] = [{"id": 1, "body": "someone else's comment"}]

    def handler(request):
        if request.method == "GET":
            return httpx.Response(200, json=comments)
        if request.method == "POST":
            comments.append({"id": 2, "body": json.loads(request.content)["body"]})
            return httpx.Response(201, json=comments[-1])
        if request.method == "PATCH":
            assert request.url.path == "/repos/acme/app/issues/comments/2"
            comments[1]["body"] = json.loads(request.content)["body"]
            return httpx.Response(200, json=comments[1])
        raise AssertionError(request.method)

    transport = httpx.MockTransport(handler)
    marker = ci_mod.comment_marker("staging.myapp.com")
    assert ci_mod.upsert_pr_comment(CTX, "t", 42, f"{marker}\nv1", marker,
                                    transport=transport) == "created"
    assert ci_mod.upsert_pr_comment(CTX, "t", 42, f"{marker}\nv2", marker,
                                    transport=transport) == "updated"
    assert len(comments) == 2 and comments[1]["body"].endswith("v2")


# --- the comment --------------------------------------------------------------------

def test_regression_comment_has_change_culprit_cause_and_fix():
    body = ci_mod.render_comment(_result(), _upload(), target="staging.myapp.com", sha=SHA)
    assert body.startswith("<!-- prescale:capacity:staging.myapp.com -->")
    assert "### 🔴 Capacity regressed: 150 → 100 users (−33%)" in body
    assert "vs `main @ 71aa0c9`" in body
    assert "| baseline | ~150 | 130–170 | 640 | `71aa0c9` |" in body
    assert "| this deploy | ~100 | 85–115 | 588 | `a41f9c2` |" in body
    assert "**Breaks first:** `/api/search` · errors climbed at ~150 users" in body
    assert "`connection_pool` (high confidence)" in body
    assert "- Increase the DB/upstream connection-pool size." in body
    assert "[Open the run](https://prescale.dev/dashboard/runs/x)" in body
    assert "Measured on a preview deploy" in body


def test_replica_comment_says_it_measured_a_build_not_a_deploy():
    result = _result()
    result["config"] = {"replica": True}
    body = ci_mod.render_comment(result, _upload(), target="staging.myapp.com", sha=SHA)
    assert "| this build | ~100 |" in body and "this deploy" not in body
    assert "Measured on a build of this commit in CI" in body
    assert "preview deploy" not in body


def test_possible_regression_says_it_may_be_noise():
    body = ci_mod.render_comment(_result(), _upload(kind="possible"),
                                 target="staging.myapp.com", sha=SHA)
    assert "🟠 Possible capacity regression" in body and "may be noise" in body


def test_first_run_comment_explains_the_baseline():
    body = ci_mod.render_comment(_result(onset=None, investigation=False), _upload(kind=None),
                                 target="staging.myapp.com", sha=SHA)
    assert "First capacity run" in body
    assert "No `main` baseline yet" in body
    assert "**Held:**" in body


def test_unverified_target_is_called_out():
    body = ci_mod.render_comment(_result(), _upload(verified=False),
                                 target="staging.myapp.com", sha=SHA)
    assert "isn't verified yet" in body


# --- the command -------------------------------------------------------------------

def _github_env(monkeypatch, tmp_path, payload):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_EVENT_NAME", "deployment_status")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/app")
    monkeypatch.setenv("GITHUB_EVENT_PATH", _event(tmp_path, payload))
    monkeypatch.setenv("GITHUB_TOKEN", "ghs_x")
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    return summary


def test_ci_skips_production_without_load(monkeypatch, tmp_path):
    _github_env(monkeypatch, tmp_path, _deployment(environment="Production"))
    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate",
                        lambda *a, **k: pytest.fail("must not load-test production"))
    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert result.exit_code == 0
    assert "production" in result.output


def test_ci_ignores_unfinished_deploys(monkeypatch, tmp_path):
    _github_env(monkeypatch, tmp_path, _deployment(state="pending"))
    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate",
                        lambda *a, **k: pytest.fail("must not run"))
    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert result.exit_code == 0


def test_ci_full_flow_comments_and_fails_on_regression(monkeypatch, tmp_path):
    summary = _github_env(monkeypatch, tmp_path, _deployment())
    monkeypatch.setenv("PRESCALE_HEADERS", "x-vercel-protection-bypass: s3cret\n")
    seen = {}

    async def fake_investigate(url, **kwargs):
        seen["url"], seen["headers"] = url, kwargs["headers"]
        seen["env"] = _git_environment()
        return _result()

    def fake_upload(result, creds, *, pr, target):
        seen["pr"], seen["target"] = pr, target
        return _upload()

    def fake_upsert(ctx, token, pr_number, body, marker):
        seen["comment"] = (pr_number, body)
        return "created"

    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate", fake_investigate)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result", fake_upload)
    monkeypatch.setattr("prescale_cli.commands.ci.upsert_pr_comment", fake_upsert)
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request",
                        lambda ctx, token: {"number": 42, "head": {"ref": "feat/search"}})

    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com",
                                      "--fail-on-regression"])
    assert result.exit_code == 1, result.output
    assert seen["url"] == "https://myapp-a1b2c3-acme.vercel.app"
    assert seen["headers"] == {"x-vercel-protection-bypass": "s3cret"}
    assert seen["env"] == {"git_commit": "a41f9c2", "git_branch": "feat/search"}
    assert (seen["pr"], seen["target"]) == (42, "staging.myapp.com")
    assert seen["comment"][0] == 42 and "Capacity regressed" in seen["comment"][1]
    assert "Capacity regressed" in summary.read_text()
    assert "::error::Capacity regressed" in result.output
    assert "s3cret" not in result.output


def test_ci_without_fail_flag_reports_but_passes(monkeypatch, tmp_path):
    _github_env(monkeypatch, tmp_path, _deployment())

    async def fake_investigate(url, **kwargs):
        return _result()

    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate", fake_investigate)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result", lambda *a, **k: _upload())
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request", lambda ctx, token: None)
    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert result.exit_code == 0, result.output
    assert "No open PR" in result.output


def test_ci_needs_a_url_outside_deployment_events():
    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert result.exit_code == 2
    assert "No URL to test" in result.output


def test_git_env_override(monkeypatch):
    monkeypatch.setenv("PRESCALE_GIT_COMMIT", "abc1234")
    monkeypatch.setenv("PRESCALE_GIT_BRANCH", "feat/x")
    assert _git_environment() == {"git_commit": "abc1234", "git_branch": "feat/x"}


def test_ci_defaults_to_a_gentle_ramp_and_reports_requests(monkeypatch, tmp_path):
    _github_env(monkeypatch, tmp_path, _deployment())
    seen = {}

    async def fake_investigate(url, **kwargs):
        seen["max_users"] = kwargs["max_users"]
        result = _result()
        result["stages"] = [{"total": 1200}, {"total": 3400}]
        return result

    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate", fake_investigate)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result",
                        lambda *a, **k: _upload("steady", 0.0))
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request", lambda ctx, token: None)
    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert result.exit_code == 0, result.output
    assert seen["max_users"] == 100
    assert "Ramp: up to 100 users" in result.output
    assert "Sent 4,600 requests" in result.output


def test_ci_skips_a_restricted_host_and_says_why_on_the_pr(monkeypatch, tmp_path):
    from prescale_cli.hosts import VERCEL
    from prescale_cli.loadtest import HostPolicyError

    summary = _github_env(monkeypatch, tmp_path, _deployment())
    seen = {}

    async def fake_investigate(url, **kwargs):
        seen["host_permission"] = kwargs["host_permission"]
        raise HostPolicyError(VERCEL)

    def fake_upsert(ctx, token, pr_number, body, marker):
        seen["comment"] = (pr_number, body, marker)
        return "created"

    def no_upload(*args, **kwargs):
        raise AssertionError("nothing to upload when no load was sent")

    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate", fake_investigate)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result", no_upload)
    monkeypatch.setattr("prescale_cli.commands.ci.upsert_pr_comment", fake_upsert)
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request",
                        lambda ctx, token: {"number": 42, "head": {"ref": "feat/search"}})

    result = CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com",
                                      "--fail-on-regression"])
    assert result.exit_code == 0, result.output  # nobody's CI breaks
    assert seen["host_permission"] is False
    number, body, marker = seen["comment"]
    assert number == 42 and marker in body
    assert "PreScale skipped this deploy" in body and "host-permission: true" in body
    assert "Enterprise plans" in summary.read_text()
    assert "::notice::PreScale skipped this Vercel deploy" in result.output


def test_ci_host_permission_flag_reaches_the_test(monkeypatch, tmp_path):
    _github_env(monkeypatch, tmp_path, _deployment())
    seen = {}

    async def fake_investigate(url, **kwargs):
        seen["host_permission"] = kwargs["host_permission"]
        return _result()

    monkeypatch.setattr("prescale_cli.commands.ci.run_investigate", fake_investigate)
    monkeypatch.setattr("prescale_cli.commands.ci.upload_result",
                        lambda result, creds, *, pr, target: _upload())
    monkeypatch.setattr("prescale_cli.commands.ci.upsert_pr_comment",
                        lambda *args, **kwargs: "created")
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request", lambda ctx, token: None)
    monkeypatch.setenv("PRESCALE_HOST_PERMISSION", "1")
    CliRunner().invoke(cli, ["ci", "--target", "staging.myapp.com"])
    assert seen["host_permission"] is True


def test_ci_replica_mode_starts_tests_and_stops_the_app(monkeypatch, tmp_path):
    import shlex
    import socket
    import sys

    _github_env(monkeypatch, tmp_path, _deployment())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/"
    seen = {}

    def fake_upload(result, creds, *, pr, target):
        seen["result"] = result
        return _upload()

    monkeypatch.setattr("prescale_cli.commands.ci.upload_result", fake_upload)
    monkeypatch.setattr("prescale_cli.commands.ci.upsert_pr_comment",
                        lambda *args, **kwargs: "created")
    monkeypatch.setattr("prescale_cli.commands.ci.find_pull_request", lambda ctx, token: None)
    app = f"{shlex.quote(sys.executable)} -m http.server {port} --bind 127.0.0.1"
    result = CliRunner().invoke(cli, ["ci", url, "--target", "myapp.com", "--app", app,
                                      "-u", "2", "-s", "0.2", "--store", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert "Previews often share" not in result.output  # it's a local build, not a preview
    assert seen["result"]["config"]["replica"] is True
    assert "http.server" not in str(seen["result"])  # the command is never uploaded
    with pytest.raises(httpx.HTTPError):
        httpx.get(url, timeout=1.0)  # stopped after the run
