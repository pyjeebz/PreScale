"""`prescale journeys` - list the app's journeys, and check they still replay.

Journeys live in the app's repo as `prescale/journeys/*.yaml`. `verify` replays
each one once, as a single user: a step that fails there means the journey is
stale (the app changed) or the app is broken, never that it broke under load.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from prescale_cli.commands.upload import header_option
from prescale_cli.journeys.model import DEFAULT_DIR, Journey, load_dir
from prescale_cli.journeys.replay import JourneyCheck, check

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

dir_option = click.option(
    "--dir", "directory", type=click.Path(file_okay=False, path_type=Path),
    default=DEFAULT_DIR, show_default=True, help="Where the journey files are.")


@click.group(invoke_without_command=True)
@dir_option
@click.pass_context
def journeys(ctx: click.Context, directory: Path) -> None:
    """List the app's journeys (prescale/journeys/*.yaml).

    \b
    Check they still replay against your app:
        prescale journeys verify http://localhost:3000
    """
    if ctx.invoked_subcommand is not None:
        return
    found = _load_or_exit(directory)
    table = Table(title=f"Journeys in {directory}")
    for col in ("Name", "Type", "Weight", "Steps", "Changes data", "File"):
        table.add_column(col)
    for j in found:
        table.add_row(j.name, j.type, f"{j.weight:g}", str(len(j.steps)),
                      "yes" if j.writes else "no", str(j.source))
    console.print(table)


@journeys.command()
@click.argument("url")
@dir_option
@click.option("--journey", "only", multiple=True,
              help="Check only this journey (repeatable).")
@click.option("--allow-writes", "allow_writes", multiple=True, metavar="HOST",
              help="Let journeys that change data (POST, PUT, PATCH, DELETE) run against "
                   "this non-local host, e.g. staging.myapp.com (repeatable).")
@click.option("--timeout", default=10.0, type=float, help="Per-request timeout in seconds.")
@header_option
def verify(url: str, directory: Path, only: tuple[str, ...], allow_writes: tuple[str, ...],
           timeout: float, headers: dict[str, str]) -> None:
    """Replay each journey once, as one user, and report any step that fails.

    Exits non-zero if a journey is stale or the app couldn't be reached.

    \b
        prescale journeys verify http://localhost:3000
        prescale journeys verify https://staging.myapp.com --allow-writes staging.myapp.com
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' is not a URL "
                      "(expected e.g. http://localhost:3000).")
        raise SystemExit(2)
    found = _load_or_exit(directory)
    if only:
        missing = sorted(set(only) - {j.name for j in found})
        if missing:
            console.print(f"[red]Error:[/red] no journey named {', '.join(missing)} "
                          f"in {directory}.")
            raise SystemExit(2)
        found = [j for j in found if j.name in only]

    host = (parsed.hostname or "").lower()
    _refuse_unallowed_writes(found, host, {h.lower() for h in allow_writes})
    unset = sorted({name for j in found for name in j.env_names()} - set(os.environ))
    if unset:
        console.print(f"[red]Error:[/red] the journeys read environment variable(s) that "
                      f"aren't set: {', '.join(unset)}.")
        raise SystemExit(2)

    base = url if url.endswith("/") else url + "/"
    results = asyncio.run(_check_all(found, base, timeout=timeout, headers=headers))
    for result in results:
        _print_check(result)

    broken = [r for r in results if not r.ok]
    if broken:
        stale = [r.journey.name for r in broken if r.stale]
        if stale:
            console.print(f"\n[yellow]{len(stale)} stale:[/yellow] {', '.join(stale)}. The app "
                          "no longer answers the way these journeys expect. If the change was "
                          "on purpose, update the journey files; if not, it's a bug.")
        unreached = [r.journey.name for r in broken if not r.stale]
        if unreached:
            console.print(f"\n[red]{len(unreached)} couldn't run:[/red] {', '.join(unreached)}.")
        raise SystemExit(1)
    console.print(f"\n[green]✓ All {len(results)} journeys replay.[/green]")


def _load_or_exit(directory: Path) -> list[Journey]:
    found, errors = load_dir(directory)
    for error in errors:
        console.print(f"[red]Error:[/red] {escape(error)}", highlight=False)
    if errors:
        raise SystemExit(2)
    if not found:
        console.print(f"No journeys in {directory}. Add one as {directory}/<name>.yaml.")
        raise SystemExit(1)
    return found


def _refuse_unallowed_writes(found: list[Journey], host: str, allowed: set[str]) -> None:
    """Journeys that change data run on local hosts, or on hosts named with
    --allow-writes. Anywhere else they could change real data."""
    if host in _LOCAL_HOSTS or host in allowed:
        return
    writers = [j.name for j in found if j.writes]
    if writers:
        console.print(f"[red]Error:[/red] {', '.join(writers)} change data (POST, PUT, PATCH "
                      f"or DELETE). Run them against {host} only if it's a staging or test "
                      f"environment, with --allow-writes {host}.")
        raise SystemExit(2)


async def _check_all(found: list[Journey], base: str, *, timeout: float,
                     headers: dict[str, str]) -> list[JourneyCheck]:
    return [await check(j, base, timeout=timeout, headers=headers) for j in found]


def _print_check(result: JourneyCheck) -> None:
    journey = result.journey
    mark = "[green]✓[/green]" if result.ok else ("[yellow]stale[/yellow]" if result.stale
                                                 else "[red]✗[/red]")
    console.print(f"\n{mark} [bold]{journey.name}[/bold] [dim]({journey.type}, "
                  f"{len(journey.steps)} steps)[/dim]")
    for i, step in enumerate(journey.steps, 1):
        done = result.steps[i - 1] if i <= len(result.steps) else None
        if done is None:
            console.print(f"   [dim]{i}. {step.name}  {step.label}  (not run)[/dim]")
        elif done.ok:
            console.print(f"   {i}. {step.name}  [dim]{step.label}[/dim]  "
                          f"{done.status}  {done.latency * 1000:.0f}ms")
        else:
            console.print(f"   {i}. {step.name}  [dim]{step.label}[/dim]  "
                          f"[red]{escape(done.problem or '')}[/red]", highlight=False)
            if done.status is not None and done.status >= 500:
                console.print("      [dim]A 5xx with no load is usually a bug in the app, "
                              "not a stale journey.[/dim]")
