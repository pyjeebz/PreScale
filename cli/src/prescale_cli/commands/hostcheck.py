"""`--host-permission` and the check behind it, shared by `run` and `investigate`.

Before any load, one normal request tells PreScale whether the target's host
restricts load testing. If it does, PreScale explains the rule and asks; where
nobody can answer (--json, no terminal), it stops unless permission was given.
"""

from __future__ import annotations

import asyncio
import sys

import click
from rich.console import Console
from rich.panel import Panel

from prescale_cli.hosts import PERMISSION_ENV
from prescale_cli.loadtest import probe_host

host_permission_option = click.option(
    "--host-permission", "host_permission", is_flag=True, envvar=PERMISSION_ENV,
    help="Confirm the target's host allows this load test. Vercel, Netlify and Cloudflare "
         f"restrict it; PreScale asks first otherwise. Env: {PERMISSION_ENV}=1.")


def confirm_host(url: str, *, console: Console, permitted: bool, as_json: bool,
                 timeout: float = 10.0, headers: dict[str, str] | None = None) -> None:
    """Return if it's fine to load-test URL's host; exit otherwise."""
    if permitted:
        return
    rule = asyncio.run(probe_host(url, timeout=timeout, headers=headers))
    if rule is None:
        return
    console.print(Panel(
        f"{rule.rule}\n[dim]{rule.link}[/dim]\n\n"
        f"Only continue if you have {rule.name}'s permission. Otherwise, test your app "
        "locally or on staging you're allowed to load.",
        title=f"⚠️  {rule.name} restricts load testing", border_style="yellow",
    ))
    if as_json or not sys.stdin.isatty():
        console.print(f"[red]Error:[/red] not load-testing a {rule.name} site without "
                      f"permission. Pass --host-permission (or {PERMISSION_ENV}=1) if you "
                      "have it.")
        raise SystemExit(1)
    if not click.confirm(f"Do you have {rule.name}'s permission to load-test this site?",
                         default=False):
        raise SystemExit(0)
