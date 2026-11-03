"""`prescale investigate` - find what breaks first, then probe it to explain why."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from urllib.parse import urlparse

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.cloud import CloudError, require_credentials
from prescale_cli.commands.audit import _ICONS as _AUDIT_ICONS
from prescale_cli.commands.hostcheck import confirm_host, host_permission_option
from prescale_cli.commands.journeys import dir_option, refuse_missing_env, refuse_unallowed_writes
from prescale_cli.commands.replicaopts import app_option, app_timeout_option, start_replica
from prescale_cli.commands.run import _journeys_to_run, run_journeys
from prescale_cli.commands.upload import header_option, upload_after_run, upload_option
from prescale_cli.investigate import _ERROR_THRESHOLD, _LATENCY_WALL_S, audit_block
from prescale_cli.investigate import investigate as run_investigate
from prescale_cli.journeys.load import NoJourneyReplaysError
from prescale_cli.live import LiveRamp, ramp_progress
from prescale_cli.loadtest import LoadError
from prescale_cli.profiles import PROFILES, lookup, scenario_block
from prescale_cli.render import render_investigation, render_terminal
from prescale_cli.result import latest_id, load_result, write_result

console = Console()

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}


@click.command()
@click.argument("url", required=False)
@click.option("--path", "paths", multiple=True,
              help="Extra route to test, relative to URL (repeatable).")
@click.option("--max-users", "-u", default=200, type=int, help="Peak virtual users.")
@click.option("--stage-seconds", "-s", default=5.0, type=float,
              help="Seconds to hold each load level.")
@click.option("--max-rps", default=None, type=float, help="Cap aggregate requests/sec.")
@click.option("--i-own-this", "yes", is_flag=True,
              help="Skip the confirmation prompt for non-local targets.")
@click.option("--json", "as_json", is_flag=True, help="Emit the full Result as JSON.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
@click.option("--fail-under", "fail_under", default=None, type=int,
              help="Exit non-zero if it survives fewer than N users (a CI gate).")
@click.option("--profile", "profile_name", default=None,
              help="Test against a launch scenario (see `prescale profiles`); ramps to 1.5x "
                   "its peak to show headroom.")
@click.option("--audit", "with_audit", is_flag=True,
              help="Also run the load-free HTTP hygiene audit.")
@click.option("--journey", "only", multiple=True,
              help="Investigate only this journey (repeatable). Default: every journey "
                   "in prescale/journeys/.")
@click.option("--no-combined", "no_combined", is_flag=True,
              help="Skip ramping the journeys together (no interference check).")
@click.option("--urls", "urls_only", is_flag=True,
              help="Investigate URLs, even when prescale/journeys/ has journeys.")
@click.option("--allow-writes", "allow_writes", multiple=True, metavar="HOST",
              help="Let journeys that change data run against this non-local host, "
                   "e.g. staging.myapp.com (repeatable).")
@dir_option
@app_option
@app_timeout_option
@host_permission_option
@header_option
@upload_option
def investigate(url: str | None, paths: tuple[str, ...], max_users: int,
                stage_seconds: float, max_rps: float | None, yes: bool,
                as_json: bool, store: str | None, fail_under: int | None,
                profile_name: str | None, with_audit: bool, only: tuple[str, ...],
                no_combined: bool, urls_only: bool, allow_writes: tuple[str, ...],
                directory: Path, app: str | None, app_timeout: float,
                host_permission: bool, headers: dict[str, str], upload: bool) -> None:
    """Find what breaks first, then probe it to explain WHY - and how to fix it.

    When prescale/journeys/ has journeys, the journey and step that break first
    are probed (with the journey's state, e.g. logged in, cart filled). Use
    --urls to investigate URLs instead. With no URL, re-investigates the latest
    saved run's target.

    \b
    Examples:
        prescale investigate http://localhost:8000
        prescale investigate https://staging.myapp.com --i-own-this
        prescale investigate https://staging.myapp.com --i-own-this --upload
        prescale investigate https://staging.myapp.com --profile hn-frontpage --audit
        prescale investigate            # re-investigate the latest saved run
        prescale investigate http://localhost:3000 --app "npm run build && npm start"
    """
    if upload:
        try:
            require_credentials()
        except CloudError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise SystemExit(1)

    if url is None:
        last = latest_id(store=store)
        if last is None:
            console.print("[dim]No saved runs yet — try "
                          "[bold]prescale investigate <url>[/bold].[/dim]")
            raise SystemExit(0)
        url = load_result(last, store=store)["target"]["url"]
        (Console(stderr=True) if as_json else console).print(
            f"[dim]Re-investigating latest run: {url}[/dim]")

    prof = lookup(profile_name) if profile_name else None
    if profile_name and prof is None:
        console.print(f"[red]Error:[/red] unknown profile '{profile_name}'. "
                      f"Try one of: {', '.join(PROFILES)}.")
        raise SystemExit(1)
    if prof is not None:
        # Past the peak, so the band around it is measured and headroom shows.
        max_users = max(prof.peak_users, round(prof.peak_users * 1.5))

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        console.print(f"[red]Error:[/red] '{url}' doesn't look like a URL "
                      "(expected e.g. http://localhost:8000).")
        raise SystemExit(1)

    journeys = _journeys_to_run(directory, only, urls_only=urls_only, url_mode=bool(paths))
    if journeys:
        host = (parsed.hostname or "").lower()
        refuse_unallowed_writes(journeys, host, {h.lower() for h in allow_writes})
        refuse_missing_env(journeys)

    if app:
        start_replica(app, url, timeout=app_timeout, console=console, quiet=as_json)

    host = (parsed.hostname or "").lower()
    if host not in _LOCAL_HOSTS and not yes:
        if as_json:
            console.print(f"[red]Error:[/red] refusing non-local host '{host}' in "
                          "--json mode without --i-own-this.")
            raise SystemExit(1)
        console.print(Panel(
            f"investigate sends real traffic to [bold]{host}[/bold] (a ramp plus a few "
            "probes).\nPoint it at a staging/preview URL you own — not production.\n"
            "Check it doesn't share production's database: the load reaches whatever it talks to.",
            title="⚠️  Heads up", border_style="yellow"))
        if not click.confirm("Proceed?", default=False):
            raise SystemExit(0)
    if host not in _LOCAL_HOSTS:
        confirm_host(url, console=console, permitted=host_permission, as_json=as_json,
                     headers=headers)

    if journeys:
        result, live_mode = _investigate_journeys(
            journeys, url, max_users=max_users, stage_seconds=stage_seconds,
            max_rps=max_rps, prof=prof, headers=headers, replica=bool(app),
            as_json=as_json, combined=not no_combined, with_audit=with_audit, store=store)
        _show(result, as_json=as_json, live_mode=live_mode, upload=upload,
              fail_under=fail_under)
        return

    progress = ramp_progress(console, latency_wall=_LATENCY_WALL_S, as_json=as_json)
    live_mode = isinstance(progress, LiveRamp)
    try:
        with progress:
            result = asyncio.run(run_investigate(
                url, max_users=max_users, paths=paths, stage_seconds=stage_seconds,
                max_rps=max_rps, store=store, headers=headers,
                think_time=prof.think_time_s if prof else 0.0, profile=prof,
                audit=with_audit, host_permission=True, replica=bool(app),
                progress_cb=progress.starting, on_stage=progress.finished,
                on_probe=progress.diagnosing))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)
    _show(result, as_json=as_json, live_mode=live_mode, upload=upload, fail_under=fail_under)


def _investigate_journeys(journeys, url: str, *, max_users: int, stage_seconds: float,
                          max_rps: float | None, prof, headers: dict[str, str],
                          replica: bool, as_json: bool, combined: bool, with_audit: bool,
                          store: str | None) -> tuple[dict, bool]:
    """Ramp the journeys (as `run` does), then probe the step that broke first."""
    config = {"method": "GET", "max_users": max_users, "stage_seconds": stage_seconds,
              "latency_wall_s": _LATENCY_WALL_S, "error_threshold": _ERROR_THRESHOLD,
              "max_rps": max_rps, "warmup": True, "repeat": 1,
              "think_time_s": prof.think_time_s if prof else 0.0,
              "profile": prof.name if prof else None}
    err = Console(stderr=True) if as_json else console
    try:
        report, result, live_mode = run_journeys(
            journeys, url, config, latency_wall=_LATENCY_WALL_S,
            error_threshold=_ERROR_THRESHOLD, timeout=10.0, headers=headers,
            replica=replica, as_json=as_json, combined=combined, diagnose=True)
    except LoadError as exc:
        err.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)
    except NoJourneyReplaysError:
        err.print("[red]Error:[/red] no journey replays against this app, so there's "
                  "nothing to investigate. Run `prescale journeys verify` for details.")
        raise SystemExit(1)
    if prof is not None:
        result["profile"] = scenario_block(prof, report.survives_users)
    if with_audit:
        result["audit"] = asyncio.run(audit_block(url, headers=headers))
    write_result(result, store=store)
    return result, live_mode


def _show(result: dict, *, as_json: bool, live_mode: bool, upload: bool,
          fail_under: int | None) -> None:
    """Print, upload and gate an investigated Result (URLs or journeys alike)."""
    if as_json:
        click.echo(json.dumps(result, indent=2))
    else:
        render_terminal(result, show_ramp=not live_mode)
        render_investigation(result)
        if result.get("audit"):
            console.print("\n[bold]HTTP hygiene[/bold]")
            for finding in result["audit"]:
                icon = _AUDIT_ICONS.get(finding["status"], "•")
                console.print(f"{icon} [bold]{finding['name']}[/bold]  {finding['detail']}")
        if result.get("investigation") is None:
            if (result.get("combined") or {}).get("onset_users") is not None \
                    or result["verdict"]["onset_users"] is not None:
                console.print("\n[yellow]⚠[/yellow] It broke, but PreScale couldn't probe the "
                              "step that broke (see above).")
            else:
                console.print("\n[green]✓[/green] Held up — nothing to diagnose.")
        console.print(f"[dim]saved as {result['id']}[/dim]")

    if upload:
        upload_after_run(result, as_json=as_json)

    survives = result["verdict"]["survives_users"]
    if fail_under is not None and survives < fail_under:
        Console(stderr=True).print(
            f"[red]✗ fail-under:[/red] survives ~{survives} < {fail_under}")
        raise SystemExit(1)
