"""`prescale run` - zero-config launch-readiness load test.

Ramps virtual users across one or more routes and reports, in plain English,
what breaks first and at what traffic level - before you launch.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.loadtest import (
    LoadError,
    analyze,
    build_targets,
    check_robots,
    default_levels,
    discover_sitemap,
    route_label,
    run_loadtest,
)
from prescale_cli.render import render_terminal
from prescale_cli.report import render_html
from prescale_cli.result import build_result, write_result

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
@click.option("--max-rps", default=None, type=float,
              help="Cap aggregate requests/sec (default: unlimited). A safety ceiling.")
@click.option("--ignore-robots", "ignore_robots", is_flag=True,
              help="Skip the robots.txt courtesy check.")
@click.option("--i-own-this", "yes", is_flag=True,
              help="Skip the confirmation prompt for non-local targets.")
@click.option("--json", "as_json", is_flag=True,
              help="Emit the raw report as JSON.")
@click.option("--html", "html_path", type=click.Path(dir_okay=False), default=None,
              help="Write a shareable HTML report to PATH.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
@click.option("--no-save", "no_save", is_flag=True,
              help="Don't save this run to .prescale/runs/.")
def run(url: str, paths: tuple[str, ...], from_sitemap: bool, max_users: int,
        stage_seconds: float, latency_wall: float, error_threshold: float,
        method: str, timeout: float, max_rps: float | None, ignore_robots: bool,
        yes: bool, as_json: bool, html_path: str | None,
        store: str | None, no_save: bool) -> None:
    """Load test URL and report what breaks first.

    \b
    Examples:
        prescale run http://localhost:8000
        prescale run https://staging.myapp.com --path /api/search --path /pricing
        prescale run https://staging.myapp.com --from-sitemap -u 500 --i-own-this
        prescale run https://staging.myapp.com --i-own-this --html report.html
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

    if not ignore_robots and not as_json:
        disallowed = asyncio.run(check_robots(targets, timeout=timeout))
        if disallowed:
            console.print(f"[yellow]⚠ robots.txt disallows {len(disallowed)} of these "
                          "route(s) — testing anyway (use --ignore-robots to "
                          "silence):[/yellow]")
            for route in disallowed[:8]:
                console.print(f"    [yellow]{route_label(route)}[/yellow]")

    if not as_json:
        cap = f", capped at {max_rps:g} req/s" if max_rps else ""
        console.print(f"\n[bold]PreScale[/bold] — load testing [cyan]{url}[/cyan]  "
                      f"({len(targets)} route{'s' if len(targets) != 1 else ''}{cap})")
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
                method=method, timeout=timeout, max_rps=max_rps,
            ))
        else:
            with console.status("[bold blue]Warming up…") as status:
                stages, warning = asyncio.run(run_loadtest(
                    targets, levels=levels, stage_seconds=stage_seconds,
                    method=method, timeout=timeout, max_rps=max_rps,
                    progress_cb=render_progress(status),
                ))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    report = analyze(stages, latency_wall=latency_wall, error_threshold=error_threshold,
                     rate_capped=max_rps is not None)

    config = {
        "method": method,
        "max_users": max_users,
        "stage_seconds": stage_seconds,
        "latency_wall_s": latency_wall,
        "error_threshold": error_threshold,
        "max_rps": max_rps,
    }
    result = build_result(report, url=url, targets=targets, config=config, warning=warning)
    saved_path = None if no_save else write_result(result, store=store)

    if html_path:
        Path(html_path).write_text(render_html(result), encoding="utf-8")

    if as_json:
        click.echo(json.dumps(result, indent=2))
        return

    render_terminal(result)
    if saved_path or html_path:
        console.print()
    if saved_path:
        console.print(f"[green]✓[/green] Saved run to [cyan]{saved_path}[/cyan]")
    if html_path:
        console.print(f"[green]✓[/green] HTML report written to [cyan]{html_path}[/cyan]")
