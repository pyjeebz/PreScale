"""`prescale compare` - diff two saved runs by capacity (and gate regressions)."""

from __future__ import annotations

import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prescale_cli.compare import compare_results, resolve, to_markdown
from prescale_cli.result import AmbiguousResultError, ResultNotFoundError

console = Console()
err = Console(stderr=True)


@click.command()
@click.argument("new", required=False)
@click.argument("old", required=False)
@click.option("--baseline", default=None,
              help="Result id or .json path to compare against (used as OLD).")
@click.option("--regression-threshold", default=0.2, type=float,
              help="Fractional drop in survives_users that counts as a regression.")
@click.option("--fail-on-regression", "fail_on_regression", is_flag=True,
              help="Exit non-zero if capacity regressed.")
@click.option("--json", "as_json", is_flag=True, help="Emit the comparison as JSON.")
@click.option("--markdown", "as_md", is_flag=True,
              help="Emit a PR-comment-ready markdown block.")
@click.option("--store", default=None, type=click.Path(file_okay=False),
              help="Directory holding saved runs (default: ./.prescale).")
def compare(new: str | None, old: str | None, baseline: str | None,
            regression_threshold: float, fail_on_regression: bool,
            as_json: bool, as_md: bool, store: str | None) -> None:
    """Compare two saved runs by capacity. Defaults to the latest two.

    \b
    Examples:
        prescale compare
        prescale compare <new-id> <old-id>
        prescale compare --baseline prescale-baseline.json --fail-on-regression
    """
    try:
        new_r = resolve(new, store=store)
        if new_r is None:
            err.print("[red]Error:[/red] no saved runs to compare.")
            raise SystemExit(1)
        old_r = resolve(baseline or old, store=store, exclude=new_r["id"])
    except (ResultNotFoundError, AmbiguousResultError) as exc:
        err.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)
    if old_r is None:
        err.print("[red]Error:[/red] need a second run (or --baseline) to compare against.")
        raise SystemExit(1)

    cmp = compare_results(old_r, new_r, threshold=regression_threshold)

    if as_json:
        click.echo(json.dumps(cmp, indent=2))
    elif as_md:
        click.echo(to_markdown(cmp))
    else:
        _render(cmp)

    if fail_on_regression and cmp["regressed"]:
        err.print(f"[red]✗ regression:[/red] {cmp['summary']}")
        raise SystemExit(1)


def _render(cmp: dict) -> None:
    o, n = cmp["old"], cmp["new"]
    if cmp["regressed"]:
        color = "red" if cmp["confident"] else "yellow"
    elif cmp["improved"]:
        color = "green"
    else:
        color = "blue"
    table = Table(show_header=True, header_style="bold magenta", title="Capacity compare")
    table.add_column("")
    table.add_column("Survives", justify="right")
    table.add_column("Peak req/s", justify="right")
    table.add_column("Commit")
    table.add_column("When")
    for label, f in (("old", o), ("new", n)):
        table.add_row(label, str(f["survives_users"]), f"{f['peak_rps']:.0f}",
                      f["commit"] or "-", f["created_at"] or "-")
    console.print(table)
    note = "" if (cmp["confident"] or not cmp["regressed"]) else \
        "  (confidence bands overlap — could be noise)"
    console.print(Panel(cmp["summary"] + note, border_style=color))
