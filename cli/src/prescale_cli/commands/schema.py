"""`prescale schema` - print the JSON Schema for the saved-run (Result) format."""

from __future__ import annotations

import click

from prescale_cli.result import schema_json


@click.command()
def schema() -> None:
    """Print the JSON Schema for a saved run (the Result envelope).

    Pipe it to a validator, or commit it alongside tooling that consumes
    `prescale run --json` / `.prescale/runs/*.json`.
    """
    click.echo(schema_json())
