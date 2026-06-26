"""Main CLI entry point for PreScale."""

import click

from prescale_cli import __version__
from prescale_cli.commands import audit, run


@click.group()
@click.version_option(version=__version__, prog_name="prescale")
def cli() -> None:
    """PreScale - launch-readiness load testing for developers.

    Point `prescale run` at a URL and it ramps traffic until something gives,
    then tells you in plain English what breaks first and at what load -
    before your users find out.

    \b
    Quick start:
        prescale run http://localhost:8000      # load test: what breaks first
        prescale audit https://myapp.com        # static scaling-hygiene check
    """


cli.add_command(run.run)
cli.add_command(audit.audit)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
