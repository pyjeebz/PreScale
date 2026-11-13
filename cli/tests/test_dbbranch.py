"""`--db neon`: a throwaway Neon branch for the replica, made and deleted around the run."""

import functools
import json
import sys
import tempfile
from pathlib import Path

import httpx
import pytest
from click.testing import CliRunner

from prescale_cli import dbbranch
from prescale_cli.dbbranch import DBBranchError, neon_branch, neon_settings
from prescale_cli.main import cli

URI = "postgresql://owner:s3cr3t-pw@ep-copy-123.us-east-2.aws.neon.tech/shop?sslmode=require"
POOLED = ("postgresql://owner:s3cr3t-pw@ep-copy-123-pooler.us-east-2.aws.neon.tech/shop"
          "?sslmode=require")


class FakeNeon:
    """Enough of Neon's API: branches, operations, databases, connection URI."""

    def __init__(self, *, databases=("shop",), op_status=("running", "finished"),
                 branches=("main", "staging"), page_size=100, delete_locked=0,
                 post_fails_after_create=False):
        self.calls: list[tuple[str, str]] = []
        self.created: dict | None = None
        self.deleted: list[str] = []
        self.databases = databases
        self.op_status = list(op_status)
        self.branches = [{"id": f"br-{n}", "name": n, "created_at": "2026-11-01T00:00:00Z"}
                         for n in branches]
        self.page_size = page_size
        self.delete_locked = delete_locked
        self.post_fails_after_create = post_fails_after_create

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/api/v2"), request.method
        self.calls.append((method, path))
        assert request.headers["authorization"] == "Bearer key-123"
        if method == "GET" and path == "/projects/p1/branches":
            search = request.url.params.get("search", "")
            found = [b for b in self.branches if search in b["name"] or search in b["id"]]
            start = int(request.url.params.get("cursor", "0"))
            page = found[start:start + self.page_size]
            more = start + self.page_size < len(found)
            return httpx.Response(200, json={
                "branches": page,
                "pagination": {"next": str(start + self.page_size)} if more else {}})
        if method == "POST" and path == "/projects/p1/branches":
            body = json.loads(request.content)
            self.created = body
            self.branches.append({"id": "br-copy", "name": body["branch"]["name"],
                                  "created_at": "2026-11-13T00:00:00Z"})
            if self.post_fails_after_create:
                return httpx.Response(500, json={"message": "oops"})
            return httpx.Response(201, json={
                "branch": {"id": "br-copy", "name": body["branch"]["name"]},
                "operations": [{"id": "op1", "status": "running"}]})
        if method == "GET" and path == "/projects/p1/operations/op1":
            status = self.op_status.pop(0) if self.op_status else "finished"
            return httpx.Response(200, json={"operation": {"id": "op1", "status": status}})
        if method == "GET" and path == "/projects/p1/branches/br-copy/databases":
            return httpx.Response(200, json={"databases": [
                {"name": d, "owner_name": "owner"} for d in self.databases]})
        if method == "GET" and path == "/projects/p1/connection_uri":
            assert request.url.params["branch_id"] == "br-copy"
            assert request.url.params["role_name"] == "owner"
            pooled = request.url.params["pooled"] == "true"
            self.uri_params = dict(request.url.params)
            return httpx.Response(200, json={"uri": POOLED if pooled else URI})
        if method == "DELETE" and path.startswith("/projects/p1/branches/"):
            if self.delete_locked:
                self.delete_locked -= 1
                return httpx.Response(423, json={"message": "locked"})
            branch = path.rsplit("/", 1)[1]
            self.deleted.append(branch)
            self.branches = [b for b in self.branches if b["id"] != branch]
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"message": "nope"})

    def transport(self):
        return httpx.MockTransport(self.handler)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(dbbranch, "_POLL_S", 0)
    monkeypatch.setattr(dbbranch, "_RETRY_SCALE", 0)


def _branch(fake, parent="staging", **kw):
    return neon_branch(parent, api_key="key-123", project="p1", transport=fake.transport(),
                       **kw)


def test_copies_the_named_branch_waits_until_ready_and_deletes_it():
    fake = FakeNeon()
    with _branch(fake) as branch:
        assert branch.uri == URI and branch.parent == "staging" and branch.database == "shop"
        assert fake.deleted == []
    body = fake.created
    assert body["branch"]["parent_id"] == "br-staging"
    assert body["branch"]["name"].startswith("prescale-")
    assert body["endpoints"] == [{"type": "read_write"}]
    assert fake.calls.count(("GET", "/projects/p1/operations/op1")) == 2  # polled until finished
    assert branch.uri == URI and branch.direct_uri == URI and branch.pooled_uri == POOLED
    assert {URI, POOLED, "s3cr3t-pw"} <= branch.secrets()
    assert fake.deleted == ["br-copy"]
    assert URI not in repr(branch) and "s3cr3t" not in repr(branch)


def test_the_copy_is_deleted_when_the_test_fails():
    fake = FakeNeon()
    with pytest.raises(KeyboardInterrupt), _branch(fake):
        raise KeyboardInterrupt
    assert fake.deleted == ["br-copy"]


def test_a_failed_creation_still_deletes_what_was_made():
    fake = FakeNeon(op_status=("failed",))
    with pytest.raises(DBBranchError, match="couldn't create the branch"), _branch(fake):
        pass
    assert fake.deleted == ["br-copy"]


def test_a_missing_parent_says_which_branches_exist_and_makes_nothing():
    fake = FakeNeon()
    with pytest.raises(DBBranchError, match="No branch named 'qa'.*main, staging"), \
            _branch(fake, parent="qa"):
        pass
    assert fake.created is None and fake.deleted == []


def test_several_databases_need_a_name_and_pooled_is_passed():
    fake = FakeNeon(databases=("shop", "analytics"))
    with pytest.raises(DBBranchError, match="--db-name"), _branch(fake):
        pass
    fake = FakeNeon(databases=("shop", "analytics"))
    with _branch(fake, database="analytics", pooled=True) as branch:
        assert branch.database == "analytics" and branch.uri == POOLED


def test_a_refused_key_is_named():
    def refuse(request):
        return httpx.Response(401, json={"message": "invalid"})
    with pytest.raises(DBBranchError, match="refused NEON_API_KEY"), \
            neon_branch("staging", api_key="k", project="p1",
                        transport=httpx.MockTransport(refuse)):
        pass


def test_settings_name_what_is_missing():
    with pytest.raises(DBBranchError, match="NEON_API_KEY and NEON_PROJECT_ID"):
        neon_settings({})
    assert neon_settings({"NEON_API_KEY": "k", "NEON_PROJECT_ID": "p"}) == ("k", "p")


# --- the command ---------------------------------------------------------------

def test_db_needs_app_and_a_parent():
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--db", "neon"])
    assert res.exit_code == 2 and "--db needs --app" in res.output
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--db", "neon", "--app", "x"])
    assert res.exit_code == 2 and "--db-parent" in res.output


def test_missing_neon_settings_stop_before_the_app_starts(monkeypatch, tmp_path):
    monkeypatch.delenv("NEON_API_KEY", raising=False)
    marker = tmp_path / "started"
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--app", f"touch {marker}",
                                   "--db", "neon", "--db-parent", "staging", "--urls"])
    assert res.exit_code == 1 and "NEON_API_KEY" in res.output
    assert not marker.exists()


APP = """
import http.server, os, sys
open(sys.argv[2], "w").write(os.environ.get("DATABASE_URL", ""))
print("connecting to", os.environ.get("DATABASE_URL"), flush=True)
if len(sys.argv) > 3:
    sys.exit(3)  # a startup failure that printed the URL
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.send_header("Content-Length", "2"); self.end_headers()
        self.wfile.write(b"ok")
    def log_message(self, *a): pass
http.server.ThreadingHTTPServer(("127.0.0.1", int(sys.argv[1])), H).serve_forever()
"""


def test_run_gives_the_app_the_copy_and_never_shows_its_url(monkeypatch, tmp_path):
    import socket
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    fake = FakeNeon()
    from prescale_cli.commands import replicaopts
    monkeypatch.setattr(replicaopts, "neon_branch",
                        functools.partial(neon_branch, transport=fake.transport()))
    monkeypatch.setenv("NEON_API_KEY", "key-123")
    monkeypatch.setenv("NEON_PROJECT_ID", "p1")
    (tmp_path / "app.py").write_text(APP)
    seen = tmp_path / "seen.txt"
    store = tmp_path / "store"
    res = CliRunner().invoke(cli, [
        "run", f"http://127.0.0.1:{port}", "--urls", "-u", "2", "-s", "0.2",
        "--app", f"{sys.executable} {tmp_path / 'app.py'} {port} {seen}",
        "--db", "neon", "--db-parent", "staging", "--json", "--store", str(store)])
    assert res.exit_code == 0, res.output
    assert seen.read_text() == URI                 # the app got the copy
    assert fake.deleted == ["br-copy"]             # and the copy is gone
    result = json.loads(res.stdout)
    assert result["config"]["database"] == {"provider": "neon", "parent": "staging",
                                            "database": "shop"}
    assert "throwaway Neon copy of staging" in result["warning"]
    saved = "".join(p.read_text() for p in store.rglob("*.json"))
    for text in (res.output, saved):
        assert "s3cr3t" not in text and "ep-copy-123" not in text


def test_skipped_operations_count_as_done():
    fake = FakeNeon(op_status=("skipped",))
    with _branch(fake) as branch:
        assert branch.uri == URI


def test_the_parent_is_found_past_the_first_page():
    fake = FakeNeon(branches=[f"preview-{i}" for i in range(30)] + ["staging"], page_size=10)
    with _branch(fake) as branch:
        assert branch.parent == "staging"
    assert fake.created["branch"]["parent_id"] == "br-staging"


def test_a_create_that_failed_after_neon_made_the_branch_still_cleans_up():
    fake = FakeNeon(post_fails_after_create=True)
    with pytest.raises(DBBranchError, match="500"), _branch(fake):
        pass
    assert fake.deleted == ["br-copy"]


def test_a_locked_delete_is_retried():
    fake = FakeNeon(delete_locked=2)
    with _branch(fake):
        pass
    assert fake.deleted == ["br-copy"]


def test_every_known_database_variable_points_at_the_copy():
    from prescale_cli.commands.replicaopts import copy_environment
    fake = FakeNeon()
    with _branch(fake) as branch:
        env = copy_environment(branch, ["DATABASE_URL", "APP_DB"], {
            "DIRECT_URL": "postgres://staging", "POSTGRES_PRISMA_URL": "postgres://staging",
            "PGHOST": "staging.example.com", "PGPASSWORD": "real", "HOME": "/root"})
    assert env["DATABASE_URL"] == env["APP_DB"] == env["POSTGRES_PRISMA_URL"] == URI
    assert env["DIRECT_URL"] == URI
    assert env["PGHOST"] == "ep-copy-123.us-east-2.aws.neon.tech"
    assert env["PGPASSWORD"] == "s3cr3t-pw" and env["PGDATABASE"] == "shop"
    assert "HOME" not in env
    # set even when unset here: an app's .env file can't win (dotenv never overrides)
    empty = copy_environment(branch, ["DATABASE_URL"], {})
    assert empty["POSTGRES_URL"] == URI and empty["DIRECT_URL"] == URI
    assert empty["PGHOST"] == "ep-copy-123.us-east-2.aws.neon.tech"


def test_other_postgres_urls_are_named():
    from prescale_cli.commands.replicaopts import other_databases
    assert other_databases({"DATABASE_URL": URI}, {
        "DATABASE_URL": "postgres://staging", "ANALYTICS_DB": "postgresql://warehouse/x",
        "HOME": "/root"}) == ["ANALYTICS_DB"]


def test_cleanup_finds_only_old_prescale_copies_and_deletes_them(monkeypatch):
    from datetime import datetime, timezone
    fake = FakeNeon(branches=("main", "staging"))
    fake.branches += [
        {"id": "br-old", "name": "prescale-20261101-000000-aaaaaa",
         "created_at": "2026-11-01T00:00:00Z"},
        {"id": "br-new", "name": "prescale-20261113-000000-bbbbbb",
         "created_at": "2026-11-13T09:00:00Z"},
        {"id": "br-x", "name": "prescale-demo",          # a user's own branch
         "created_at": "2026-10-01T00:00:00Z"},
        {"id": "br-p", "name": "prescale-20261001-000000-cccccc", "protected": True,
         "created_at": "2026-10-01T00:00:00Z"},
    ]
    now = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
    stale = dbbranch.stale_copies(api_key="key-123", project="p1", older_than_hours=6,
                                  transport=fake.transport(), now=now)
    assert {b["id"] for b in stale} == {"br-old"}  # only names PreScale generates
    assert dbbranch.delete_copies(stale, api_key="key-123", project="p1",
                                  transport=fake.transport()) == []
    assert fake.deleted == ["br-old"]
    # and delete_copies itself refuses branches PreScale didn't make, even if handed them
    not_ours = [b for b in fake.branches if b["id"] in ("br-main", "br-staging", "br-x", "br-p")]
    assert dbbranch.delete_copies(not_ours, api_key="key-123", project="p1",
                                  transport=fake.transport()) == []
    assert fake.deleted == ["br-old"]
    assert "br-staging" not in fake.deleted and "br-main" not in fake.deleted


def test_an_app_that_prints_its_url_and_dies_never_shows_the_secret(monkeypatch, tmp_path):
    fake = FakeNeon()
    from prescale_cli.commands import replicaopts
    monkeypatch.setattr(replicaopts, "neon_branch",
                        functools.partial(neon_branch, transport=fake.transport()))
    monkeypatch.setenv("NEON_API_KEY", "key-123")
    monkeypatch.setenv("NEON_PROJECT_ID", "p1")
    (tmp_path / "app.py").write_text(APP)
    res = CliRunner().invoke(cli, [
        "run", "http://127.0.0.1:9", "--urls",
        "--app", f"{sys.executable} {tmp_path / 'app.py'} 9 {tmp_path / 'seen'} die",
        "--db", "neon", "--db-parent", "staging"])
    assert res.exit_code == 1
    flat = "".join(res.output.split())   # Rich wraps long lines
    assert "connectingto***" in flat     # the log tail is shown, masked
    assert "s3cr3t" not in flat and "ep-copy-123" not in flat
    assert fake.deleted == ["br-copy"]
    leftover = list(Path(tempfile.gettempdir()).glob("prescale-app-*.log"))
    assert not any("s3cr3t" in p.read_text(errors="replace") for p in leftover)


def test_when_a_failed_create_cant_be_checked_the_user_is_told():
    fake = FakeNeon(post_fails_after_create=True)
    calls = {"n": 0}

    def flaky(request):
        if request.method == "GET" and "search=prescale-" in str(request.url):
            calls["n"] += 1
            return httpx.Response(500, json={"message": "down"})
        return fake.handler(request)
    told = []
    with pytest.raises(DBBranchError), neon_branch(
            "staging", api_key="key-123", project="p1", transport=httpx.MockTransport(flaky),
            on_delete_failed=lambda name, exc: told.append(name)):
        pass
    assert calls["n"] == 1 and told and told[0].startswith("prescale-")


def test_the_first_signal_ends_the_run_and_later_ones_cant_interrupt_cleanup():
    import signal

    import click

    from prescale_cli import replica as replica_mod
    from prescale_cli.commands.replicaopts import _guard_signals
    before = signal.getsignal(signal.SIGTERM)
    with click.Context(click.Command("x")) as ctx:
        _guard_signals(ctx)
        handler = signal.getsignal(signal.SIGTERM)
        assert handler not in (before, signal.SIG_DFL)
        with pytest.raises(SystemExit) as exit_:
            handler(signal.SIGTERM, None)
        assert exit_.value.code == 128 + signal.SIGTERM
        assert replica_mod.QUICK_STOP is True                  # the app gets a short stop
        assert signal.getsignal(signal.SIGTERM) == signal.SIG_IGN
        assert signal.getsignal(signal.SIGINT) == signal.SIG_IGN  # a 2nd Ctrl-C too
    assert signal.getsignal(signal.SIGTERM) == before            # restored afterwards
    assert replica_mod.QUICK_STOP is False
