"""Replica mode: start the app's own build, test it on localhost, stop it.

Hosts like Vercel only allow load tests by arrangement, and what breaks under
load is usually the app's code and database, not the CDN. So PreScale can start
the app itself (`--app "npm run build && npm start"`), wait until the local URL
answers, run the test against localhost, and stop everything it started. No
host is involved, so no host's rules are broken and no CDN shapes the result.

The command is never written into a Result or uploaded: it may carry secrets.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}
DEFAULT_TIMEOUT = 600.0  # a production build can take minutes
NOTE = ("Measured on a local replica: your app's own build on this machine, not your host. "
        "Serverless behaviour such as cold starts isn't included.")

_POLL_S = 0.5
_STOP_GRACE_S = 10.0
_LOG_LINES = 15


class ReplicaError(Exception):
    """The app couldn't be started, or never answered."""


@dataclass
class Replica:
    pid: int
    log_path: str


def require_local(url: str) -> None:
    host = (urlparse(url).hostname or "").lower()
    if host not in LOCAL_HOSTS:
        raise ReplicaError(f"--app runs your app on this machine, so the URL must be local "
                           f"(like http://localhost:3000), not {host or url}.")


@contextmanager
def replica(command: str, url: str, *, timeout: float = DEFAULT_TIMEOUT, cwd: str | None = None,
            on_wait=None):
    """Start `command`, wait for `url` to answer, yield, then stop the app and
    everything it started (also on errors and Ctrl-C)."""
    require_local(url)
    if _answers(url):
        raise ReplicaError(f"Something is already running at {url}. Stop it, or point the "
                           "app at another port, so PreScale tests the build it starts.")
    log = tempfile.NamedTemporaryFile(prefix="prescale-app-", suffix=".log", delete=False)
    process = _start(command, cwd, log)
    try:
        _wait_until_ready(process, url, timeout, log.name, on_wait)
        yield Replica(pid=process.pid, log_path=log.name)
    finally:
        _stop(process)
        log.close()


def _start(command: str, cwd: str | None, log) -> subprocess.Popen:
    # A new process group, so stopping it also stops what npm or a shell started.
    group = ({"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP} if sys.platform == "win32"
             else {"start_new_session": True})
    try:
        return subprocess.Popen(command, shell=True, cwd=cwd, stdout=log,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                env=os.environ.copy(), **group)
    except OSError as exc:
        raise ReplicaError(f"Couldn't start the app: {exc}") from exc


def _answers(url: str) -> bool:
    try:
        httpx.get(url, timeout=2.0)
    except httpx.HTTPError:
        return False
    return True


def _wait_until_ready(process: subprocess.Popen, url: str, timeout: float, log_path: str,
                      on_wait) -> None:
    deadline = time.monotonic() + timeout
    started = time.monotonic()
    while time.monotonic() < deadline:
        code = process.poll()
        if code is not None:
            raise ReplicaError(f"The app exited (code {code}) before {url} answered. "
                               f"The end of its log ({log_path}):\n{_tail(log_path)}")
        if _answers(url):
            return
        if on_wait:
            on_wait(time.monotonic() - started)
        time.sleep(_POLL_S)
    raise ReplicaError(f"The app didn't answer at {url} within {timeout:g}s. Raise "
                       f"--app-timeout if the build takes longer. The end of its log "
                       f"({log_path}):\n{_tail(log_path)}")


def _stop(process: subprocess.Popen) -> None:
    """Stop the app's whole process group: the shell may be gone while the server
    it started keeps running."""
    if sys.platform == "win32":
        if process.poll() is None:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(process.pid)],
                           capture_output=True, check=False)
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    deadline = time.monotonic() + _STOP_GRACE_S
    while time.monotonic() < deadline and _group_alive(process.pid):
        process.poll()  # reap the leader so it doesn't linger as a zombie
        time.sleep(0.1)
    if _group_alive(process.pid):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=_STOP_GRACE_S)
    except subprocess.TimeoutExpired:
        pass


def _group_alive(pgid: int) -> bool:
    try:
        os.killpg(pgid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tail(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return "(no log)"
    return "\n".join(lines[-_LOG_LINES:]) or "(the app printed nothing)"
