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
from rich.markup import escape
from rich.panel import Panel

from prescale_cli.cloud import CloudError, require_credentials
from prescale_cli.commands.hostcheck import confirm_host, host_permission_option
from prescale_cli.commands.journeys import dir_option, refuse_missing_env, refuse_unallowed_writes
from prescale_cli.commands.replicaopts import app_option, app_timeout_option, start_replica
from prescale_cli.commands.upload import header_option, upload_after_run, upload_option
from prescale_cli.journeys.load import JourneyRun, first_to_break, journeys_block, ramp
from prescale_cli.journeys.model import Journey, load_dir
from prescale_cli.journeys.replay import check
from prescale_cli.live import LiveRamp, ramp_progress
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
from prescale_cli.profiles import PROFILES, lookup, scenario_block
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
@click.option("--warmup/--no-warmup", "warmup", default=True,
              help="Run a brief warmup before measuring (default: on).")
@click.option("--repeat", default=1, type=int,
              help="Run the whole ramp N times and pool results (default: 1).")
@click.option("--think-time", "think_time", default=0.0, type=float,
              help="Seconds each virtual user pauses between requests (default: 0).")
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
@click.option("--fail-under", "fail_under", default=None, type=int,
              help="Exit non-zero if it survives fewer than N users (a CI gate).")
@click.option("--profile", "profile_name", default=None,
              help="Frame the run as a launch scenario (see `prescale profiles`).")
@click.option("--journey", "only", multiple=True,
              help="Replay only this journey (repeatable). See `prescale journeys`.")
@click.option("--urls", "urls_only", is_flag=True,
              help="Test URLs, not journeys, even when prescale/journeys/ has some.")
@click.option("--allow-writes", "allow_writes", multiple=True, metavar="HOST",
              help="Let journeys that change data run against this non-local host "
                   "(repeatable).")
@dir_option
@app_option
@app_timeout_option
@host_permission_option
@header_option
@upload_option
def run(url: str, paths: tuple[str, ...], from_sitemap: bool, max_users: int,
        stage_seconds: float, latency_wall: float, error_threshold: float,
        method: str, timeout: float, max_rps: float | None, warmup: bool,
        repeat: int, think_time: float,
        ignore_robots: bool, yes: bool, as_json: bool, html_path: str | None,
        store: str | None, no_save: bool, fail_under: int | None,
        profile_name: str | None, only: tuple[str, ...], urls_only: bool,
        allow_writes: tuple[str, ...], directory: Path, app: str | None,
        app_timeout: float, host_permission: bool, headers: dict[str, str],
        upload: bool) -> None:
    """Load test URL and report what breaks first.

    When prescale/journeys/ has journeys, each one is replayed at load (users
    walk the whole journey: log in, add to cart, order) and the report names the
    journey and step that break first. Use --urls to test URLs instead.

    \b
    Examples:
        prescale run http://localhost:8000
        prescale run https://staging.myapp.com --path /api/search --path /pricing
        prescale run https://staging.myapp.com --from-sitemap -u 500 --i-own-this
        prescale run https://staging.myapp.com --i-own-this --html report.html
        prescale run https://staging.myapp.com --i-own-this --upload
        prescale run http://localhost:3000 --app "npm run build && npm start"
    """
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. http://localhost:8000).")
        raise SystemExit(1)

    if upload:
        try:
            require_credentials()
        except CloudError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise SystemExit(1)

    prof = lookup(profile_name) if profile_name else None
    if profile_name and prof is None:
        console.print(f"[red]Error:[/red] unknown profile '{profile_name}'. "
                      f"Try one of: {', '.join(PROFILES)}.")
        raise SystemExit(1)
    if prof is not None:
        max_users = prof.peak_users
        think_time = prof.think_time_s

    journeys = _journeys_to_run(directory, only, urls_only=urls_only,
                                url_mode=bool(paths or from_sitemap or method.upper() != "GET"))
    host = (parsed.hostname or "").lower()
    if journeys:
        refuse_unallowed_writes(journeys, host, {h.lower() for h in allow_writes})
        refuse_missing_env(journeys)

    if app:
        start_replica(app, url, timeout=app_timeout, console=console, quiet=as_json)

    is_local = host in _LOCAL_HOSTS
    if not is_local and not yes:
        if as_json:
            console.print(f"[red]Error:[/red] refusing to load-test non-local host "
                          f"'{host}' in --json mode without --i-own-this.")
            raise SystemExit(1)
        console.print(Panel(
            f"You're about to send real traffic to [bold]{host}[/bold] "
            f"(up to {max_users} concurrent users).\n"
            "Point this at a staging/preview URL you own — not production.\n"
            "Check it doesn't share production's database: the load reaches whatever it talks to.",
            title="⚠️  Heads up", border_style="yellow",
        ))
        if not click.confirm("Proceed?", default=False):
            raise SystemExit(0)
    if not is_local:
        confirm_host(url, console=console, permitted=host_permission, as_json=as_json,
                     timeout=timeout, headers=headers)

    config = {
        "method": method,
        "max_users": max_users,
        "stage_seconds": stage_seconds,
        "latency_wall_s": latency_wall,
        "error_threshold": error_threshold,
        "max_rps": max_rps,
        "warmup": warmup,
        "repeat": repeat,
        "think_time_s": think_time,
        "fail_under": fail_under,
        "profile": prof.name if prof else None,
    }
    finish = dict(prof=prof, no_save=no_save, store=store, html_path=html_path,
                  as_json=as_json, upload=upload, fail_under=fail_under)

    if journeys:
        report, result, live_mode = _run_journeys(
            journeys, url, config, latency_wall=latency_wall,
            error_threshold=error_threshold, timeout=timeout, headers=headers,
            replica=bool(app), as_json=as_json)
        _finish(result, report, live_mode=live_mode, **finish)
        return

    extra: list[str] = []
    if from_sitemap:
        if not as_json:
            console.print("[dim]Discovering routes from sitemap.xml…[/dim]")
        try:
            extra = asyncio.run(discover_sitemap(url, timeout=timeout, headers=headers))
        except Exception:  # discovery is best-effort; never block the run
            extra = []
        if not as_json:
            found = f"{len(extra)} route(s) found" if extra else "none found"
            console.print(f"  [dim]sitemap: {found}[/dim]")

    targets = build_targets(url, paths=paths, extra=extra)

    if not ignore_robots and not as_json:
        disallowed = asyncio.run(check_robots(targets, timeout=timeout, headers=headers))
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

    progress = ramp_progress(console, latency_wall=latency_wall, as_json=as_json)
    live_mode = isinstance(progress, LiveRamp)
    try:
        with progress:
            stages, warning = asyncio.run(run_loadtest(
                targets, levels=levels, stage_seconds=stage_seconds,
                method=method, timeout=timeout, max_rps=max_rps, warmup=warmup,
                repeat=repeat, think_time=think_time, headers=headers,
                host_permission=True,
                progress_cb=progress.starting, on_stage=progress.finished,
            ))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    report = analyze(stages, latency_wall=latency_wall, error_threshold=error_threshold,
                     rate_capped=max_rps is not None)
    result = build_result(report, url=url, targets=targets, config=config, warning=warning,
                          replica=bool(app))
    _finish(result, report, live_mode=live_mode, **finish)


def _finish(result: dict, report, *, prof, no_save: bool, store: str | None,
            html_path: str | None, as_json: bool, upload: bool, fail_under: int | None,
            live_mode: bool) -> None:
    """Save, render, upload and gate a finished run (URLs or journeys alike)."""
    if prof is not None:
        result["profile"] = scenario_block(prof, report.survives_users)
    saved_path = None if no_save else write_result(result, store=store)

    if html_path:
        Path(html_path).write_text(render_html(result), encoding="utf-8")

    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        render_terminal(result, show_ramp=not live_mode)
        if saved_path or html_path:
            console.print()
        if saved_path:
            console.print(f"[green]✓[/green] Saved run to [cyan]{saved_path}[/cyan]")
        if html_path:
            console.print(f"[green]✓[/green] HTML report written to [cyan]{html_path}[/cyan]")

    if upload:
        upload_after_run(result, as_json=as_json)

    if fail_under is not None and report.survives_users < fail_under:
        Console(stderr=True).print(
            f"[red]✗ fail-under:[/red] survives ~{report.survives_users} < {fail_under}")
        raise SystemExit(1)


def _journeys_to_run(directory: Path, only: tuple[str, ...], *, urls_only: bool,
                     url_mode: bool) -> list[Journey]:
    """The journeys this run replays: none in URL mode (--urls, --path,
    --from-sitemap or a non-GET --method), else every valid file in DIRECTORY,
    narrowed by --journey. A broken journey file stops the run rather than
    silently falling back to testing URLs."""
    if urls_only or url_mode:
        if only:
            console.print("[red]Error:[/red] --journey can't be combined with --urls, "
                          "--path, --from-sitemap or --method.")
            raise SystemExit(2)
        return []
    found, errors = load_dir(directory)
    for error in errors:
        console.print(f"[red]Error:[/red] {escape(error)}", highlight=False)
    if errors:
        raise SystemExit(2)
    if only:
        missing = sorted(set(only) - {j.name for j in found})
        if missing:
            console.print(f"[red]Error:[/red] no journey named {', '.join(missing)} "
                          f"in {escape(str(directory))}.", highlight=False)
            raise SystemExit(2)
        found = [j for j in found if j.name in only]
    return found


def _run_journeys(journeys: list[Journey], url: str, config: dict, *, latency_wall: float,
                  error_threshold: float, timeout: float, headers: dict[str, str],
                  replica: bool, as_json: bool) -> tuple:
    """The isolation pass: check each journey once, then ramp each one that
    replays on its own. Returns (report, result, live_mode) for the first
    journey to break, with every journey's verdict in result["journeys"]."""
    if not as_json:
        console.print(f"\n[bold]PreScale[/bold] — replaying {len(journeys)} "
                      f"journey{'s' if len(journeys) != 1 else ''} against [cyan]{url}[/cyan]")
    checks = asyncio.run(_check_all(journeys, url, timeout=timeout, headers=headers))
    runs = [JourneyRun(j, c) for j, c in zip(journeys, checks)]
    levels = default_levels(config["max_users"])
    live_mode = False
    for run in runs:
        name = escape(run.journey.name)
        if not run.check.ok:
            failed = run.check.failed
            what = "stale" if run.check.stale else "couldn't run"
            console.print(f"[yellow]⚠ {name}: {what}, not load-tested[/yellow] "
                          f"[dim]({escape(failed.step.name)}: {escape(failed.problem or '')})"
                          "[/dim]", highlight=False)
            continue
        if not as_json:
            console.print(f"\n[bold]Journey {name}[/bold] [dim]({run.journey.type}, "
                          f"{len(run.journey.steps)} steps)[/dim]", highlight=False)
        progress = ramp_progress(console, latency_wall=latency_wall, as_json=as_json)
        live_mode = isinstance(progress, LiveRamp)
        try:
            with progress:
                stages, run.warning = asyncio.run(ramp(
                    run.journey, url, levels=levels, stage_seconds=config["stage_seconds"],
                    timeout=timeout, max_rps=config["max_rps"], warmup=config["warmup"],
                    repeat=config["repeat"], headers=headers,
                    progress_cb=progress.starting, on_stage=progress.finished))
        except LoadError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise SystemExit(1)
        run.report = analyze(stages, latency_wall=latency_wall,
                             error_threshold=error_threshold,
                             rate_capped=config["max_rps"] is not None)

    worst = first_to_break(runs)
    if worst is None:
        console.print("[red]Error:[/red] no journey replays against this app, so there's "
                      "nothing to load-test. Run `prescale journeys verify` for details.")
        raise SystemExit(1)
    warnings = list(dict.fromkeys(r.warning for r in runs if r.warning))
    result = build_result(worst.report, url=url,
                          targets=[s.label for s in worst.journey.steps],
                          config={**config, "mode": "journeys"},
                          warning=" ".join(warnings) or None, replica=replica)
    result["verdict"]["culprit_journey"] = worst.journey.name
    result["journeys"] = journeys_block(runs)
    return worst.report, result, live_mode


async def _check_all(journeys: list[Journey], url: str, *, timeout: float,
                     headers: dict[str, str]):
    return [await check(j, url, timeout=timeout, headers=headers) for j in journeys]
