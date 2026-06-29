"""Thin FastMCP wiring for `prescale mcp`. Imports the optional `mcp` package;
all real logic lives in `mcp_tools.py` (which has no `mcp` dependency).

Tool docstrings are the agent-facing contract — keep them clear and concise.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from prescale_cli import mcp_tools
from prescale_cli.result import schema_json


def build_server(allow: set[str]) -> FastMCP:
    server = FastMCP("prescale")

    @server.tool()
    async def load_test(url: str, max_users: int = 100, paths: list[str] | None = None,
                        stage_seconds: float = 3.0, max_rps: float | None = None) -> dict:
        """Load-test a URL and return a plain-English readiness verdict — what breaks
        first and at what concurrency. Point it at the app's local or preview URL.
        Returns a compact summary (verdict, survives band, culprit route, run id);
        call get_run(id) for the full breakdown. Only local hosts are allowed unless
        the host was allowlisted when this server was started."""
        return await mcp_tools.run_summary(
            url, allow=allow, max_users=max_users, paths=tuple(paths or ()),
            stage_seconds=stage_seconds, max_rps=max_rps)

    @server.tool()
    async def audit(url: str) -> dict:
        """Fast, load-free scaling-hygiene check for a URL: compression, static-asset
        caching, CDN/edge, HTTP version, cookies on assets. Returns pass/warn/fail
        findings with fixes."""
        return await mcp_tools.audit_summary(url)

    @server.tool()
    async def list_runs() -> list[dict]:
        """List saved PreScale runs (newest first) with their verdict one-liners."""
        return mcp_tools.list_runs()

    @server.tool()
    async def get_run(run_id: str) -> dict:
        """Fetch the full saved Result for a run id — the complete per-level and
        per-route breakdown behind a load_test summary."""
        return mcp_tools.get_run(run_id)

    @server.resource("prescale://schema")
    def result_schema() -> str:
        """JSON Schema for a saved PreScale run (Result)."""
        return schema_json()

    return server


def serve(allow: set[str] | None = None) -> None:
    """Run the stdio MCP server (blocks)."""
    build_server(allow or set()).run()
