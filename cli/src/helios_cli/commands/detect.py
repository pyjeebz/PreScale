"""Anomaly detection commands for Helios CLI."""

import json
from datetime import datetime

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--deployment", "-d", required=True, help="Deployment name")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--lookback", "-l", default=1, help="Hours of data to analyze")
@click.option("--sensitivity", "-s", default="medium", 
              type=click.Choice(["low", "medium", "high"]),
              help="Detection sensitivity")
@click.pass_context
def detect(ctx: click.Context, deployment: str, namespace: str, lookback: int, sensitivity: str) -> None:
    """Detect anomalies in resource metrics.
    
    Analyzes recent metrics to identify unusual patterns that may indicate
    issues with your deployment.
    
    Examples:
        helios detect --deployment my-app
        helios detect -d my-app -n production --sensitivity high
    """
    endpoint = ctx.obj["endpoint"]
    api_key = ctx.obj["api_key"]
    output_format = ctx.obj["output"]
    
    with console.status("[bold blue]Analyzing metrics for anomalies..."):
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = httpx.post(
                f"{endpoint}/detect",
                json={
                    "deployment": deployment,
                    "namespace": namespace,
                    "lookback_hours": lookback,
                    "sensitivity": sensitivity,
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
        _display_anomalies(data, deployment, namespace)


def _display_anomalies(data: dict, deployment: str, namespace: str) -> None:
    """Display anomaly detection results."""
    console.print()
    
    anomalies = data.get("anomalies", [])
    status_color = "green" if len(anomalies) == 0 else "red" if len(anomalies) > 3 else "yellow"
    status_text = "No anomalies detected" if len(anomalies) == 0 else f"{len(anomalies)} anomalies detected"
    
    console.print(Panel(
        f"[bold]Anomaly Detection Results[/bold]\n"
        f"Deployment: [cyan]{deployment}[/cyan]\n"
        f"Namespace: [cyan]{namespace}[/cyan]\n"
        f"Status: [{status_color}]{status_text}[/{status_color}]",
        title="🔍 Helios Anomaly Detection",
        border_style=status_color,
    ))
    console.print()
    
    if anomalies:
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Time", style="dim")
        table.add_column("Metric")
        table.add_column("Severity", justify="center")
        table.add_column("Value", justify="right")
        table.add_column("Expected", justify="right")
        table.add_column("Description")
        
        for anomaly in anomalies:
            timestamp = anomaly.get("timestamp", "")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                    timestamp = dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass
            
            severity = anomaly.get("severity", "medium")
            severity_style = {
                "low": "yellow",
                "medium": "orange1",
                "high": "red",
                "critical": "bold red",
            }.get(severity, "white")
            
            table.add_row(
                timestamp,
                anomaly.get("metric", "unknown"),
                f"[{severity_style}]{severity.upper()}[/{severity_style}]",
                f"{anomaly.get('actual_value', 0):.2f}",
                f"{anomaly.get('expected_value', 0):.2f}",
                anomaly.get("description", ""),
            )
        
        console.print(table)
        
        # Show recommendations
        if "recommendations" in data:
            console.print()
            console.print("[bold]Recommendations:[/bold]")
            for rec in data["recommendations"]:
                console.print(f"  • {rec}")
    else:
        console.print("[green]✓ All metrics are within normal ranges[/green]")
    
    # Show health score
    if "health_score" in data:
        score = data["health_score"]
        score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"
        console.print()
        console.print(f"[bold]Health Score:[/bold] [{score_color}]{score:.0f}/100[/{score_color}]")
