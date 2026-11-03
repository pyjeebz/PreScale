"""`prescale ci` - capacity-check a deploy from CI and report it on the PR.

Built for GitHub Actions (the PreScale action wraps it), usable from any CI:
investigate the deploy URL (or, when the checkout has prescale/journeys/,
replay the journeys at load), upload the Result, compare it with the baseline
(server-side, the same rule as the dashboard), write a job summary, and keep
one capacity comment on the PR up to date.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import click
import httpx
from rich.console import Console

from prescale_cli.ci import (
    comment_marker,
    comparison_for,
    find_pull_request,
    github_context,
    render_comment,
    render_host_skip,
    render_stale_only,
    upsert_pr_comment,
)
from prescale_cli.cloud import CloudError, parse_headers, require_credentials, upload_result
from prescale_cli.commands.journeys import dir_option, refuse_missing_env, refuse_unallowed_writes
from prescale_cli.commands.replicaopts import app_option, app_timeout_option, start_replica
from prescale_cli.commands.run import run_journeys
from prescale_cli.hosts import PERMISSION_ENV
from prescale_cli.investigate import investigate as run_investigate
from prescale_cli.journeys.load import NoJourneyReplaysError
from prescale_cli.journeys.model import load_dir
from prescale_cli.live import ramp_progress
from prescale_cli.loadtest import HostPolicyError, LoadError, default_levels, probe_host
from prescale_cli.result import write_result

console = Console()


def _lines(value: str | None) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _annotate(level: str, message: str) -> None:
    """A GitHub Actions annotation (shown on the run and the PR checks)."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        click.echo(f"::{level}::{message}")


@click.command()
@click.argument("url", required=False)
@click.option("--target", "target", envvar="PRESCALE_TARGET", required=True,
              help="The PreScale target this deploy belongs to (a hostname, e.g. "
                   "staging.myapp.com). Env: PRESCALE_TARGET.")
@click.option("--path", "paths", multiple=True, help="Extra route to test (repeatable).")
@click.option("--header", "-H", "header_values", multiple=True,
              help="Extra request header 'Name: value' (repeatable). Newline-separated "
                   "headers in $PRESCALE_HEADERS are added too, so secrets stay out of argv.")
@click.option("--max-users", "-u", default=100, type=int,
              help="Peak virtual users (default 100: gentle enough to run on every PR).")
@click.option("--stage-seconds", "-s", default=5.0, type=float,
              help="Seconds to hold each load level.")
@click.option("--max-rps", default=None, type=float, help="Cap aggregate requests/sec.")
@click.option("--fail-on-regression", is_flag=True,
              help="Exit non-zero on a confident capacity regression vs the baseline.")
@click.option("--comment/--no-comment", default=True,
              help="Post or update the capacity comment on the PR (needs GITHUB_TOKEN).")
@click.option("--allow-production", is_flag=True,
              help="Run even when the deployment environment is production.")
@click.option("--host-permission", "host_permission", is_flag=True, envvar=PERMISSION_ENV,
              help="Confirm the deploy's host allows load testing (Vercel, Netlify and "
                   f"Cloudflare restrict it; otherwise PreScale skips). Env: {PERMISSION_ENV}=1.")
@click.option("--stale", "stale", type=click.Choice(["warn", "fail"]), default="warn",
              show_default=True,
              help="Journey runs: what a journey that no longer replays does to the check. It's "
                   "always reported on the PR; 'fail' also fails the job.")
@click.option("--allow-writes", "allow_writes", multiple=True, metavar="HOST",
              help="Let journeys that change data run against this non-local host "
                   "(repeatable). Not needed with --app: the replica is local.")
@dir_option
@app_option
@app_timeout_option
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
def ci(url: str | None, target: str, paths: tuple[str, ...], header_values: tuple[str, ...],
       max_users: int, stage_seconds: float, max_rps: float | None, fail_on_regression: bool,
       comment: bool, allow_production: bool, host_permission: bool, stale: str,
       allow_writes: tuple[str, ...], directory: Path, app: str | None,
       app_timeout: float, store: str | None) -> None:
    """Capacity-check a deploy from CI, upload it, and comment on the PR.

    With no URL, uses the deploy URL from a GitHub `deployment_status` event. With
    --app, PreScale builds and starts your app in the job and tests it at
    http://localhost:3000 (or the URL you pass), so no deploy is needed: run it on
    `pull_request`, and on pushes to main for the baseline.
    Needs PRESCALE_TOKEN; PRESCALE_URL points at your dashboard if it isn't the
    default. Production deploys are skipped unless you pass --allow-production, and
    deploys on hosts that restrict load testing unless you pass --host-permission.

    \b
    Example (GitHub Actions, on: deployment_status):
        prescale ci --target staging.myapp.com --fail-on-regression

    \b
    Example (replica mode, on: pull_request):
        prescale ci --target myapp.com --app "npm run build && npm start"

    When prescale/journeys/ (or --dir) has journeys, they're replayed at load
    instead of the URL routes, and the PR comment shows each journey's verdict.
    """
    ctx = github_context()

    if ctx.event_name == "deployment_status" and ctx.deployment_state not in (None, "success"):
        console.print(f"[dim]Deployment is {ctx.deployment_state}, not success. "
                      "Nothing to test.[/dim]")
        return
    if ctx.is_production and not allow_production:
        console.print(f"[yellow]Skipping:[/yellow] {ctx.deployment_environment} is a production "
                      "deploy. PreScale only ramps load on previews and staging by default "
                      "(--allow-production to override).")
        _annotate("notice", "PreScale skipped a production deploy.")
        return

    url = url or ("http://localhost:3000" if app else ctx.deployment_url)
    if not url:
        raise click.UsageError("No URL to test. Pass one, or run on a deployment_status event.")

    # A checkout with journey files replays them; without one (a deploy event with no
    # checkout) it's a URL run as before. Broken files and missing secrets stop the
    # job here, before an app is built.
    journeys, errors = load_dir(directory)
    for error in errors:
        console.print(f"[red]Error:[/red] {error}", markup=False)
        _annotate("error", f"PreScale: {error}")
    if errors:
        raise SystemExit(2)
    if journeys:
        host = (httpx.URL(url).host or "").lower()
        try:
            refuse_unallowed_writes(journeys, host, {h.lower() for h in allow_writes})
            refuse_missing_env(journeys)
        except SystemExit:
            _annotate("error", "PreScale refused to replay the journeys (see the log: "
                               "journeys that change data need allow-writes for this host, "
                               "and every {{env.NAME}} they read must be set).")
            raise
        if paths or os.environ.get("PRESCALE_PATHS"):
            console.print("[dim]Journeys are replayed, so --path / paths are ignored.[/dim]")

    try:
        headers = parse_headers(header_values + tuple(_lines(os.environ.get("PRESCALE_HEADERS"))))
        creds = require_credentials()
    except (ValueError, CloudError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1) from None

    github_token = os.environ.get("GITHUB_TOKEN")
    pr = None
    if ctx.pr_number is None and github_token:
        try:
            pr = find_pull_request(ctx, github_token)
        except httpx.HTTPError:
            pr = None
    pr_number = ctx.pr_number or (pr or {}).get("number")
    branch = ctx.branch or ((pr or {}).get("head") or {}).get("ref")

    # The deploy usually has no checkout here: take commit/branch from GitHub.
    if ctx.short_sha:
        os.environ["PRESCALE_GIT_COMMIT"] = ctx.short_sha
    if branch:
        os.environ["PRESCALE_GIT_BRANCH"] = branch

    if app:
        start_replica(app, url, timeout=app_timeout, console=console, quiet=False)

    if journeys:
        _ci_journeys(journeys, url, target=target, ctx=ctx, creds=creds, headers=headers,
                     max_users=max_users, stage_seconds=stage_seconds, max_rps=max_rps,
                     store=store, comment=comment, pr_number=pr_number,
                     github_token=github_token, host_permission=host_permission,
                     replica=bool(app), stale=stale, fail_on_regression=fail_on_regression)
        return

    extra_paths = tuple(paths) + tuple(_lines(os.environ.get("PRESCALE_PATHS")))
    console.print(f"[bold]PreScale[/bold] — capacity check of [cyan]{url}[/cyan] for "
                  f"[bold]{target}[/bold]"
                  + (f" (PR #{pr_number})" if pr_number else ""))
    levels = default_levels(max_users)
    console.print(f"[dim]Ramp: up to {max_users} users in {len(levels)} steps of "
                  f"{stage_seconds:g}s (~{round(len(levels) * stage_seconds)}s of load). "
                  + ("The load reaches whatever this job's environment points the app at."
                     if app else
                     "Previews often share production's database: the load reaches it too.")
                  + "[/dim]")
    try:
        with ramp_progress(console) as progress:
            result = asyncio.run(run_investigate(
                url, max_users=max_users, paths=extra_paths, stage_seconds=stage_seconds,
                max_rps=max_rps, store=store, headers=headers, host_permission=host_permission,
                replica=bool(app), progress_cb=progress.starting, on_stage=progress.finished,
                on_probe=progress.diagnosing))
    except HostPolicyError as exc:
        _skip_restricted_host(exc.rule, target=target, ctx=ctx, comment=comment,
                              pr_number=pr_number, github_token=github_token)
        return
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        _annotate("error", f"PreScale couldn't load-test {url}: {exc}")
        raise SystemExit(1) from None

    if _report(result, url=url, target=target, ctx=ctx, creds=creds, comment=comment,
               pr_number=pr_number, github_token=github_token,
               fail_on_regression=fail_on_regression):
        raise SystemExit(1)


def _ci_journeys(journeys, url: str, *, target: str, ctx, creds, headers: dict[str, str],
                 max_users: int, stage_seconds: float, max_rps: float | None,
                 store: str | None, comment: bool, pr_number: int | None,
                 github_token: str | None, host_permission: bool, replica: bool, stale: str,
                 fail_on_regression: bool) -> None:
    """Replay the checkout's journeys at load, upload, comment, and gate."""
    # Journey ramps skip the preflight that checks the host, so check it here.
    if not replica and not host_permission:
        rule = asyncio.run(probe_host(url, headers=headers))
        if rule is not None:
            _skip_restricted_host(rule, target=target, ctx=ctx, comment=comment,
                                  pr_number=pr_number, github_token=github_token)
            return
    console.print(f"[bold]PreScale[/bold] — journey check for [bold]{target}[/bold]"
                  + (f" (PR #{pr_number})" if pr_number else ""))
    config = {"method": "GET", "max_users": max_users, "stage_seconds": stage_seconds,
              "latency_wall_s": 2.0, "error_threshold": 0.02, "max_rps": max_rps,
              "warmup": True, "repeat": 1, "think_time_s": 0.0, "fail_under": None,
              "profile": None}
    try:
        _, result, _ = run_journeys(journeys, url, config, latency_wall=2.0,
                                    error_threshold=0.02, timeout=10.0, headers=headers,
                                    replica=replica, as_json=False, diagnose=True)
    except NoJourneyReplaysError as exc:
        body = render_stale_only(exc.runs, target=target)
        _publish(body, target=target, ctx=ctx, comment=comment, pr_number=pr_number,
                 github_token=github_token)
        # Only "stale" (the app answered differently) follows --stale. An app that
        # doesn't answer, or fails with a single user, fails the check like URL mode.
        broken = [r.journey.name for r in exc.runs if r.check.outcome != "stale"]
        if broken:
            _annotate("error", f"PreScale: {', '.join(broken)} failed with a single user "
                               "(no answer, or a 5xx), so nothing was load-tested.")
            raise SystemExit(1)
        level = "error" if stale == "fail" else "warning"
        _annotate(level, "PreScale: no journey replays against this build, so nothing was "
                         "load-tested. Update the journey files if the app changed on purpose.")
        if stale == "fail":
            raise SystemExit(1)
        return
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        _annotate("error", f"PreScale couldn't load-test {url}: {exc}")
        raise SystemExit(1) from None
    write_result(result, store=store)

    stale_names = [j["name"] for j in result["journeys"] if j["status"] == "stale"]
    broken = [j["name"] for j in result["journeys"] if j["status"] in ("error", "unreachable")]
    regressed = _report(result, url=url, target=target, ctx=ctx, creds=creds, comment=comment,
                        pr_number=pr_number, github_token=github_token,
                        fail_on_regression=fail_on_regression)
    if stale_names:
        level = "error" if stale == "fail" else "warning"
        what = ("replays against this build, so it wasn't" if len(stale_names) == 1
                else "replay against this build, so they weren't")
        _annotate(level, f"PreScale: {', '.join(stale_names)} no longer {what} load-tested.")
    if broken:
        _annotate("error", f"PreScale: {', '.join(broken)} failed with a single user (no "
                           "answer, or a 5xx), so they weren't load-tested.")
    if regressed or broken or (stale_names and stale == "fail"):
        raise SystemExit(1)


def _publish(body: str, *, target: str, ctx, comment: bool, pr_number: int | None,
             github_token: str | None) -> None:
    """The job summary, and the one PreScale comment on the PR."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as fh:
            fh.write(body + "\n")
    if comment and pr_number and github_token and ctx.repository:
        try:
            action = upsert_pr_comment(ctx, github_token, pr_number, body, comment_marker(target))
            console.print(f"[green]✓[/green] PR #{pr_number} comment {action}")
        except httpx.HTTPError as exc:
            console.print(f"[yellow]Couldn't comment on PR #{pr_number}:[/yellow] {exc}. "
                          "Does the job have `pull-requests: write`?")
    elif comment and not pr_number:
        console.print("[dim]No open PR for this commit, so no PR comment.[/dim]")


def _report(result: dict, *, url: str, target: str, ctx, creds, comment: bool,
            pr_number: int | None, github_token: str | None,
            fail_on_regression: bool) -> bool:
    """Upload the run, comment on the PR, and annotate a regression. Returns
    whether the job should fail (a regression with --fail-on-regression); the
    caller exits, after any notes of its own."""
    try:
        upload = upload_result(result, creds, pr=pr_number, target=target)
    except CloudError as exc:
        console.print(f"[red]✗ upload failed:[/red] {exc}")
        _annotate("error", f"PreScale upload failed: {exc}")
        raise SystemExit(1) from None

    body = render_comment(result, upload, target=target, sha=ctx.sha)
    comparison = comparison_for(result, upload)
    verdict = result["verdict"]
    sent = sum(stage.get("total", 0) for stage in result.get("stages", []))
    console.print(f"[dim]Sent {sent:,} requests while measuring.[/dim]")
    console.print(f"survives ~{verdict['survives_users']} users"
                  + (f" · {comparison['kind']} {round(comparison['pct'] * 100):+d}% vs "
                     f"{comparison['against']}" if comparison else " · first run")
                  + f"\n[green]✓[/green] uploaded → [cyan]{upload.get('url')}[/cyan]")

    _publish(body, target=target, ctx=ctx, comment=comment, pr_number=pr_number,
             github_token=github_token)

    kind = comparison["kind"] if comparison else None
    if kind == "regressed":
        _annotate("error", f"Capacity regressed {round(comparison['pct'] * 100)}% vs "
                           f"{comparison['against']}.")
        return fail_on_regression
    if kind == "possible":
        _annotate("warning", f"Possible capacity regression {round(comparison['pct'] * 100)}% "
                             f"vs {comparison['against']} (bands overlap).")
    return False


def _skip_restricted_host(rule, *, target: str, ctx, comment: bool, pr_number: int | None,
                          github_token: str | None) -> None:
    """The deploy's host restricts load testing: say so everywhere, and pass the check."""
    console.print(f"[yellow]Skipping:[/yellow] {rule.rule} Set host-permission (or "
                  f"--host-permission) if you have {rule.name}'s permission. {rule.link}")
    _annotate("notice", f"PreScale skipped this {rule.name} deploy: {rule.rule}")
    body = render_host_skip(rule, target=target)
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as fh:
            fh.write(body + "\n")
    if comment and pr_number and github_token and ctx.repository:
        try:
            upsert_pr_comment(ctx, github_token, pr_number, body, comment_marker(target))
        except httpx.HTTPError:
            pass
