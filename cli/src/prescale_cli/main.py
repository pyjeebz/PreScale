"""Main CLI entry point for Prescale."""

import click
from rich.console import Console

from prescale_cli import __version__
from prescale_cli.commands import predict, detect, recommend, status, config, agent

console = Console()


@click.group()
@click.version_option(version=__version__, prog_name="prescale")
@click.option(
    "--endpoint",
    "-e",
    envvar="PRESCALE_ENDPOINT",
    default="http://104.155.137.61",
    help="Prescale API endpoint URL",
)
@click.option(
    "--api-key",
    envvar="PRESCALE_API_KEY",
    default=None,
    help="API key for authentication",
)
@click.option(
    "--output",
    "-o",
    type=click.Choice(["table", "json", "yaml"]),
    default="table",
    help="Output format",
)
@click.pass_context
def cli(ctx: click.Context, endpoint: str, api_key: str | None, output: str) -> None:
    """Prescale CLI - Predictive Infrastructure Intelligence Platform.
    
    ML-powered resource forecasting and anomaly detection for Kubernetes.
    
    \b
    Quick Commands (all have sensible defaults):
        prescale status                    # Check service health
        prescale detect                    # Detect anomalies
        prescale recommend                 # Get scaling recommendations
        prescale predict cpu               # CPU predictions (needs models)
    
    \b
    Examples with options:
        prescale detect -d my-app -n prod --sensitivity high
        prescale recommend -d my-app --cost-optimize
        prescale predict cpu -d my-app -p 24
    """
    ctx.ensure_object(dict)
    ctx.obj["endpoint"] = endpoint
    ctx.obj["api_key"] = api_key
    ctx.obj["output"] = output


# Register commands
cli.add_command(predict.predict)
cli.add_command(detect.detect)
cli.add_command(recommend.recommend)
cli.add_command(status.status)
cli.add_command(config.config)
cli.add_command(agent.agent)


def main() -> None:
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
