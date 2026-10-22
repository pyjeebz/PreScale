"""`--app` / `--app-timeout`: replica mode for `run`, `investigate` and `ci`.

The app is started through Click's context, so it's stopped when the command
ends however it ends: a verdict, an error, or Ctrl-C.
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.replica import DEFAULT_TIMEOUT, ReplicaError, replica, require_local

app_option = click.option(
    "--app", "app", default=None, metavar="COMMAND",
    help='Start your app with COMMAND (e.g. "npm run build && npm start"), test it on the '
         "local URL, then stop it. Replica mode: no host is involved. The command is never "
         "saved or uploaded.")
app_timeout_option = click.option(
    "--app-timeout", "app_timeout", default=DEFAULT_TIMEOUT, type=float, show_default=True,
    help="Seconds to wait for the app to answer (builds can take minutes).")


def start_replica(app: str, url: str, *, timeout: float, console: Console, quiet: bool) -> None:
    """Start the app for this command, or exit with the reason it couldn't start."""
    try:
        require_local(url)
    except ReplicaError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    if not quiet:
        console.print(Panel(
            f"Starting your app with [bold]{app}[/bold] and waiting for {url}.\n"
            "It runs with your environment: point DATABASE_URL and API keys at dev or "
            "staging, not production.\n"
            "PreScale stops it when the test ends. The command is never saved or uploaded.",
            title="Replica mode", border_style="cyan"))
    ctx = click.get_current_context()
    try:
        if quiet:
            ctx.with_resource(replica(app, url, timeout=timeout))
        else:
            with console.status("Building and starting your app…"):
                ctx.with_resource(replica(app, url, timeout=timeout))
    except ReplicaError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    if not quiet:
        console.print(f"[green]✓[/green] your app is up at {url}")
