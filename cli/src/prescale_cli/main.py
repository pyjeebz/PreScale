"""Main CLI entry point for PreScale."""

import click

from prescale_cli import __version__
from prescale_cli.commands import audit, history, investigate, mcp, run, schema, show


@click.group()
@click.version_option(version=__version__, prog_name="prescale")
def cli() -> None:
    """PreScale - launch-readiness load testing for developers.

    Point `prescale run` at a URL and it ramps traffic until something gives,
    then tells you in plain English what breaks first and at what load -
    before your users find out.

    \b
    Quick start:
        prescale run http://localhost:8000          # load test: what breaks first
        prescale investigate http://localhost:8000  # ...and why, plus how to fix it
        prescale audit https://myapp.com            # static scaling-hygiene check
        prescale history                            # list saved runs
        prescale show                               # re-render the latest saved run
        prescale mcp                                # MCP server for coding agents
    """


cli.add_command(run.run)
cli.add_command(investigate.investigate)
cli.add_command(audit.audit)
cli.add_command(history.history)
cli.add_command(show.show)
cli.add_command(schema.schema)
cli.add_command(mcp.mcp)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
