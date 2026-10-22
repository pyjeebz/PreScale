"""Hosts that restrict load testing (Vercel, Netlify, Cloudflare): PreScale checks
the first response and sends no load without the user's permission."""

import asyncio
import io
import itertools

import httpx
import pytest
from click.testing import CliRunner
from rich.console import Console

from prescale_cli import mcp_tools
from prescale_cli.commands.hostcheck import confirm_host
from prescale_cli.hosts import CLOUDFLARE, NETLIFY, VERCEL, detect_host, refusal
from prescale_cli.loadtest import HostPolicyError, default_levels, run_loadtest
from prescale_cli.main import cli


def test_hosts_are_recognised_from_their_headers():
    assert detect_host(httpx.Headers({"x-vercel-id": "iad1::abc"})) is VERCEL
    assert detect_host(httpx.Headers({"server": "Vercel"})) is VERCEL
    assert detect_host(httpx.Headers({"x-nf-request-id": "01H"})) is NETLIFY
    assert detect_host(httpx.Headers({"server": "Netlify"})) is NETLIFY
    assert detect_host(httpx.Headers({"cf-ray": "8a1b-YUL"})) is CLOUDFLARE
    assert detect_host(httpx.Headers({"server": "cloudflare"})) is CLOUDFLARE


def test_other_hosts_are_not_restricted():
    for headers in ({"server": "nginx"}, {"server": "gunicorn"}, {}):
        assert detect_host(httpx.Headers(headers)) is None
    assert detect_host(None) is None


def test_the_platform_closest_to_the_app_wins():
    behind_cloudflare = httpx.Headers({"cf-ray": "8a1b", "x-vercel-id": "iad1::abc"})
    assert detect_host(behind_cloudflare) is VERCEL


def test_the_refusal_names_the_rule_the_way_out_and_the_alternative():
    message = refusal(VERCEL)
    assert "Enterprise plans" in message and VERCEL.link in message
    assert "--host-permission" in message and "staging you're allowed to load" in message


def _counting_vercel():
    calls = itertools.count()

    def handler(request):
        next(calls)
        return httpx.Response(200, headers={"x-vercel-id": "iad1::abc"}, text="ok")

    return calls, httpx.MockTransport(handler)


def _ramp(transport, **kwargs):
    return asyncio.run(run_loadtest(["https://x.test/"], levels=default_levels(5),
                                    stage_seconds=0.05, transport=transport, **kwargs))


def test_no_load_without_permission_only_the_preflight():
    calls, transport = _counting_vercel()
    with pytest.raises(HostPolicyError) as raised:
        _ramp(transport)
    assert raised.value.rule is VERCEL
    assert next(calls) == 1  # only the preflight went out


def test_permission_lets_the_test_run():
    calls, transport = _counting_vercel()
    stages, _ = _ramp(transport, host_permission=True)
    assert stages and next(calls) > 10


def test_confirm_host_skips_the_probe_when_permission_is_given(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("probed despite permission")

    monkeypatch.setattr("prescale_cli.commands.hostcheck.probe_host", fail)
    confirm_host("https://x.test", console=_console(), permitted=True, as_json=False)


def test_confirm_host_refuses_in_json_mode(monkeypatch):
    _restricted(monkeypatch)
    with pytest.raises(SystemExit) as stopped:
        confirm_host("https://x.test", console=_console(), permitted=False, as_json=True)
    assert stopped.value.code == 1


def test_confirm_host_asks_and_no_means_no(monkeypatch):
    _restricted(monkeypatch)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    asked = {}

    def answer(question, default):
        asked["question"], asked["default"] = question, default
        return False

    monkeypatch.setattr("prescale_cli.commands.hostcheck.click.confirm", answer)
    with pytest.raises(SystemExit) as stopped:
        confirm_host("https://x.test", console=_console(), permitted=False, as_json=False)
    assert stopped.value.code == 0
    assert asked == {"question": "Do you have Vercel's permission to load-test this site?",
                     "default": False}


def test_run_command_refuses_a_vercel_site_without_permission(monkeypatch, tmp_path):
    _restricted(monkeypatch)
    result = CliRunner().invoke(cli, ["run", "https://myapp.vercel.app", "--i-own-this",
                                      "--json", "--store", str(tmp_path)])
    assert result.exit_code == 1
    assert "Vercel only permits load testing" in result.output
    assert "--host-permission" in result.output


def test_mcp_refuses_unless_the_server_was_started_with_permission(monkeypatch, tmp_path):
    monkeypatch.delenv("PRESCALE_HOST_PERMISSION", raising=False)
    _, transport = _counting_vercel()
    with pytest.raises(HostPolicyError):
        asyncio.run(mcp_tools.run_summary("https://x.test/", allow={"x.test"}, max_users=2,
                                          stage_seconds=0.02, store=tmp_path,
                                          transport=transport))
    monkeypatch.setenv("PRESCALE_HOST_PERMISSION", "1")
    _, transport = _counting_vercel()
    summary = asyncio.run(mcp_tools.run_summary("https://x.test/", allow={"x.test"},
                                                max_users=2, stage_seconds=0.02,
                                                store=tmp_path, transport=transport))
    assert summary


def _restricted(monkeypatch):
    async def probe(url, **kwargs):
        return VERCEL

    monkeypatch.setattr("prescale_cli.commands.hostcheck.probe_host", probe)


def _console():
    return Console(file=io.StringIO())
