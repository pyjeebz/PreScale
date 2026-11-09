"""`--app` / `--app-timeout` (replica mode) and `--db` (a throwaway database
copy for it) for `run`, `investigate` and `ci`.

The app and its database copy are started through Click's context, so they're
stopped and deleted when the command ends however it ends: a verdict, an error,
or Ctrl-C. The copy is made first and deleted last, after the app has stopped.
"""

from __future__ import annotations

import functools

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.dbbranch import DBBranchError, neon_branch, neon_settings
from prescale_cli.replica import DEFAULT_TIMEOUT, ReplicaError, replica, require_local

# Where the --db choices and the copy's (non-secret) description live for the command.
DB_META = "prescale.db"

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
    @click.option("--db-env", "db_env", default="DATABASE_URL", show_default=True,
                  metavar="VAR", help="The environment variable the app reads its database "
                                      "URL from.")
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
                "provider": db, "parent": db_parent, "name": db_name, "env": db_env,
                "pooled": db_pooled}
        return fn(*args, **kwargs)
    return wrapper


def _start_database(console: Console, quiet: bool) -> dict[str, str]:
    """Make the database copy if --db asked for one; the app's extra environment."""
    ctx = click.get_current_context()
    want = ctx.meta.get(DB_META)
    if not want:
        return {}
    try:
        api_key, project = neon_settings()
    except DBBranchError as exc:
        console.print(f"[red]Error:[/red] {exc}")
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
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    # What the Result may say about it: never the URL.
    want["copy"] = {"provider": "neon", "parent": branch.parent, "database": branch.database}
    if not quiet:
        console.print(f"[green]✓[/green] a throwaway copy of {branch.parent} is ready "
                      f"([dim]{branch.name}[/dim]); it's deleted when the test ends")
    return {want["env"]: branch.uri}


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
            ctx.with_resource(replica(app, url, timeout=timeout, env=env))
        else:
            with console.status("Building and starting your app…"):
                ctx.with_resource(replica(app, url, timeout=timeout, env=env))
    except ReplicaError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    if not quiet:
        console.print(f"[green]✓[/green] your app is up at {url}")
