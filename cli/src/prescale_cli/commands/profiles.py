"""`prescale profiles` - list the launch profiles for `run --profile`."""

from __future__ import annotations

import click
from rich.console import Console

from prescale_cli.profiles import PROFILES

console = Console()


@click.command()
def profiles() -> None:
    """List the launch profiles you can pass to `prescale run --profile <name>`."""
    console.print("[bold]Launch profiles[/bold] — "
                  "use with [cyan]prescale run --profile <name>[/cyan]\n")
    for p in PROFILES.values():
        console.print(f"  [bold]{p.name}[/bold]")
        console.print(f"    {p.label} — peaks ~{p.peak_users} users, "
                      f"{p.think_time_s:g}s think-time")
