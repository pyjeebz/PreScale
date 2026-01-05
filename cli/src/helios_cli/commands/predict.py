"""Prediction commands for Helios CLI."""

import json
from datetime import datetime

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.group()
def predict() -> None:
    """Generate resource predictions.
    
    Use these commands to forecast CPU, memory, and other resource usage
    for your Kubernetes deployments.
    """
    pass


@predict.command()
@click.option("--deployment", "-d", required=True, help="Deployment name")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--horizon", "-h", default=24, help="Prediction horizon in hours")
@click.option("--interval", "-i", default="1h", help="Prediction interval (1h, 30m, etc.)")
@click.pass_context
def cpu(ctx: click.Context, deployment: str, namespace: str, horizon: int, interval: str) -> None:
    """Predict CPU usage for a deployment.
    
    Example:
        helios predict cpu --deployment my-app --horizon 24
    """
    endpoint = ctx.obj["endpoint"]
    api_key = ctx.obj["api_key"]
    output_format = ctx.obj["output"]
    
    with console.status("[bold blue]Fetching CPU predictions..."):
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = httpx.post(
                f"{endpoint}/predict",
                json={
                    "metric_type": "cpu",
                    "deployment": deployment,
                    "namespace": namespace,
                    "horizon_hours": horizon,
                    "interval": interval,
                },
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]Error:[/red] Failed to connect to Helios: {e}")
            raise SystemExit(1)
    
    if output_format == "json":
        console.print(json.dumps(data, indent=2))
    elif output_format == "yaml":
        import yaml
        console.print(yaml.dump(data, default_flow_style=False))
    else:
        _display_prediction_table(data, "CPU", deployment, namespace)


@predict.command()
@click.option("--deployment", "-d", required=True, help="Deployment name")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--horizon", "-h", default=24, help="Prediction horizon in hours")
@click.option("--interval", "-i", default="1h", help="Prediction interval (1h, 30m, etc.)")
@click.pass_context
def memory(ctx: click.Context, deployment: str, namespace: str, horizon: int, interval: str) -> None:
    """Predict memory usage for a deployment.
    
    Example:
        helios predict memory --deployment my-app --horizon 48
    """
    endpoint = ctx.obj["endpoint"]
    api_key = ctx.obj["api_key"]
    output_format = ctx.obj["output"]
    
    with console.status("[bold blue]Fetching memory predictions..."):
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = httpx.post(
                f"{endpoint}/predict",
                json={
                    "metric_type": "memory",
                    "deployment": deployment,
                    "namespace": namespace,
                    "horizon_hours": horizon,
                    "interval": interval,
                },
                headers=headers,
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as e:
            console.print(f"[red]Error:[/red] Failed to connect to Helios: {e}")
            raise SystemExit(1)
    
    if output_format == "json":
        console.print(json.dumps(data, indent=2))
    elif output_format == "yaml":
        import yaml
        console.print(yaml.dump(data, default_flow_style=False))
    else:
        _display_prediction_table(data, "Memory", deployment, namespace)


def _display_prediction_table(data: dict, metric_type: str, deployment: str, namespace: str) -> None:
    """Display prediction data in a formatted table."""
    console.print()
    console.print(Panel(
        f"[bold]{metric_type} Prediction[/bold]\n"
        f"Deployment: [cyan]{deployment}[/cyan]\n"
        f"Namespace: [cyan]{namespace}[/cyan]",
        title="🔮 Helios Prediction",
        border_style="blue",
    ))
    console.print()
    
    if "predictions" in data:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim")
        table.add_column("Predicted", justify="right")
        table.add_column("Lower Bound", justify="right", style="yellow")
        table.add_column("Upper Bound", justify="right", style="yellow")
        table.add_column("Confidence", justify="right")
        
        for pred in data["predictions"][:10]:  # Show first 10
            timestamp = pred.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            
            table.add_row(
                timestamp,
                f"{pred.get('value', 0):.2f}",
                f"{pred.get('lower_bound', 0):.2f}",
                f"{pred.get('upper_bound', 0):.2f}",
                f"{pred.get('confidence', 0) * 100:.1f}%",
            )
        
        console.print(table)
        
        if len(data["predictions"]) > 10:
            console.print(f"\n[dim]... and {len(data['predictions']) - 10} more predictions[/dim]")
    
    # Show summary statistics
    if "summary" in data:
        summary = data["summary"]
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Peak predicted: [red]{summary.get('peak', 0):.2f}[/red]")
        console.print(f"  Average: [blue]{summary.get('average', 0):.2f}[/blue]")
        console.print(f"  Trend: {summary.get('trend', 'stable')}")
