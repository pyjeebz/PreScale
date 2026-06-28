"""`prescale show` - re-render a saved run from .prescale/runs/.

`show` reads a stored Result back through the same `render_terminal` /
`render_html` as `run`, so a re-rendered run is identical to the live one.
"""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console

from prescale_cli.render import render_terminal
from prescale_cli.report import render_html
from prescale_cli.result import (
    AmbiguousResultError,
    ResultNotFoundError,
    latest_id,
    load_result,
)

console = Console()


@click.command()
@click.argument("run_id", required=False)
@click.option("--json", "as_json", is_flag=True, help="Emit the saved Result as JSON.")
@click.option("--html", "html_path", type=click.Path(dir_okay=False), default=None,
              help="Re-render the saved run to an HTML report at PATH.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory holding saved runs (default: ./.prescale).")
def show(run_id: str | None, as_json: bool, html_path: str | None,
         store: str | None) -> None:
    """Re-render a saved run (defaults to the latest).

    \b
    Examples:
        prescale show
        prescale show 20260628T173648Z-3b836f
        prescale show --html report.html
    """
    if run_id is None:
        run_id = latest_id(store=store)
        if run_id is None:
            console.print("[dim]No saved runs yet — run [bold]prescale run <url>[/bold] "
                          "first.[/dim]")
            return

    try:
        result = load_result(run_id, store=store)
    except (ResultNotFoundError, AmbiguousResultError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    if html_path:
        Path(html_path).write_text(render_html(result), encoding="utf-8")

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    console.print(f"[dim]{result['id']}  ·  {result['target']['url']}  ·  "
                  f"{result['created_at']}[/dim]")
    render_terminal(result)
    if html_path:
        console.print(f"\n[green]✓[/green] HTML report written to [cyan]{html_path}[/cyan]")
