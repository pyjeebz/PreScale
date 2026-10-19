"""Tests for the opt-in hosted-app bridge: credentials, headers, upload, login."""

import asyncio
import json
import os
import stat

import httpx
import pytest
from click.testing import CliRunner

from prescale_cli import cloud
from prescale_cli.investigate import investigate
from prescale_cli.loadtest import client_headers, run_loadtest
from prescale_cli.main import cli
from prescale_cli.result import write_result

SECRET = "bypass-secret-123"


@pytest.fixture(autouse=True)
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv("PRESCALE_CONFIG_DIR", str(tmp_path / "config"))
    monkeypatch.delenv("PRESCALE_TOKEN", raising=False)
    monkeypatch.delenv("PRESCALE_URL", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.delenv("SSH_CONNECTION", raising=False)


def _result(run_id="20261015T120000Z-abc123"):
    return {
        "schema_version": 1, "kind": "run", "id": run_id, "tool_version": "0.2.1",
        "created_at": "2026-10-15T12:00:00Z",
        "target": {"url": "https://staging.myapp.com", "host": "staging.myapp.com",
                   "routes": ["/"]},
        "config": {}, "verdict": {"survives_users": 90}, "stages": [],
        "warning": None, "environment": {"git_commit": None, "git_branch": None},
    }


# --- headers ----------------------------------------------------------------

def test_parse_headers_accepts_name_value_pairs():
    parsed = cloud.parse_headers(("x-vercel-protection-bypass: abc", "Authorization:Bearer t"))
    assert parsed == {"x-vercel-protection-bypass": "abc", "Authorization": "Bearer t"}


@pytest.mark.parametrize("raw", ["no-colon", ": value", "bad name: v"])
def test_parse_headers_rejects_malformed(raw):
    with pytest.raises(ValueError):
        cloud.parse_headers((raw,))


def test_client_headers_keeps_user_agent():
    headers = client_headers({"x-extra": "1"})
    assert headers["x-extra"] == "1"
    assert headers["User-Agent"].startswith("prescale/")


def test_extra_headers_reach_the_target():
    seen = []

    def handler(request):
        seen.append(request.headers.get("x-vercel-protection-bypass"))
        return httpx.Response(200, text="ok")

    asyncio.run(run_loadtest(
        ["http://t.local/"], levels=[1], stage_seconds=0.05, warmup=False,
        transport=httpx.MockTransport(handler), headers={"x-vercel-protection-bypass": SECRET}))
    assert seen and all(value == SECRET for value in seen)


def test_header_values_never_land_in_the_result(tmp_path):
    transport = httpx.MockTransport(lambda req: httpx.Response(200, text="ok"))
    result = asyncio.run(investigate(
        "http://t.local/", max_users=2, stage_seconds=0.05, store=tmp_path,
        transport=transport, headers={"x-vercel-protection-bypass": SECRET}))
    assert SECRET not in json.dumps(result)
    saved = next((tmp_path / "runs").glob("*.json")).read_text()
    assert SECRET not in saved


def test_run_rejects_malformed_header():
    result = CliRunner().invoke(cli, ["run", "http://localhost:1", "-H", "nope"])
    assert result.exit_code == 2
    assert "isn't a header" in result.output


# --- credentials --------------------------------------------------------------

def test_save_and_load_credentials_private_file():
    path = cloud.save_credentials("app.example.com/", "psk_abc")
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    creds = cloud.load_credentials()
    assert creds == cloud.Credentials(url="https://app.example.com", token="psk_abc",
                                      source="file")


def test_env_token_overrides_saved_login(monkeypatch):
    cloud.save_credentials("https://app.example.com", "psk_file")
    monkeypatch.setenv("PRESCALE_TOKEN", "psk_env")
    monkeypatch.setenv("PRESCALE_URL", "http://localhost:3001")
    creds = cloud.load_credentials()
    assert (creds.token, creds.url, creds.source) == ("psk_env", "http://localhost:3001", "env")


def test_clear_credentials():
    cloud.save_credentials("https://app.example.com", "psk_abc")
    assert cloud.clear_credentials() is True
    assert cloud.load_credentials() is None
    assert cloud.clear_credentials() is False


def test_require_credentials_explains_how_to_log_in():
    with pytest.raises(cloud.CloudError, match="prescale login"):
        cloud.require_credentials()


# --- API calls ------------------------------------------------------------------

CREDS = cloud.Credentials(url="https://app.example.com", token="psk_abc", source="file")


def test_upload_sends_the_result_unchanged_with_bearer_token(monkeypatch):
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    captured = {}

    def handler(request):
        captured["auth"] = request.headers["authorization"]
        captured["source"] = request.headers["x-prescale-source"]
        captured["path"] = request.url.path
        captured["body"] = json.loads(request.content)
        return httpx.Response(201, json={"id": "x", "url": "u", "created": True, "target": {}})

    response = cloud.upload_result(_result(), CREDS, transport=httpx.MockTransport(handler))
    assert response["created"] is True
    assert captured == {"auth": "Bearer psk_abc", "source": "action",
                        "path": "/api/v1/results", "body": _result()}


def test_api_paths_keep_the_dashboard_prefix():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        return httpx.Response(200, json={"user": {}})

    creds = cloud.Credentials(url="https://prescale.dev/dashboard", token="psk_abc", source="file")
    cloud.whoami(creds, transport=httpx.MockTransport(handler))
    assert seen == ["https://prescale.dev/dashboard/api/v1/whoami"]


def test_rejected_token_points_at_login():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json={"error": "Invalid or revoked token."}))
    with pytest.raises(cloud.CloudError, match="Invalid or revoked token. Run `prescale login`"):
        cloud.whoami(CREDS, transport=transport)


def test_server_error_message_is_surfaced():
    transport = httpx.MockTransport(
        lambda req: httpx.Response(422, json={"error": "verdict.survives_users is missing"}))
    with pytest.raises(cloud.CloudError, match="survives_users"):
        cloud.upload_result(_result(), CREDS, transport=transport)


def test_unreachable_app_is_a_cloud_error():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(cloud.CloudError, match="Couldn't reach"):
        cloud.whoami(CREDS, transport=httpx.MockTransport(handler))


# --- commands ---------------------------------------------------------------------

def test_upload_dry_run_prints_the_saved_file_and_sends_nothing(tmp_path, monkeypatch):
    write_result(_result(), store=tmp_path)
    monkeypatch.setattr("prescale_cli.commands.upload.upload_result",
                        lambda *a, **k: pytest.fail("dry run must not upload"))
    result = CliRunner().invoke(cli, ["upload", "--dry-run", "--store", str(tmp_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload == _result()


def test_upload_without_login_fails_cleanly(tmp_path):
    write_result(_result(), store=tmp_path)
    result = CliRunner().invoke(cli, ["upload", "--store", str(tmp_path)])
    assert result.exit_code == 1
    assert "Not logged in" in result.output


def test_upload_latest_run(tmp_path, monkeypatch):
    write_result(_result(), store=tmp_path)
    cloud.save_credentials("https://app.example.com", "psk_abc")
    sent = []

    def fake_upload(result, creds):
        sent.append((result["id"], creds.token))
        return {"id": result["id"], "url": "https://app.example.com/runs/x", "created": True,
                "target": {"hostname": "staging.myapp.com", "created": True, "verified": False}}

    monkeypatch.setattr("prescale_cli.commands.upload.upload_result", fake_upload)
    result = CliRunner().invoke(cli, ["upload", "--store", str(tmp_path)])
    assert result.exit_code == 0, result.output
    assert sent == [("20261015T120000Z-abc123", "psk_abc")]
    assert "Uploaded" in result.output
    assert "New target staging.myapp.com" in result.output


def test_run_upload_without_login_fails_before_sending_load(monkeypatch):
    monkeypatch.setattr("prescale_cli.commands.run.run_loadtest",
                        lambda *a, **k: pytest.fail("must not load-test"))
    result = CliRunner().invoke(cli, ["run", "http://localhost:1", "--upload"])
    assert result.exit_code == 1
    assert "Not logged in" in result.output


def test_login_rejects_non_prescale_token():
    result = CliRunner().invoke(cli, ["login", "--token", "ghp_nope"])
    assert result.exit_code == 1
    assert "psk_" in result.output
    assert cloud.load_credentials() is None


def test_login_verifies_then_saves(monkeypatch):
    monkeypatch.setattr("prescale_cli.commands.login.whoami",
                        lambda creds: {"user": {"login": "pyjeebz"}})
    result = CliRunner().invoke(cli, ["login", "--token", "psk_abc", "--url",
                                      "http://localhost:3001"])
    assert result.exit_code == 0, result.output
    assert "@pyjeebz" in result.output
    assert cloud.load_credentials().url == "http://localhost:3001"


def test_login_failure_saves_nothing(monkeypatch):
    def reject(creds):
        raise cloud.CloudError("Invalid or revoked token.")

    monkeypatch.setattr("prescale_cli.commands.login.whoami", reject)
    result = CliRunner().invoke(cli, ["login", "--token", "psk_bad"])
    assert result.exit_code == 1
    assert cloud.load_credentials() is None


# --- browser sign-in ----------------------------------------------------------

_LOGIN = cloud.DeviceLogin(
    device_code="secret-device-code-1234567890", user_code="WDJB-MJHT",
    verification_url="http://localhost:3001/dashboard/cli",
    verification_url_complete="http://localhost:3001/dashboard/cli?code=WDJB-MJHT",
    expires_in=600, interval=2,
)


def test_device_login_round_trip_over_http():
    polls = iter([(400, {"error": "authorization_pending"}),
                  (200, {"token": "psk_new", "user": {"login": "pyjeebz"}})])

    def handler(request):
        if request.url.path.endswith("/api/v1/auth/device"):
            body = json.loads(request.content)
            assert body == {"device_name": "laptop", "platform": "Linux 6.6"}
            return httpx.Response(200, json={
                "device_code": _LOGIN.device_code, "user_code": _LOGIN.user_code,
                "verification_url": _LOGIN.verification_url,
                "verification_url_complete": _LOGIN.verification_url_complete,
                "expires_in": 600, "interval": 2})
        assert json.loads(request.content) == {"device_code": _LOGIN.device_code}
        status, payload = next(polls)
        return httpx.Response(status, json=payload)

    transport = httpx.MockTransport(handler)
    url = "http://localhost:3001/dashboard"
    login = cloud.start_device_login(url, "laptop", "Linux 6.6", transport=transport)
    assert login == _LOGIN
    assert cloud.poll_device_login(url, login.device_code, transport=transport)[0] == \
        "authorization_pending"
    status, data = cloud.poll_device_login(url, login.device_code, transport=transport)
    assert (status, data["token"]) == ("approved", "psk_new")


def test_device_login_on_an_older_app_points_at_paste():
    transport = httpx.MockTransport(lambda request: httpx.Response(404, text="Not found"))
    with pytest.raises(cloud.CloudError, match="--paste"):
        cloud.start_device_login("http://old.example", "laptop", "Linux", transport=transport)


def _browser_login(monkeypatch, polls, opened=None):
    replies = iter(polls)
    sleeps = []
    monkeypatch.setattr("prescale_cli.commands.login.start_device_login",
                        lambda url, name, platform: _LOGIN)
    monkeypatch.setattr("prescale_cli.commands.login.poll_device_login",
                        lambda url, code: next(replies))
    monkeypatch.setattr("prescale_cli.commands.login.time.sleep", sleeps.append)
    monkeypatch.setattr("prescale_cli.commands.login.webbrowser.open",
                        lambda link: (opened.append(link) if opened is not None else None) or True)
    return sleeps


def test_login_approved_in_browser_saves_token(monkeypatch):
    opened = []
    sleeps = _browser_login(monkeypatch, [
        ("authorization_pending", {}),
        ("slow_down", {}),
        ("approved", {"token": "psk_from_browser", "user": {"login": "pyjeebz"}}),
    ], opened)
    result = CliRunner().invoke(cli, ["login", "--url", "http://localhost:3001/dashboard"])
    assert result.exit_code == 0, result.output
    assert "WDJB-MJHT" in result.output and "@pyjeebz" in result.output
    assert opened == [_LOGIN.verification_url_complete]
    assert sleeps == [2, 2, 7]  # slow_down adds 5 seconds to the interval
    creds = cloud.load_credentials()
    assert (creds.url, creds.token) == ("http://localhost:3001/dashboard", "psk_from_browser")


def test_login_cancelled_in_browser_saves_nothing(monkeypatch):
    _browser_login(monkeypatch, [("access_denied", {"message": "cancelled"})])
    result = CliRunner().invoke(cli, ["login"])
    assert result.exit_code == 1
    assert "Cancelled in the browser" in result.output
    assert cloud.load_credentials() is None


def test_login_expired_code_saves_nothing(monkeypatch):
    _browser_login(monkeypatch, [("expired_token", {"message": "The login code expired."})])
    result = CliRunner().invoke(cli, ["login"])
    assert result.exit_code == 1
    assert "expired" in result.output
    assert cloud.load_credentials() is None


def test_login_over_ssh_prints_the_link_instead_of_opening_a_browser(monkeypatch):
    monkeypatch.setenv("SSH_CONNECTION", "10.0.0.1 22 10.0.0.2 22")
    opened = []
    _browser_login(monkeypatch, [("approved", {"token": "psk_x", "user": {}})], opened)
    result = CliRunner().invoke(cli, ["login"])
    assert result.exit_code == 0, result.output
    assert opened == []
    assert _LOGIN.verification_url_complete in result.output.replace("\n", "")


def test_login_paste_keeps_the_token_flow(monkeypatch):
    monkeypatch.setattr("prescale_cli.commands.login.whoami",
                        lambda creds: {"user": {"login": "pyjeebz"}})
    result = CliRunner().invoke(cli, ["login", "--paste"], input="psk_pasted\n")
    assert result.exit_code == 0, result.output
    assert cloud.load_credentials().token == "psk_pasted"
