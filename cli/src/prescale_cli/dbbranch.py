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
import re
import secrets
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx

NEON_API = "https://console.neon.tech/api/v2"
READY_TIMEOUT = 120.0
DELETE_TIMEOUT = 30.0
_POLL_S = 1.0
NAME_PREFIX = "prescale-"
# Exactly the names neon_branch generates, so cleanup never matches a user's
# own branch that happens to start with "prescale-".
OUR_NAME = re.compile(r"^prescale-\d{8}-\d{6}-[0-9a-f]{6}$")
# Neon says 423 (another operation holds the resource) and 503 are safe to retry.
_RETRYABLE = (423, 503)
_RETRY_SCALE = 1.0  # tests set 0 to skip the backoff waits


class DBBranchError(Exception):
    """The copy couldn't be made, or a Neon call failed."""


@dataclass
class Branch:
    id: str
    name: str
    parent: str
    database: str
    # Secrets: never printed, saved or uploaded.
    uri: str = field(repr=False)          # direct, or pooled with --db-pooled
    direct_uri: str = field(repr=False)
    pooled_uri: str = field(repr=False)

    def secrets(self) -> set[str]:
        """Every value that must never be shown: the URLs and the password."""
        values = {self.uri, self.direct_uri, self.pooled_uri}
        values |= {urlsplit(u).password or "" for u in values}
        return {v for v in values if v}


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
        what = ("project (check NEON_PROJECT_ID)" if path.count("/") <= 2
                else f"resource at {path.split('?')[0]}")
        raise DBBranchError(f"Neon has no such {what} (404).")
    if resp.status_code >= 400:
        detail = ""
        try:
            detail = str(resp.json().get("message") or "")[:200]
        except ValueError:
            pass
        raise DBBranchError(f"Neon answered {resp.status_code} to {method} {path.split('?')[0]}"
                            + (f": {detail}" if detail else "."))
    return resp.json() if resp.content else {}


def _branches(client: httpx.Client, project: str, search: str | None = None) -> list[dict]:
    """Every branch (following pagination), optionally narrowed by Neon's search."""
    out, cursor = [], None
    for _ in range(50):  # pages; a guard against a cursor that never ends
        params = {k: v for k, v in {"search": search, "cursor": cursor}.items() if v}
        page = _call(client, "GET", f"/projects/{project}/branches", params=params)
        out += page.get("branches") or []
        cursor = (page.get("pagination") or {}).get("next")
        if not cursor or not page.get("branches"):
            break
    return out


def _find_parent(client: httpx.Client, project: str, parent: str) -> dict:
    # Search narrows by partial name or id; match exactly.
    found = _branches(client, project, search=parent)
    match = next((b for b in found if parent in (b.get("name"), b.get("id"))), None)
    if match is None:
        names = ", ".join(sorted(b.get("name", "?") for b in _branches(client, project)))
        raise DBBranchError(f"No branch named {parent!r} in the Neon project. Branches: "
                            f"{names or 'none'}.")
    return match


def _delete(client: httpx.Client, project: str, branch_id: str,
            timeout: float = DELETE_TIMEOUT) -> None:
    """Delete a branch, retrying while Neon says it's locked or busy."""
    deadline, wait = time.monotonic() + timeout, 1.0
    while True:
        try:
            resp = client.request("DELETE", f"/projects/{project}/branches/{branch_id}")
        except httpx.HTTPError as exc:
            if time.monotonic() >= deadline:
                raise DBBranchError(f"Couldn't reach Neon ({exc.__class__.__name__}).") from exc
        else:
            if resp.status_code in (200, 202, 204, 404):  # 404: already gone
                return
            if resp.status_code not in _RETRYABLE or time.monotonic() >= deadline:
                raise DBBranchError(f"Neon answered {resp.status_code} to the delete.")
        time.sleep(min(wait, max(0.0, deadline - time.monotonic())) * _RETRY_SCALE)
        wait *= 2


def _wait(client: httpx.Client, project: str, operations: list[dict], timeout: float) -> None:
    pending = {op["id"] for op in operations
               if op.get("status") not in ("finished", "skipped")}
    deadline = time.monotonic() + timeout
    while pending:
        if time.monotonic() > deadline:
            raise DBBranchError(f"The Neon branch wasn't ready within {timeout:g}s.")
        for op_id in list(pending):
            op = _call(client, "GET", f"/projects/{project}/operations/{op_id}").get(
                "operation") or {}
            status = op.get("status")
            if status in ("finished", "skipped"):  # both are successful ends
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
    created, name = None, None
    try:
        source = _find_parent(client, project, parent)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        name = f"{NAME_PREFIX}{stamp}-{secrets.token_hex(3)}"
        made = _call(client, "POST", f"/projects/{project}/branches", json={
            "branch": {"parent_id": source["id"], "name": name},
            "endpoints": [{"type": "read_write"}],
        })
        created = made["branch"]
        _wait(client, project, made.get("operations") or [], timeout)
        db_name, role = _database(client, project, created["id"], database)

        def uri_for(pool: bool) -> str:
            return _call(client, "GET", f"/projects/{project}/connection_uri", params={
                "branch_id": created["id"], "database_name": db_name, "role_name": role,
                "pooled": "true" if pool else "false"})["uri"]
        direct, pooled_uri = uri_for(False), uri_for(True)
        yield Branch(id=created["id"], name=name, parent=source.get("name") or parent,
                     database=db_name, uri=pooled_uri if pooled else direct,
                     direct_uri=direct, pooled_uri=pooled_uri)
    finally:
        try:
            if created is None and name is not None:
                # The create call failed, but Neon may have made the branch anyway
                # (a timeout or a 5xx after the fact): find it by its unique name.
                try:
                    created = next((b for b in _branches(client, project, search=name)
                                    if b.get("name") == name), None)
                except DBBranchError as exc:
                    # Can't tell whether it exists: say which branch to check.
                    if on_delete_failed:
                        on_delete_failed(name, exc)
            if created is not None:
                try:
                    _delete(client, project, created["id"])
                except DBBranchError as exc:
                    if on_delete_failed:
                        on_delete_failed(created.get("name") or created["id"], exc)
        finally:
            client.close()


def _ours(branch: dict) -> bool:
    return (bool(OUR_NAME.match(branch.get("name") or "")) and not branch.get("default")
            and not branch.get("protected") and not branch.get("primary"))


def stale_copies(*, api_key: str, project: str, older_than_hours: float,
                 transport: httpx.BaseTransport | None = None,
                 now: datetime | None = None) -> list[dict]:
    """PreScale's own copies (`prescale-...`) created more than OLDER_THAN_HOURS
    ago: what a run that couldn't clean up left behind."""
    now = now or datetime.now(timezone.utc)
    with httpx.Client(base_url=NEON_API, timeout=30.0, transport=transport,
                      headers={"Authorization": f"Bearer {api_key}"}) as client:
        found = _branches(client, project, search=NAME_PREFIX)
    stale = []
    for b in found:
        if not _ours(b):
            continue
        try:
            created = datetime.fromisoformat(str(b.get("created_at")).replace("Z", "+00:00"))
        except ValueError:
            continue
        if (now - created).total_seconds() >= older_than_hours * 3600:
            stale.append(b)
    return stale


def delete_copies(branches: list[dict], *, api_key: str, project: str,
                  transport: httpx.BaseTransport | None = None) -> list[tuple[str, str]]:
    """Delete BRANCHES; the (name, reason) of each that couldn't be deleted."""
    failed = []
    with httpx.Client(base_url=NEON_API, timeout=30.0, transport=transport,
                      headers={"Authorization": f"Bearer {api_key}"}) as client:
        for b in branches:
            if not _ours(b):
                continue  # never anything PreScale didn't make
            try:
                _delete(client, project, b["id"])
            except DBBranchError as exc:
                failed.append((b.get("name") or b["id"], str(exc)))
    return failed
