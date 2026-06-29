"""`prescale mcp` - run PreScale as an MCP server for coding agents."""

from __future__ import annotations

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
    except ImportError:
        err.print("[red]Error:[/red] MCP support needs the optional extra:\n"
                  "    pip install 'prescale[mcp]'")
        raise SystemExit(1)

    allow = parse_allow(os.environ.get("PRESCALE_MCP_ALLOW"))
    allow.update(h.strip().lower() for h in allow_hosts if h.strip())
    serve(allow)
