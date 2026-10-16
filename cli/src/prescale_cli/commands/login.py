"""`prescale login` / `prescale logout` - connect the CLI to your dashboard."""

from __future__ import annotations

import click
from rich.console import Console

from prescale_cli.cloud import (
    DEFAULT_URL,
    TOKEN_PREFIX,
    CloudError,
    Credentials,
    clear_credentials,
    normalize_url,
    save_credentials,
    whoami,
)

console = Console()


@click.command()
@click.option("--token", "token", default=None,
              help="API token (default: prompt, so it stays out of shell history).")
@click.option("--url", "url", default=DEFAULT_URL, show_default=True,
              help="PreScale app URL.")
def login(token: str | None, url: str) -> None:
    """Connect this machine to your PreScale dashboard.

    Create a token under Connect in the dashboard, then paste it here. Nothing
    is uploaded until you pass --upload or run `prescale upload`.
    """
    url = normalize_url(url)
    if token is None:
        console.print(f"Create a token at [cyan]{url}/connect[/cyan], then paste it below.")
        token = click.prompt("Token", hide_input=True).strip()

    if not token.startswith(TOKEN_PREFIX):
        console.print(f"[red]Error:[/red] PreScale tokens start with "
                      f"[bold]{TOKEN_PREFIX}[/bold].")
        raise SystemExit(1)

    try:
        identity = whoami(Credentials(url=url, token=token, source="login"))
    except CloudError as exc:
        console.print(f"[red]✗ login failed:[/red] {exc}")
        raise SystemExit(1)

    path = save_credentials(url, token)
    user = identity.get("user", {})
    who = f"@{user['login']}" if user.get("login") else user.get("name") or "your account"
    console.print(f"[green]✓[/green] Logged in to [cyan]{url}[/cyan] as [bold]{who}[/bold]")
    console.print(f"  [dim]Token saved to {path} (readable only by you).[/dim]")
    console.print("  [dim]Upload a run with [bold]--upload[/bold], e.g. "
                  "prescale investigate https://staging.myapp.com --upload[/dim]")


@click.command()
def logout() -> None:
    """Forget the saved token on this machine."""
    if clear_credentials():
        console.print("[green]✓[/green] Logged out. Revoke the token in the dashboard "
                      "if it might have leaked.")
    else:
        console.print("[dim]Not logged in.[/dim]")
