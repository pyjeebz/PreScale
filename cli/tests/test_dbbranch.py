"""`--db neon`: a throwaway Neon branch for the replica, made and deleted around the run."""

import functools
import json
import sys

import httpx
import pytest
from click.testing import CliRunner

from prescale_cli import dbbranch
from prescale_cli.dbbranch import DBBranchError, neon_branch, neon_settings
from prescale_cli.main import cli

URI = "postgresql://owner:s3cr3t-pw@ep-copy-123.us-east-2.aws.neon.tech/shop?sslmode=require"


class FakeNeon:
    """Enough of Neon's API: branches, operations, databases, connection URI."""

    def __init__(self, *, databases=("shop",), op_status=("running", "finished"),
                 branches=("main", "staging")):
        self.calls: list[tuple[str, str]] = []
        self.created: dict | None = None
        self.deleted: list[str] = []
        self.databases = databases
        self.op_status = list(op_status)
        self.branches = [{"id": f"br-{n}", "name": n} for n in branches]

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path.removeprefix("/api/v2"), request.method
        self.calls.append((method, path))
        assert request.headers["authorization"] == "Bearer key-123"
        if method == "GET" and path == "/projects/p1/branches":
            return httpx.Response(200, json={"branches": self.branches})
        if method == "POST" and path == "/projects/p1/branches":
            body = json.loads(request.content)
            self.created = body
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
            self.uri_params = dict(request.url.params)
            return httpx.Response(200, json={"uri": URI})
        if method == "DELETE" and path == "/projects/p1/branches/br-copy":
            self.deleted.append("br-copy")
            return httpx.Response(200, json={})
        return httpx.Response(404, json={"message": "nope"})

    def transport(self):
        return httpx.MockTransport(self.handler)


@pytest.fixture(autouse=True)
def fast(monkeypatch):
    monkeypatch.setattr(dbbranch, "_POLL_S", 0)


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
    assert fake.uri_params["pooled"] == "false"
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
        assert branch.database == "analytics"
    assert fake.uri_params["pooled"] == "true"


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
