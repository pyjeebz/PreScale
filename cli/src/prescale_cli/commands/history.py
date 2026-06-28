"""`prescale history` - list saved runs from .prescale/runs/, newest first."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import click
from rich.console import Console
from rich.table import Table

from prescale_cli.result import list_results

console = Console()


@click.command()
@click.option("-n", "limit", default=20, type=int, help="Max runs to show (0 = all).")
@click.option("--json", "as_json", is_flag=True, help="Emit the run list as JSON.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory holding saved runs (default: ./.prescale).")
def history(limit: int, as_json: bool, store: str | None) -> None:
    """List saved runs, newest first.

    \b
    Examples:
        prescale history
        prescale history -n 5 --json
    """
    runs = list_results(store=store)
    shown = runs[:limit] if limit and limit > 0 else runs

    if as_json:
        click.echo(json.dumps(shown, indent=2))
        return

    if not runs:
        console.print("[dim]No saved runs yet — run [bold]prescale run <url>[/bold] "
                      "to create one.[/dim]")
        return

    table = Table(show_header=True, header_style="bold magenta",
                  title=f"Saved runs (showing {len(shown)} of {len(runs)})")
    table.add_column("ID", no_wrap=True)
    table.add_column("When", justify="right")
    table.add_column("Target")
    table.add_column("Verdict")
    for r in shown:
        table.add_row(r["id"], _when(r.get("created_at")),
                      r.get("host") or "-", _verdict(r))
    console.print(table)
    console.print("\n[dim]prescale show <id>  ·  no id = latest[/dim]")


def _verdict(r: dict) -> str:
    onset = r.get("onset_users")
    survives = r.get("survives_users")
    if onset is None:
        return (f"[green]held up[/green] (≥{survives})" if survives is not None
                else "[green]held up[/green]")
    reason = "latency" if r.get("onset_reason") == "latency" else "errors"
    color = "red" if survives == 0 else "yellow"
    return f"[{color}]survives ~{survives}[/{color}] · breaks {onset} ({reason})"


def _when(created_at: str | None) -> str:
    if not created_at:
        return "-"
    try:
        ts = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError:
        return created_at
    secs = int((datetime.now(timezone.utc) - ts).total_seconds())
    if secs < 60:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    return f"{secs // 86400}d ago"
