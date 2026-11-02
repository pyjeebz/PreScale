"""`prescale mcp` - run PreScale as an MCP server for coding agents."""

from __future__ import annotations

import importlib.util
import os

import click
from rich.console import Console

from prescale_cli.mcp_tools import parse_allow

# Diagnostics go to stderr — stdout is the MCP protocol stream.
err = Console(stderr=True)


@click.command()
@click.option("--allow", "allow_hosts", multiple=True,
              help="Permit load-testing this non-local host (repeatable). "
                   "Also reads PRESCALE_MCP_ALLOW.")
def mcp(allow_hosts: tuple[str, ...]) -> None:
    """Run PreScale as an MCP server (stdio) so a coding agent can load-test mid-build.

    Local hosts are allowed by default; non-local hosts require --allow or
    PRESCALE_MCP_ALLOW.

    \b
    Claude Code:  claude mcp add prescale -- prescale mcp
    """
    try:
        from prescale_cli.mcp_server import serve
    except ImportError as exc:
        if importlib.util.find_spec("mcp") is not None:
            # Installed, but a version we can't use (mcp 2.x renamed FastMCP).
            err.print("[red]Error:[/red] the installed mcp package isn't supported:")
            err.print(f"    {exc}", markup=False)
            err.print("Install a supported version with:")
            err.print("    pip install 'mcp>=1.0,<2'", markup=False)
            raise SystemExit(1)
        err.print("[red]Error:[/red] MCP support needs the optional extra. Install it with:")
        err.print("    pip install 'prescale[mcp]'", markup=False)
        raise SystemExit(1)

    allow = parse_allow(os.environ.get("PRESCALE_MCP_ALLOW"))
    allow.update(h.strip().lower() for h in allow_hosts if h.strip())
    serve(allow)
