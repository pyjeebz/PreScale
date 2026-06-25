"""`prescale run` - zero-config launch-readiness load test for one URL.

Ramps virtual users against a URL and reports, in plain English, what breaks
first and at what traffic level - before you launch.
"""

from __future__ import annotations

import asyncio
import json
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from prescale_cli.loadtest import (
    LoadError,
    RunReport,
    analyze,
    default_levels,
    run_loadtest,
)

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@click.command()
@click.argument("url")
@click.option("--max-users", "-u", default=200, type=int,
              help="Peak virtual users to ramp to.")
@click.option("--stage-seconds", "-s", default=5.0, type=float,
              help="Seconds to hold each load level.")
@click.option("--latency-wall", default=2.0, type=float,
              help="p95 latency (seconds) treated as the failure threshold.")
@click.option("--error-threshold", default=0.02, type=float,
              help="Error rate (0-1) treated as the failure threshold.")
@click.option("--method", "-m", default="GET",
              help="HTTP method to fire.")
@click.option("--timeout", default=10.0, type=float,
              help="Per-request timeout in seconds.")
@click.option("--i-own-this", "yes", is_flag=True,
              help="Skip the confirmation prompt for non-local targets.")
@click.option("--json", "as_json", is_flag=True,
              help="Emit the raw report as JSON.")
def run(url: str, max_users: int, stage_seconds: float, latency_wall: float,
        error_threshold: float, method: str, timeout: float, yes: bool,
        as_json: bool) -> None:
    """Load test URL and report what breaks first.

    \b
    Examples:
        prescale run http://localhost:8000
        prescale run https://staging.myapp.com -u 500
        prescale run https://staging.myapp.com --i-own-this --json
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. http://localhost:8000).")
        raise SystemExit(1)

    host = (parsed.hostname or "").lower()
    is_local = host in _LOCAL_HOSTS
    if not is_local and not yes and not as_json:
        console.print(Panel(
            f"You're about to send real traffic to [bold]{host}[/bold] "
            f"(up to {max_users} concurrent users).\n"
            "Point this at a staging/preview URL you own — not production.",
            title="⚠️  Heads up", border_style="yellow",
        ))
        if not click.confirm("Proceed?", default=False):
            raise SystemExit(0)

    levels = default_levels(max_users)

    if not as_json:
        console.print(f"\n[bold]PreScale[/bold] — load testing [cyan]{url}[/cyan]")

    def render_progress(status):
        def cb(users: int) -> None:
            status.update(f"[bold blue]Ramping load — {users} virtual users…")
        return cb

    try:
        if as_json:
            stages, warning = asyncio.run(run_loadtest(
                url, levels=levels, stage_seconds=stage_seconds,
                method=method, timeout=timeout,
            ))
        else:
            with console.status("[bold blue]Warming up…") as status:
                stages, warning = asyncio.run(run_loadtest(
                    url, levels=levels, stage_seconds=stage_seconds,
                    method=method, timeout=timeout, progress_cb=render_progress(status),
                ))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    report = analyze(stages, latency_wall=latency_wall, error_threshold=error_threshold)

    if as_json:
        console.print(json.dumps(_report_to_dict(report, warning), indent=2))
        return

    _render(report, warning)


def _report_to_dict(report: RunReport, warning: str | None) -> dict:
    return {
        "survives_users": report.survives_users,
        "max_tested": report.max_tested,
        "onset_users": report.onset_users,
        "onset_reason": report.onset_reason,
        "bottleneck": report.bottleneck,
        "latency_wall": report.latency_wall,
        "warning": warning,
        "stages": [
            {
                "users": s.users,
                "rps": round(s.rps, 1),
                "p50_ms": round(s.pct(0.50) * 1000),
                "p95_ms": round(s.pct(0.95) * 1000),
                "p99_ms": round(s.pct(0.99) * 1000),
                "error_rate": round(s.error_rate, 4),
                "errors": s.errors,
                "total": s.total,
            }
            for s in report.stages
        ],
    }


def _render(report: RunReport, warning: str | None) -> None:
    console.print()
    if warning:
        console.print(f"[yellow]⚠ {warning}[/yellow]\n")

    table = Table(show_header=True, header_style="bold magenta", title="Load ramp")
    table.add_column("Users", justify="right")
    table.add_column("Req/s", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("p99", justify="right")
    table.add_column("Errors", justify="right")

    for stage in report.stages:
        is_onset = stage.users == report.onset_users
        err = stage.error_rate
        err_color = "red" if err >= 0.02 else "yellow" if err > 0 else "green"
        row_style = "bold red" if is_onset else None
        table.add_row(
            str(stage.users),
            f"{stage.rps:.0f}",
            _ms(stage.pct(0.50)),
            _ms(stage.pct(0.95)),
            _ms(stage.pct(0.99)),
            f"[{err_color}]{err:.0%}[/{err_color}]",
            style=row_style,
        )
    console.print(table)
    console.print()

    if report.onset_users is None:
        emoji, color = "✅", "green"
        headline = (f"Held up through {report.max_tested} concurrent users "
                    "(the most we tested).")
    else:
        emoji = "🟢" if report.survives_users >= report.max_tested else "⚠️"
        color = "yellow"
        if report.survives_users == 0:
            emoji, color = "🛑", "red"
        headline = f"Survives ~{report.survives_users} concurrent users."

    lines = [f"[bold]Scale readiness:[/bold] {emoji} {headline}"]
    if report.onset_users is not None:
        if report.onset_reason == "latency":
            lines.append(f"Latency wall  p95 crosses {report.latency_wall:g}s "
                         f"at ~{report.onset_users} users.")
        else:
            lines.append(f"First failure  errors climb at ~{report.onset_users} users.")
    if report.bottleneck:
        lines.append(f"Likely cause  {report.bottleneck}")

    console.print(Panel("\n".join(lines), title="📈 Readiness report",
                        border_style=color))


def _ms(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    return f"{seconds * 1000:.0f}ms"
