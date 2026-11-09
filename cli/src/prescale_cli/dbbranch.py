"""Database copies for replica mode: a throwaway Neon branch for each run.

`--db neon --db-parent staging` makes a copy of the `staging` branch (Neon
branches are copy-on-write, so this takes seconds whatever the size), gives it
its own compute, starts the app with DATABASE_URL pointing at it, and deletes
the copy when the test ends, however it ends. Journeys that write change the
copy, never the database the copy came from, and the load runs on the copy's
own compute, so it never competes with the parent's traffic.

The parent must be named: the project's default branch is often production, so
PreScale never picks it silently. The connection string is a secret: it goes
into the app's environment and nowhere else (not the terminal, the Result, an
upload or a log).
"""

from __future__ import annotations

import os
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

NEON_API = "https://console.neon.tech/api/v2"
READY_TIMEOUT = 120.0
_POLL_S = 1.0
_NAME_PREFIX = "prescale-"


class DBBranchError(Exception):
    """The copy couldn't be made, or a Neon call failed."""


@dataclass
class Branch:
    id: str
    name: str
    parent: str
    database: str
    uri: str = field(repr=False)   # a secret: never printed, saved or uploaded


def neon_settings(env: dict[str, str] | None = None) -> tuple[str, str]:
    """NEON_API_KEY and NEON_PROJECT_ID, or a clear error naming what's missing."""
    env = os.environ if env is None else env
    missing = [n for n in ("NEON_API_KEY", "NEON_PROJECT_ID") if not env.get(n)]
    if missing:
        raise DBBranchError(f"--db neon needs {' and '.join(missing)} in the environment "
                            "(a Neon API key, and the ID of the project to copy from).")
    return env["NEON_API_KEY"], env["NEON_PROJECT_ID"]


def _call(client: httpx.Client, method: str, path: str, **kwargs) -> dict:
    try:
        resp = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise DBBranchError(f"Couldn't reach Neon ({exc.__class__.__name__}).") from exc
    if resp.status_code == 401:
        raise DBBranchError("Neon refused NEON_API_KEY (401). Check the key is current.")
    if resp.status_code == 404:
        raise DBBranchError("Neon has no such project or branch (404). Check NEON_PROJECT_ID.")
    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json().get("message") or "")[:200]
        except ValueError:
            pass
        raise DBBranchError(f"Neon answered {resp.status_code} to {method} {path.split('?')[0]}"
                            + (f": {detail}" if detail else "."))
    return resp.json() if resp.content else {}


def _find_parent(client: httpx.Client, project: str, parent: str) -> dict:
    branches = _call(client, "GET", f"/projects/{project}/branches").get("branches") or []
    match = next((b for b in branches if parent in (b.get("name"), b.get("id"))), None)
    if match is None:
        names = ", ".join(sorted(b.get("name", "?") for b in branches)) or "none"
        raise DBBranchError(f"No branch named {parent!r} in the Neon project. Branches: {names}.")
    return match


def _wait(client: httpx.Client, project: str, operations: list[dict], timeout: float) -> None:
    pending = {op["id"] for op in operations if op.get("status") != "finished"}
    deadline = time.monotonic() + timeout
    while pending:
        if time.monotonic() > deadline:
            raise DBBranchError(f"The Neon branch wasn't ready within {timeout:g}s.")
        for op_id in list(pending):
            op = _call(client, "GET", f"/projects/{project}/operations/{op_id}").get(
                "operation") or {}
            status = op.get("status")
            if status == "finished":
                pending.discard(op_id)
            elif status in ("failed", "error", "cancelled"):
                raise DBBranchError(f"Neon couldn't create the branch (operation {status}).")
        if pending:
            time.sleep(_POLL_S)


def _database(client: httpx.Client, project: str, branch_id: str,
              name: str | None) -> tuple[str, str]:
    dbs = _call(client, "GET", f"/projects/{project}/branches/{branch_id}/databases").get(
        "databases") or []
    if name:
        db = next((d for d in dbs if d.get("name") == name), None)
        if db is None:
            raise DBBranchError(f"The branch has no database named {name!r}. Databases: "
                                f"{', '.join(d.get('name', '?') for d in dbs) or 'none'}.")
    elif len(dbs) == 1:
        db = dbs[0]
    else:
        raise DBBranchError("The branch has several databases "
                            f"({', '.join(d.get('name', '?') for d in dbs)}): "
                            "pick one with --db-name.")
    return db["name"], db["owner_name"]


@contextmanager
def neon_branch(parent: str, *, api_key: str, project: str, database: str | None = None,
                pooled: bool = False, timeout: float = READY_TIMEOUT,
                transport: httpx.BaseTransport | None = None, on_delete_failed=None):
    """Make a throwaway branch of PARENT, yield it, then delete it (also on
    errors and Ctrl-C). ON_DELETE_FAILED(branch, error) is told if Neon won't
    delete it, so the user can remove it by name."""
    client = httpx.Client(base_url=NEON_API, timeout=30.0, transport=transport,
                          headers={"Authorization": f"Bearer {api_key}",
                                   "Accept": "application/json"})
    created = None
    try:
        source = _find_parent(client, project, parent)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        name = f"{_NAME_PREFIX}{stamp}-{secrets.token_hex(3)}"
        made = _call(client, "POST", f"/projects/{project}/branches", json={
            "branch": {"parent_id": source["id"], "name": name},
            "endpoints": [{"type": "read_write"}],
        })
        created = made["branch"]
        _wait(client, project, made.get("operations") or [], timeout)
        db_name, role = _database(client, project, created["id"], database)
        uri = _call(client, "GET", f"/projects/{project}/connection_uri", params={
            "branch_id": created["id"], "database_name": db_name, "role_name": role,
            "pooled": "true" if pooled else "false"})["uri"]
        yield Branch(id=created["id"], name=name, parent=source.get("name") or parent,
                     database=db_name, uri=uri)
    finally:
        if created is not None:
            try:
                _call(client, "DELETE", f"/projects/{project}/branches/{created['id']}")
            except DBBranchError as exc:
                if on_delete_failed:
                    on_delete_failed(created.get("name") or created["id"], exc)
        client.close()
