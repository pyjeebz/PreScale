"""`prescale investigate` - find what breaks first, then probe it to explain why."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.investigate import investigate as run_investigate
from prescale_cli.loadtest import LoadError
from prescale_cli.render import render_investigation, render_terminal
from prescale_cli.result import latest_id, load_result

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@click.command()
@click.argument("url", required=False)
@click.option("--path", "paths", multiple=True,
              help="Extra route to test, relative to URL (repeatable).")
@click.option("--max-users", "-u", default=200, type=int, help="Peak virtual users.")
@click.option("--stage-seconds", "-s", default=5.0, type=float,
              help="Seconds to hold each load level.")
@click.option("--max-rps", default=None, type=float, help="Cap aggregate requests/sec.")
@click.option("--i-own-this", "yes", is_flag=True,
              help="Skip the confirmation prompt for non-local targets.")
@click.option("--json", "as_json", is_flag=True, help="Emit the full Result as JSON.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
@click.option("--fail-under", "fail_under", default=None, type=int,
              help="Exit non-zero if it survives fewer than N users (a CI gate).")
def investigate(url: str | None, paths: tuple[str, ...], max_users: int,
                stage_seconds: float, max_rps: float | None, yes: bool,
                as_json: bool, store: str | None, fail_under: int | None) -> None:
    """Find what breaks first, then probe it to explain WHY - and how to fix it.

    With no URL, re-investigates the latest saved run's target.

    \b
    Examples:
        prescale investigate http://localhost:8000
        prescale investigate https://staging.myapp.com --i-own-this
        prescale investigate            # re-investigate the latest saved run
    """
    if url is None:
        last = latest_id(store=store)
        if last is None:
            console.print("[dim]No saved runs yet — try "
                          "[bold]prescale investigate <url>[/bold].[/dim]")
            raise SystemExit(0)
        url = load_result(last, store=store)["target"]["url"]
        console.print(f"[dim]Re-investigating latest run: {url}[/dim]")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. http://localhost:8000).")
        raise SystemExit(1)

    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_HOSTS and not yes:
        if as_json:
            console.print(f"[red]Error:[/red] refusing non-local host '{host}' in "
                          "--json mode without --i-own-this.")
            raise SystemExit(1)
        console.print(Panel(
            f"investigate sends real traffic to [bold]{host}[/bold] (a ramp plus a few "
            "probes).\nPoint it at a staging/preview URL you own — not production.",
            title="⚠️  Heads up", border_style="yellow"))
        if not click.confirm("Proceed?", default=False):
            raise SystemExit(0)

    def render_progress(status):
        def cb(u: int) -> None:
            status.update(f"[bold blue]Ramping load — {u} virtual users…")
        return cb

    try:
        if as_json:
            result = asyncio.run(run_investigate(
                url, max_users=max_users, paths=paths, stage_seconds=stage_seconds,
                max_rps=max_rps, store=store))
        else:
            with console.status("[bold blue]Warming up…") as status:
                result = asyncio.run(run_investigate(
                    url, max_users=max_users, paths=paths, stage_seconds=stage_seconds,
                    max_rps=max_rps, store=store, progress_cb=render_progress(status)))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        render_terminal(result)
        render_investigation(result)
        if result.get("investigation") is None:
            console.print("\n[green]✓[/green] Held up — nothing to diagnose.")
        console.print(f"[dim]saved as {result['id']}[/dim]")

    survives = result["verdict"]["survives_users"]
    if fail_under is not None and survives < fail_under:
        Console(stderr=True).print(
            f"[red]✗ fail-under:[/red] survives ~{survives} < {fail_under}")
        raise SystemExit(1)
