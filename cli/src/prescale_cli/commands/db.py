"""`prescale db cleanup` - delete database copies a run couldn't clean up.

Every `--db neon` run deletes its copy when it ends. A run that's killed outright
(a machine that dies, `kill -9`) can't, and Neon plans limit how many branches a
project has. This finds PreScale's own copies (`prescale-...`) older than a few
hours and deletes them. It never touches a branch PreScale didn't make.
"""

from __future__ import annotations

import click
from rich.console import Console

from prescale_cli.dbbranch import DBBranchError, delete_copies, neon_settings, stale_copies

console = Console()


@click.group()
def db() -> None:
    """Database copies made by --db."""


@db.command()
@click.option("--older-than", "older_than", default=6.0, type=float, show_default=True,
              metavar="HOURS", help="Only copies created at least this many hours ago.")
@click.option("--yes", "yes", is_flag=True, help="Delete without asking.")
def cleanup(older_than: float, yes: bool) -> None:
    """Delete leftover Neon copies (prescale-...) from runs that couldn't clean up.

    Needs NEON_API_KEY and NEON_PROJECT_ID, like --db neon.
    """
    try:
        api_key, project = neon_settings()
        stale = stale_copies(api_key=api_key, project=project, older_than_hours=older_than)
    except DBBranchError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None
    if not stale:
        console.print(f"[green]✓[/green] No PreScale copies older than {older_than:g}h.")
        return
    console.print(f"{len(stale)} PreScale cop{'y' if len(stale) == 1 else 'ies'} older than "
                  f"{older_than:g}h:")
    for b in stale:
        console.print(f"  {b['name']}  [dim](created {b.get('created_at')})[/dim]")
    if not yes and not click.confirm("Delete them?", default=False):
        raise SystemExit(0)
    failed = delete_copies(stale, api_key=api_key, project=project)
    for name, reason in failed:
        console.print(f"[red]✗[/red] {name}: {reason}")
    console.print(f"[green]✓[/green] Deleted {len(stale) - len(failed)}.")
    if failed:
        raise SystemExit(1)
