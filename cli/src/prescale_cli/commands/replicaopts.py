"""`--app` / `--app-timeout` (replica mode) and `--db` (a throwaway database
copy for it) for `run`, `investigate` and `ci`.

The app and its database copy are started through Click's context, so they're
stopped and deleted when the command ends however it ends: a verdict, an error,
or Ctrl-C. The copy is made first and deleted last, after the app has stopped.
"""

from __future__ import annotations

import functools
import os
import re
import signal
import sys
from pathlib import Path
from urllib.parse import urlsplit

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.dbbranch import DBBranchError, neon_branch, neon_settings
from prescale_cli.replica import DEFAULT_TIMEOUT, ReplicaError, replica, require_local

# Where the --db choices and the copy's (non-secret) description live for the command.
DB_META = "prescale.db"

# Database variables apps commonly read (Prisma, Vercel's Neon integration, libpq).
# Any of these that's set is pointed at the copy too, so no part of the app can
# reach the real database by another name.
_DIRECT_URL_VARS = ("DIRECT_URL", "DATABASE_URL_UNPOOLED", "POSTGRES_URL_NON_POOLING")
_URL_VARS = ("DATABASE_URL", "POSTGRES_URL", "POSTGRES_PRISMA_URL") + _DIRECT_URL_VARS
_PG_VARS = ("PGHOST", "PGHOST_UNPOOLED", "PGUSER", "PGPASSWORD", "PGDATABASE", "PGPORT")

app_option = click.option(
    "--app", "app", default=None, metavar="COMMAND",
    help='Start your app with COMMAND (e.g. "npm run build && npm start"), test it on the '
         "local URL, then stop it. Replica mode: no host is involved. The command is never "
         "saved or uploaded.")
app_timeout_option = click.option(
    "--app-timeout", "app_timeout", default=DEFAULT_TIMEOUT, type=float, show_default=True,
    help="Seconds to wait for the app to answer (builds can take minutes).")


def db_options(fn):
    """--db, --db-parent, --db-name, --db-env, --db-pooled. They need --app: only
    an app PreScale starts can be pointed at the copy."""
    @click.option("--db", "db", type=click.Choice(["neon"]), default=None,
                  help="With --app: give the app its own throwaway copy of the database (a "
                       "Neon branch), deleted when the test ends. Needs NEON_API_KEY and "
                       "NEON_PROJECT_ID.")
    @click.option("--db-parent", "db_parent", default=None, metavar="BRANCH",
                  help="The Neon branch to copy, e.g. staging. Required with --db: the "
                       "default branch is often production, so PreScale never picks it.")
    @click.option("--db-name", "db_name", default=None, metavar="NAME",
                  help="The database in the branch, if it has more than one.")
    @click.option("--db-env", "db_env", multiple=True, default=("DATABASE_URL",),
                  show_default=True, metavar="VAR",
                  help="An environment variable the app reads its database URL from "
                       "(repeatable). DIRECT_URL, POSTGRES_URL*, DATABASE_URL_UNPOOLED and "
                       "PG* are pointed at the copy too whenever they're set.")
    @click.option("--db-pooled", "db_pooled", is_flag=True,
                  help="Give the app Neon's pooled connection URL (through its pooler).")
    @functools.wraps(fn)
    def wrapper(*args, db, db_parent, db_name, db_env, db_pooled, **kwargs):
        if db:
            if not kwargs.get("app"):
                raise click.UsageError("--db needs --app: PreScale can only point an app it "
                                       "starts at the database copy.")
            if not db_parent:
                raise click.UsageError("--db neon needs --db-parent BRANCH, the branch to "
                                       "copy (e.g. staging).")
            click.get_current_context().meta[DB_META] = {
                "provider": db, "parent": db_parent, "name": db_name, "env": list(db_env),
                "pooled": db_pooled}
            _guard_signals(click.get_current_context())
        return fn(*args, **kwargs)
    return wrapper


def _guard_signals(ctx: click.Context) -> None:
    """A cancelled CI job sends SIGINT, then SIGTERM seconds later, then kills.
    The first signal ends the run normally (so the app stops and the copy is
    deleted), the app gets a short stop, and later signals are ignored so they
    can't interrupt the delete. The old handlers come back afterwards."""
    from prescale_cli import replica as replica_mod

    def first(signum, _frame):
        ignore_signals()
        replica_mod.QUICK_STOP = True
        Console(stderr=True).print("[dim]Cancelled: stopping the app and deleting the "
                                   "database copy…[/dim]")
        if signum == signal.SIGINT:
            raise KeyboardInterrupt
        sys.exit(128 + signum)

    try:
        previous = {sig: signal.signal(sig, first) for sig in _SIGNALS}
    except (ValueError, OSError):  # not the main thread, or no such signal here
        return

    def restore():
        replica_mod.QUICK_STOP = False
        for sig, handler in previous.items():
            try:
                signal.signal(sig, handler)
            except (ValueError, OSError, TypeError):
                pass
    ctx.call_on_close(restore)


def ignore_signals() -> None:
    """From here on, signals can't interrupt deleting the copy."""
    for sig in _SIGNALS:
        try:
            signal.signal(sig, signal.SIG_IGN)
        except (ValueError, OSError):
            pass


_SIGNALS = tuple(s for s in (getattr(signal, "SIGINT", None), getattr(signal, "SIGTERM", None))
                 if s is not None)


def _start_database(console: Console, quiet: bool) -> dict[str, str]:
    """Make the database copy if --db asked for one; the app's extra environment."""
    ctx = click.get_current_context()
    want = ctx.meta.get(DB_META)
    if not want:
        return {}
    err = Console(stderr=True) if quiet else console  # keep --json stdout clean
    try:
        api_key, project = neon_settings()
    except DBBranchError as exc:
        err.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None

    def left_behind(name, exc):
        Console(stderr=True).print(f"[yellow]⚠ Couldn't delete the Neon branch {name}: {exc} "
                                   "Delete it in the Neon console.[/yellow]")
    copy = neon_branch(want["parent"], api_key=api_key, project=project,
                       database=want["name"], pooled=want["pooled"],
                       on_delete_failed=left_behind)
    try:
        if quiet:
            branch = ctx.with_resource(copy)
        else:
            with console.status(f"Copying the Neon branch {want['parent']}…"):
                branch = ctx.with_resource(copy)
    except DBBranchError as exc:
        err.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    # What the Result may say about it: never the URL.
    want["copy"] = {"provider": "neon", "parent": branch.parent, "database": branch.database}
    want["secrets"] = branch.secrets()
    env = copy_environment(branch, want["env"], os.environ)
    if not quiet:
        console.print(f"[green]✓[/green] a throwaway copy of {branch.parent} is ready "
                      f"([dim]{branch.name}[/dim]); it's deleted when the test ends")
        console.print(f"  [dim]pointed at the copy: {', '.join(sorted(env))}[/dim]")
    others = other_databases(env, os.environ)
    if others:
        Console(stderr=True).print(
            f"[yellow]⚠ {', '.join(others)} also hold a Postgres URL and still point where "
            "they did. If the app reads them, add them with --db-env.[/yellow]")
    return env


def copy_environment(branch, named: list[str], current) -> dict[str, str]:
    """The app's database variables, all pointing at the copy: the ones named
    with --db-env, and every well-known one, set or not. Always set, because
    apps often load these from a .env file, and dotenv never overrides a
    variable that's already set: so the copy wins over the file."""
    env = {name: branch.uri for name in named}
    for name in _URL_VARS:
        env.setdefault(name, branch.direct_uri if name in _DIRECT_URL_VARS else branch.uri)
    parts = urlsplit(branch.direct_uri)
    env.update({"PGHOST": parts.hostname or "", "PGHOST_UNPOOLED": parts.hostname or "",
                "PGUSER": parts.username or "", "PGPASSWORD": parts.password or "",
                "PGDATABASE": parts.path.lstrip("/"), "PGPORT": str(parts.port or 5432),
                "PGSSLMODE": "require"})
    return env


_POSTGRES_URL = re.compile(r"^\s*['\"]?postgres(ql)?(\+[a-z0-9]+)?://", re.IGNORECASE)
_ENV_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")


def other_databases(env: dict[str, str], current, cwd: str = ".") -> list[str]:
    """Names (never values) of variables not pointed at the copy that hold a
    Postgres URL, in this environment or in the app's .env files: the app might
    still reach a real database through them."""
    found = {name for name, value in current.items() if _POSTGRES_URL.match(str(value))}
    for path in sorted(Path(cwd).glob(".env*")):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            m = _ENV_LINE.match(line)
            if m and _POSTGRES_URL.match(m.group(2)):
                found.add(m.group(1))
    return sorted(found - set(env))


def database_info() -> dict | None:
    """The database copy this command's app ran against, for the Result."""
    ctx = click.get_current_context(silent=True)
    want = ctx.meta.get(DB_META) if ctx else None
    return (want or {}).get("copy")


def start_replica(app: str, url: str, *, timeout: float, console: Console, quiet: bool) -> None:
    """Start the app for this command (with its database copy, if --db asked for
    one), or exit with the reason it couldn't start."""
    try:
        require_local(url)
    except ReplicaError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    env = _start_database(console, quiet)
    hidden = (click.get_current_context().meta.get(DB_META) or {}).get("secrets")
    if not quiet:
        console.print(Panel(
            f"Starting your app with [bold]{app}[/bold] and waiting for {url}.\n" +
            ("Its database is the throwaway copy. " if env else
             "It runs with your environment: point DATABASE_URL and API keys at dev or "
             "staging, not production.\n") +
            "PreScale stops it when the test ends. The command is never saved or uploaded.",
            title="Replica mode", border_style="cyan"))
    ctx = click.get_current_context()
    try:
        if quiet:
            ctx.with_resource(replica(app, url, timeout=timeout, env=env, secrets=hidden))
        else:
            with console.status("Building and starting your app…"):
                ctx.with_resource(replica(app, url, timeout=timeout, env=env, secrets=hidden))
    except ReplicaError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    if hidden:
        # Callbacks run last-in-first-out: this one runs as cleanup starts, so a
        # cancel that arrives while the copy is being deleted can't interrupt it.
        ctx.call_on_close(ignore_signals)
    if not quiet:
        console.print(f"[green]✓[/green] your app is up at {url}")
