"""Status command for Prescale CLI."""

import json

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Check Prescale service status.
    
    Displays the health and status of connected Prescale services.
    
    Example:
        prescale status
    """
    endpoint = ctx.obj["endpoint"]
    api_key = ctx.obj["api_key"]
    output_format = ctx.obj["output"]
    
    results = {}
    
    # Check inference service
    with console.status("[bold blue]Checking Prescale services..."):
        # Health check
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = httpx.get(
                f"{endpoint}/health",
                headers=headers,
                timeout=10.0,
            )
            results["inference"] = {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "response_time_ms": response.elapsed.total_seconds() * 1000,
                "details": response.json() if response.status_code == 200 else {},
            }
        except httpx.HTTPError as e:
            results["inference"] = {
                "status": "unreachable",
                "error": str(e),
            }
        
        # Get metrics endpoint
        try:
            response = httpx.get(
                f"{endpoint}/metrics",
                headers=headers,
                timeout=10.0,
            )
            results["metrics"] = {
                "status": "available" if response.status_code == 200 else "unavailable",
            }
        except httpx.HTTPError:
            results["metrics"] = {"status": "unavailable"}
    
    if output_format == "json":
        console.print(json.dumps(results, indent=2))
    elif output_format == "yaml":
        import yaml
        console.print(yaml.dump(results, default_flow_style=False))
    else:
        _display_status(results, endpoint)


def _display_status(results: dict, endpoint: str) -> None:
    """Display service status in a formatted view."""
    console.print()
    
    inference = results.get("inference", {})
    status = inference.get("status", "unknown")
    status_color = {
        "healthy": "green",
        "unhealthy": "yellow",
        "unreachable": "red",
    }.get(status, "white")
    status_emoji = {
        "healthy": "✓",
        "unhealthy": "⚠",
        "unreachable": "✗",
    }.get(status, "?")
    
    console.print(Panel(
        f"[bold]Prescale Service Status[/bold]\n"
        f"Endpoint: [cyan]{endpoint}[/cyan]",
        title="🌟 Prescale",
        border_style=status_color,
    ))
    console.print()
    
    # Services table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Service")
    table.add_column("Status", justify="center")
    table.add_column("Response Time", justify="right")
    table.add_column("Details")
    
    # Inference service
    response_time = inference.get("response_time_ms", 0)
    response_time_str = f"{response_time:.0f}ms" if response_time else "N/A"
    details = inference.get("details", {})
    version = details.get("version", "unknown")
    
    table.add_row(
        "Inference API",
        f"[{status_color}]{status_emoji} {status.upper()}[/{status_color}]",
        response_time_str,
        f"v{version}" if status == "healthy" else inference.get("error", ""),
    )
    
    # Metrics endpoint
    metrics = results.get("metrics", {})
    metrics_status = metrics.get("status", "unknown")
    metrics_color = "green" if metrics_status == "available" else "red"
    metrics_emoji = "✓" if metrics_status == "available" else "✗"
    
    table.add_row(
        "Metrics",
        f"[{metrics_color}]{metrics_emoji} {metrics_status.upper()}[/{metrics_color}]",
        "",
        "Prometheus format",
    )
    
    console.print(table)
    
    # Model information
    if status == "healthy" and "models" in inference.get("details", {}):
        console.print()
        console.print("[bold]Loaded Models:[/bold]")
        for model in inference["details"]["models"]:
            console.print(f"  • {model}")
    
    # Quick actions
    console.print()
    console.print("[bold]Quick Actions:[/bold]")
    console.print("  [dim]prescale predict cpu -d <deployment>[/dim]  - Get CPU predictions")
    console.print("  [dim]prescale detect -d <deployment>[/dim]       - Detect anomalies")
    console.print("  [dim]prescale recommend -d <deployment>[/dim]    - Get recommendations")
