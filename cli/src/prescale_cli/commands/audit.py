"""`prescale audit` - fast static scaling-hygiene check for a URL (no load)."""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

import click
from rich.console import Console

from prescale_cli.audit import AuditError, Finding, run_audit

console = Console()

_ICONS = {
    "pass": "[green]✓[/green]",
    "warn": "[yellow]⚠[/yellow]",
    "fail": "[red]✗[/red]",
    "info": "[dim]•[/dim]",
}


@click.command()
@click.argument("url")
@click.option("--timeout", default=10.0, type=float, help="Per-request timeout in seconds.")
@click.option("--json", "as_json", is_flag=True, help="Emit findings as JSON.")
def audit(url: str, timeout: float, as_json: bool) -> None:
    """Static scaling-hygiene check for URL (no load).

    \b
    Examples:
        prescale audit https://myapp.com
        prescale audit https://myapp.com --json
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. https://myapp.com).")
        raise SystemExit(1)

    try:
        if as_json:
            findings = asyncio.run(run_audit(url, timeout=timeout))
        else:
            with console.status("[bold blue]Auditing…"):
                findings = asyncio.run(run_audit(url, timeout=timeout))
    except AuditError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    if as_json:
        click.echo(json.dumps(
            [{"name": f.name, "status": f.status, "detail": f.detail, "fix": f.fix}
             for f in findings],
            indent=2,
        ))
        return

    _render(url, findings)


def _render(url: str, findings: list[Finding]) -> None:
    console.print(f"\n[bold]PreScale audit[/bold] — [cyan]{url}[/cyan]\n")
    for f in findings:
        console.print(f"{_ICONS.get(f.status, '•')} [bold]{f.name}[/bold]  {f.detail}")
        if f.fix:
            console.print(f"    [dim]{f.fix}[/dim]")

    counts = {s: sum(1 for f in findings if f.status == s) for s in ("pass", "warn", "fail")}
    console.print(
        f"\n[green]{counts['pass']} passed[/green] · "
        f"[yellow]{counts['warn']} warnings[/yellow] · "
        f"[red]{counts['fail']} failed[/red]"
    )
