"""Replica mode: PreScale starts the app's own build, tests it on localhost, and
stops everything it started."""

import shlex
import socket
import sys
import time

import httpx
import pytest

from prescale_cli.replica import ReplicaError, replica

PY = shlex.quote(sys.executable)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _up(url: str) -> bool:
    try:
        httpx.get(url, timeout=1.0)
    except httpx.HTTPError:
        return False
    return True


def test_starts_the_app_waits_for_it_then_stops_it(tmp_path):
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    # A shell that starts the server, like "npm run build && npm start" does.
    command = f"echo building && {PY} -m http.server {port} --bind 127.0.0.1"
    with replica(command, url, timeout=20, cwd=str(tmp_path)) as running:
        assert _up(url)
        assert running.log_path
    time.sleep(0.2)
    assert not _up(url)  # the server the shell started is gone too


def test_an_app_that_crashes_shows_its_exit_code_and_log():
    port = _free_port()
    command = f"{PY} -c \"print('missing DATABASE_URL'); raise SystemExit(3)\""
    with pytest.raises(ReplicaError, match=r"exited \(code 3\)") as raised:
        with replica(command, f"http://127.0.0.1:{port}/", timeout=20):
            pass
    assert "missing DATABASE_URL" in str(raised.value)


def test_an_app_that_never_answers_times_out_and_is_stopped():
    port = _free_port()
    command = f"{PY} -c \"import time; print('still building'); time.sleep(60)\""
    started = time.monotonic()
    with pytest.raises(ReplicaError, match="didn't answer .* within 1.5s") as raised:
        with replica(command, f"http://127.0.0.1:{port}/", timeout=1.5):
            pass
    assert "--app-timeout" in str(raised.value)
    assert time.monotonic() - started < 15  # stopped, not left running for a minute


def test_only_local_urls():
    with pytest.raises(ReplicaError, match="must be local"):
        with replica("true", "https://myapp.vercel.app/"):
            pass


def test_refuses_when_something_already_answers_there(tmp_path):
    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    with replica(f"{PY} -m http.server {port} --bind 127.0.0.1", url, timeout=20,
                 cwd=str(tmp_path)):
        with pytest.raises(ReplicaError, match="already running"):
            with replica("true", url):
                pass


def test_run_command_in_replica_mode_marks_the_result_and_hides_the_command(tmp_path):
    import json

    from click.testing import CliRunner

    from prescale_cli.main import cli

    port = _free_port()
    url = f"http://127.0.0.1:{port}/"
    secret = "s3cret-token-in-the-command"
    command = f"API_KEY={secret} {PY} -m http.server {port} --bind 127.0.0.1"
    result = CliRunner().invoke(cli, ["run", url, "--app", command, "--json", "-u", "2",
                                      "-s", "0.2", "--no-warmup", "--store", str(tmp_path)])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["config"]["replica"] is True
    assert "local replica" in data["warning"]
    assert secret not in result.output
    saved = next((tmp_path / "runs").glob("*.json")).read_text()
    assert secret not in saved and '"replica": true' in saved
    time.sleep(0.2)
    assert not _up(url)  # stopped after the run


def test_app_with_a_remote_url_is_refused_before_anything_starts(tmp_path):
    from click.testing import CliRunner

    from prescale_cli.main import cli

    result = CliRunner().invoke(cli, ["run", "https://myapp.vercel.app", "--app", "true",
                                      "--json", "--store", str(tmp_path)])
    assert result.exit_code == 1 and "must be local" in result.output
