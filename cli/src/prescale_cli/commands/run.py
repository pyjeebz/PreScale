"""`prescale run` - zero-config launch-readiness load test.

Ramps virtual users across one or more routes and reports, in plain English,
what breaks first and at what traffic level - before you launch.
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
    build_targets,
    default_levels,
    discover_sitemap,
    route_label,
    run_loadtest,
)

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@click.command()
@click.argument("url")
@click.option("--path", "paths", multiple=True,
              help="Extra route to test, relative to URL (repeatable). e.g. --path /api/search")
@click.option("--from-sitemap", "from_sitemap", is_flag=True,
              help="Also pull GET routes from the site's sitemap.xml.")
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
def run(url: str, paths: tuple[str, ...], from_sitemap: bool, max_users: int,
        stage_seconds: float, latency_wall: float, error_threshold: float,
        method: str, timeout: float, yes: bool, as_json: bool) -> None:
    """Load test URL and report what breaks first.

    \b
    Examples:
        prescale run http://localhost:8000
        prescale run https://staging.myapp.com --path /api/search --path /pricing
        prescale run https://staging.myapp.com --from-sitemap -u 500 --i-own-this
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. http://localhost:8000).")
        raise SystemExit(1)

    host = (parsed.hostname or "").lower()
    is_local = host in _LOCAL_HOSTS
    if not is_local and not yes:
        if as_json:
            console.print(f"[red]Error:[/red] refusing to load-test non-local host "
                          f"'{host}' in --json mode without --i-own-this.")
            raise SystemExit(1)
        console.print(Panel(
            f"You're about to send real traffic to [bold]{host}[/bold] "
            f"(up to {max_users} concurrent users).\n"
            "Point this at a staging/preview URL you own — not production.",
            title="⚠️  Heads up", border_style="yellow",
        ))
        if not click.confirm("Proceed?", default=False):
            raise SystemExit(0)

    extra: list[str] = []
    if from_sitemap:
        if not as_json:
            console.print("[dim]Discovering routes from sitemap.xml…[/dim]")
        try:
            extra = asyncio.run(discover_sitemap(url, timeout=timeout))
        except Exception:  # discovery is best-effort; never block the run
            extra = []
        if not as_json:
            found = f"{len(extra)} route(s) found" if extra else "none found"
            console.print(f"  [dim]sitemap: {found}[/dim]")

    targets = build_targets(url, paths=paths, extra=extra)

    if not as_json:
        console.print(f"\n[bold]PreScale[/bold] — load testing [cyan]{url}[/cyan]  "
                      f"({len(targets)} route{'s' if len(targets) != 1 else ''})")
        if len(targets) > 1:
            for target in targets[:12]:
                console.print(f"  [dim]{route_label(target)}[/dim]")
            if len(targets) > 12:
                console.print(f"  [dim]… +{len(targets) - 12} more[/dim]")

    levels = default_levels(max_users)

    def render_progress(status):
        def cb(users: int) -> None:
            status.update(f"[bold blue]Ramping load — {users} virtual users…")
        return cb

    try:
        if as_json:
            stages, warning = asyncio.run(run_loadtest(
                targets, levels=levels, stage_seconds=stage_seconds,
                method=method, timeout=timeout,
            ))
        else:
            with console.status("[bold blue]Warming up…") as status:
                stages, warning = asyncio.run(run_loadtest(
                    targets, levels=levels, stage_seconds=stage_seconds,
                    method=method, timeout=timeout, progress_cb=render_progress(status),
                ))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    report = analyze(stages, latency_wall=latency_wall, error_threshold=error_threshold)

    if as_json:
        console.print(json.dumps(_report_to_dict(report, warning), indent=2))
        return

    _render(report, warning, multi=len(targets) > 1)


def _report_to_dict(report: RunReport, warning: str | None) -> dict:
    return {
        "survives_users": report.survives_users,
        "max_tested": report.max_tested,
        "onset_users": report.onset_users,
        "onset_reason": report.onset_reason,
        "culprit_route": report.culprit_route,
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
                "routes": {
                    label: {
                        "total": r.total,
                        "errors": r.errors,
                        "error_rate": round(r.error_rate, 4),
                        "p95_ms": round(r.pct(0.95) * 1000),
                    }
                    for label, r in s.routes.items()
                },
            }
            for s in report.stages
        ],
    }


def _render(report: RunReport, warning: str | None, multi: bool) -> None:
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
        table.add_row(
            str(stage.users),
            f"{stage.rps:.0f}",
            _ms(stage.pct(0.50)),
            _ms(stage.pct(0.95)),
            _ms(stage.pct(0.99)),
            _err(stage.error_rate),
            style="bold red" if is_onset else None,
        )
    console.print(table)
    console.print()

    if report.onset_users is None:
        emoji, color = "✅", "green"
        headline = (f"Held up through {report.max_tested} concurrent users "
                    "(the most we tested).")
    else:
        emoji, color = "⚠️", "yellow"
        if report.survives_users == 0:
            emoji, color = "🛑", "red"
        headline = f"Survives ~{report.survives_users} concurrent users."

    lines = [f"[bold]Scale readiness:[/bold] {emoji} {headline}"]
    if report.onset_users is not None:
        culprit = f"{report.culprit_route}  " if (multi and report.culprit_route) else ""
        if report.onset_reason == "latency":
            lines.append(f"Latency wall  {culprit}p95 crosses "
                         f"{report.latency_wall:g}s at ~{report.onset_users} users.")
        else:
            lines.append(f"First failure  {culprit}errors climb at "
                         f"~{report.onset_users} users.")
    if report.bottleneck:
        lines.append(f"Likely cause  {report.bottleneck}")

    console.print(Panel("\n".join(lines), title="📈 Readiness report", border_style=color))

    if multi and report.stages:
        _render_routes(report)


def _render_routes(report: RunReport) -> None:
    decisive = next((s for s in report.stages if s.users == report.onset_users),
                    report.stages[-1])
    table = Table(show_header=True, header_style="bold magenta",
                  title=f"Per route @ {decisive.users} users")
    table.add_column("Route")
    table.add_column("Req/s", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("Errors", justify="right")

    ranked = sorted(decisive.routes.items(),
                    key=lambda kv: (kv[1].error_rate, kv[1].pct(0.95)), reverse=True)
    for label, stat in ranked:
        is_culprit = label == report.culprit_route
        shown = f"[bold red]{label}[/bold red]" if is_culprit else label
        table.add_row(
            shown,
            f"{stat.total / decisive.duration:.0f}",
            _ms(stat.pct(0.95)),
            _err(stat.error_rate),
        )
    console.print()
    console.print(table)


def _err(rate: float) -> str:
    color = "red" if rate >= 0.02 else "yellow" if rate > 0 else "green"
    return f"[{color}]{rate:.0%}[/{color}]"


def _ms(seconds: float) -> str:
    if seconds <= 0:
        return "-"
    return f"{seconds * 1000:.0f}ms"
