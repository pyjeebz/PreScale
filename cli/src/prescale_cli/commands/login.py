"""`prescale login` / `prescale logout` - connect the CLI to your dashboard."""

from __future__ import annotations

import os
import platform
import socket
import time
import webbrowser

import click
from rich.console import Console

from prescale_cli.cloud import (
    DEFAULT_URL,
    TOKEN_PREFIX,
    CloudError,
    Credentials,
    clear_credentials,
    normalize_url,
    poll_device_login,
    save_credentials,
    start_device_login,
    whoami,
)

console = Console()


def _device_name() -> str:
    return (socket.gethostname().split(".")[0] or "this machine")[:60]


def _platform() -> str:
    system = platform.system()
    if system == "Darwin":
        version = platform.mac_ver()[0]
        return f"macOS {version}".strip()
    return f"{system} {platform.release()}".strip()


def _should_open_browser(no_browser: bool) -> bool:
    # Over SSH the browser would open on the remote machine, not in front of you.
    return not no_browser and not os.environ.get("SSH_CONNECTION")


def _finish(url: str, token: str, user: dict) -> None:
    path = save_credentials(url, token)
    who = f"@{user['login']}" if user.get("login") else user.get("name") or "your account"
    console.print(f"[green]✓[/green] Logged in to [cyan]{url}[/cyan] as [bold]{who}[/bold]")
    console.print(f"  [dim]Token saved to {path} (readable only by you).[/dim]")
    console.print("  [dim]Upload a run with [bold]--upload[/bold], e.g. "
                  "prescale investigate https://staging.myapp.com --upload[/dim]")


def _login_with_token(url: str, token: str) -> None:
    if not token.startswith(TOKEN_PREFIX):
        console.print(f"[red]Error:[/red] PreScale tokens start with "
                      f"[bold]{TOKEN_PREFIX}[/bold].")
        raise SystemExit(1)
    try:
        identity = whoami(Credentials(url=url, token=token, source="login"))
    except CloudError as exc:
        console.print(f"[red]✗ login failed:[/red] {exc}")
        raise SystemExit(1)
    _finish(url, token, identity.get("user", {}))


def _login_in_browser(url: str, no_browser: bool) -> None:
    try:
        login = start_device_login(url, _device_name(), _platform())
    except CloudError as exc:
        console.print(f"[red]✗ login failed:[/red] {exc}")
        raise SystemExit(1)

    console.print(f"Your login code: [bold cyan]{login.user_code}[/bold cyan]")
    opened = _should_open_browser(no_browser) and webbrowser.open(login.verification_url_complete)
    if opened:
        console.print(f"  Opened [cyan]{login.verification_url_complete}[/cyan] in your browser.")
    else:
        console.print(f"  Open [cyan]{login.verification_url_complete}[/cyan] in a browser.")
    console.print("  [dim]Check the code matches, then approve. Ctrl+C to cancel.[/dim]")

    deadline = time.monotonic() + login.expires_in
    interval = login.interval
    try:
        with console.status("Waiting for approval in the browser…"):
            while time.monotonic() < deadline:
                time.sleep(interval)
                status, data = poll_device_login(url, login.device_code)
                if status == "approved":
                    break
                if status == "authorization_pending":
                    continue
                if status == "slow_down":
                    interval += 5  # RFC 8628: back off and keep polling.
                    continue
                message = {"access_denied": "Cancelled in the browser. Nothing was connected."}
                console.print(f"[red]✗ login failed:[/red] "
                              f"{message.get(status) or data.get('message') or status}")
                raise SystemExit(1)
            else:
                console.print("[red]✗ login failed:[/red] The code expired before it was "
                              "approved. Run prescale login again.")
                raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("[dim]Cancelled.[/dim]")
        raise SystemExit(130)
    except CloudError as exc:
        console.print(f"[red]✗ login failed:[/red] {exc}")
        raise SystemExit(1)

    _finish(url, data["token"], data.get("user") or {})


@click.command()
@click.option("--token", "token", default=None,
              help="Log in with an existing API token (for CI and scripts).")
@click.option("--paste", is_flag=True,
              help="Paste a token from Connect instead of approving in the browser.")
@click.option("--no-browser", is_flag=True,
              help="Print the approval link instead of opening a browser.")
@click.option("--url", "url", default=DEFAULT_URL, show_default=True,
              help="PreScale app URL.")
def login(token: str | None, paste: bool, no_browser: bool, url: str) -> None:
    """Connect this machine to your PreScale dashboard.

    Opens your browser to approve this machine; the CLI is signed in as soon
    as you click Approve. Nothing is uploaded until you pass --upload or run
    `prescale upload`.
    """
    url = normalize_url(url)
    if token is not None:
        _login_with_token(url, token)
    elif paste:
        console.print(f"Create a token at [cyan]{url}/connect[/cyan], then paste it below.")
        _login_with_token(url, click.prompt("Token", hide_input=True).strip())
    else:
        _login_in_browser(url, no_browser)


@click.command()
def logout() -> None:
    """Forget the saved token on this machine."""
    if clear_credentials():
        console.print("[green]✓[/green] Logged out. Revoke the token in the dashboard "
                      "if it might have leaked.")
    else:
        console.print("[dim]Not logged in.[/dim]")
