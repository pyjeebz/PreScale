"""`prescale ci` - capacity-check a deploy from CI and report it on the PR.

Built for GitHub Actions (the PreScale action wraps it), usable from any CI:
investigate the deploy URL, upload the Result, compare it with the baseline
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
    find_pull_request,
    github_context,
    render_comment,
    upsert_pr_comment,
)
from prescale_cli.cloud import CloudError, parse_headers, require_credentials, upload_result
from prescale_cli.investigate import investigate as run_investigate
from prescale_cli.loadtest import LoadError

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
@click.option("--max-users", "-u", default=200, type=int, help="Peak virtual users.")
@click.option("--stage-seconds", "-s", default=5.0, type=float,
              help="Seconds to hold each load level.")
@click.option("--max-rps", default=None, type=float, help="Cap aggregate requests/sec.")
@click.option("--fail-on-regression", is_flag=True,
              help="Exit non-zero on a confident capacity regression vs the baseline.")
@click.option("--comment/--no-comment", default=True,
              help="Post or update the capacity comment on the PR (needs GITHUB_TOKEN).")
@click.option("--allow-production", is_flag=True,
              help="Run even when the deployment environment is production.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
def ci(url: str | None, target: str, paths: tuple[str, ...], header_values: tuple[str, ...],
       max_users: int, stage_seconds: float, max_rps: float | None, fail_on_regression: bool,
       comment: bool, allow_production: bool, store: str | None) -> None:
    """Capacity-check a deploy from CI, upload it, and comment on the PR.

    With no URL, uses the deploy URL from a GitHub `deployment_status` event.
    Needs PRESCALE_TOKEN; PRESCALE_URL points at your dashboard if it isn't the
    default. Production deploys are skipped unless you pass --allow-production.

    \b
    Example (GitHub Actions, on: deployment_status):
        prescale ci --target staging.myapp.com --fail-on-regression
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

    url = url or ctx.deployment_url
    if not url:
        raise click.UsageError("No URL to test. Pass one, or run on a deployment_status event.")

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

    extra_paths = tuple(paths) + tuple(_lines(os.environ.get("PRESCALE_PATHS")))
    console.print(f"[bold]PreScale[/bold] — capacity check of [cyan]{url}[/cyan] for "
                  f"[bold]{target}[/bold]"
                  + (f" (PR #{pr_number})" if pr_number else ""))
    try:
        result = asyncio.run(run_investigate(
            url, max_users=max_users, paths=extra_paths, stage_seconds=stage_seconds,
            max_rps=max_rps, store=store, headers=headers))
    except LoadError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        _annotate("error", f"PreScale couldn't load-test {url}: {exc}")
        raise SystemExit(1) from None

    try:
        upload = upload_result(result, creds, pr=pr_number, target=target)
    except CloudError as exc:
        console.print(f"[red]✗ upload failed:[/red] {exc}")
        _annotate("error", f"PreScale upload failed: {exc}")
        raise SystemExit(1) from None

    body = render_comment(result, upload, target=target, sha=ctx.sha)
    comparison = upload.get("comparison")
    verdict = result["verdict"]
    console.print(f"survives ~{verdict['survives_users']} users"
                  + (f" · {comparison['kind']} {round(comparison['pct'] * 100):+d}% vs "
                     f"{comparison['against']}" if comparison else " · first run")
                  + f"\n[green]✓[/green] uploaded → [cyan]{upload.get('url')}[/cyan]")

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

    kind = comparison["kind"] if comparison else None
    if kind == "regressed":
        _annotate("error", f"Capacity regressed {round(comparison['pct'] * 100)}% vs "
                           f"{comparison['against']}.")
        if fail_on_regression:
            raise SystemExit(1)
    elif kind == "possible":
        _annotate("warning", f"Possible capacity regression {round(comparison['pct'] * 100)}% "
                             f"vs {comparison['against']} (bands overlap).")
