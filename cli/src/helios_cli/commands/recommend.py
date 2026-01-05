"""Scaling recommendation commands for Helios CLI."""

import json

import click
import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


@click.command()
@click.option("--deployment", "-d", required=True, help="Deployment name")
@click.option("--namespace", "-n", default="default", help="Kubernetes namespace")
@click.option("--cost-optimize", is_flag=True, help="Prioritize cost optimization")
@click.option("--performance", is_flag=True, help="Prioritize performance")
@click.pass_context
def recommend(ctx: click.Context, deployment: str, namespace: str, cost_optimize: bool, performance: bool) -> None:
    """Get scaling recommendations for a deployment.
    
    Analyzes current resource usage and predicted demand to provide
    intelligent scaling recommendations.
    
    Examples:
        helios recommend --deployment my-app
        helios recommend -d my-app --cost-optimize
        helios recommend -d my-app --performance
    """
    endpoint = ctx.obj["endpoint"]
    api_key = ctx.obj["api_key"]
    output_format = ctx.obj["output"]
    
    # Determine optimization strategy
    strategy = "balanced"
    if cost_optimize:
        strategy = "cost"
    elif performance:
        strategy = "performance"
    
    with console.status("[bold blue]Generating scaling recommendations..."):
        try:
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            response = httpx.post(
                f"{endpoint}/recommend",
                json={
                    "deployment": deployment,
                    "namespace": namespace,
                    "strategy": strategy,
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
        _display_recommendations(data, deployment, namespace, strategy)


def _display_recommendations(data: dict, deployment: str, namespace: str, strategy: str) -> None:
    """Display scaling recommendations."""
    console.print()
    
    strategy_emoji = {
        "balanced": "⚖️",
        "cost": "💰",
        "performance": "🚀",
    }.get(strategy, "⚖️")
    
    console.print(Panel(
        f"[bold]Scaling Recommendations[/bold]\n"
        f"Deployment: [cyan]{deployment}[/cyan]\n"
        f"Namespace: [cyan]{namespace}[/cyan]\n"
        f"Strategy: {strategy_emoji} {strategy.capitalize()}",
        title="📊 Helios Recommendations",
        border_style="blue",
    ))
    console.print()
    
    # Current vs Recommended
    current = data.get("current", {})
    recommended = data.get("recommended", {})
    
    if current and recommended:
        table = Table(show_header=True, header_style="bold magenta", title="Resource Configuration")
        table.add_column("Resource", style="dim")
        table.add_column("Current", justify="right")
        table.add_column("Recommended", justify="right")
        table.add_column("Change", justify="center")
        
        # Replicas
        curr_replicas = current.get("replicas", 0)
        rec_replicas = recommended.get("replicas", 0)
        replica_change = rec_replicas - curr_replicas
        replica_style = "green" if replica_change > 0 else "red" if replica_change < 0 else "dim"
        replica_arrow = "↑" if replica_change > 0 else "↓" if replica_change < 0 else "→"
        table.add_row(
            "Replicas",
            str(curr_replicas),
            str(rec_replicas),
            f"[{replica_style}]{replica_arrow} {abs(replica_change)}[/{replica_style}]" if replica_change != 0 else "[dim]no change[/dim]",
        )
        
        # CPU Request
        curr_cpu = current.get("cpu_request", "N/A")
        rec_cpu = recommended.get("cpu_request", "N/A")
        table.add_row(
            "CPU Request",
            curr_cpu,
            f"[green]{rec_cpu}[/green]" if curr_cpu != rec_cpu else rec_cpu,
            "[yellow]→[/yellow]" if curr_cpu != rec_cpu else "[dim]no change[/dim]",
        )
        
        # Memory Request
        curr_mem = current.get("memory_request", "N/A")
        rec_mem = recommended.get("memory_request", "N/A")
        table.add_row(
            "Memory Request",
            curr_mem,
            f"[green]{rec_mem}[/green]" if curr_mem != rec_mem else rec_mem,
            "[yellow]→[/yellow]" if curr_mem != rec_mem else "[dim]no change[/dim]",
        )
        
        # CPU Limit
        curr_cpu_limit = current.get("cpu_limit", "N/A")
        rec_cpu_limit = recommended.get("cpu_limit", "N/A")
        table.add_row(
            "CPU Limit",
            curr_cpu_limit,
            f"[green]{rec_cpu_limit}[/green]" if curr_cpu_limit != rec_cpu_limit else rec_cpu_limit,
            "[yellow]→[/yellow]" if curr_cpu_limit != rec_cpu_limit else "[dim]no change[/dim]",
        )
        
        # Memory Limit
        curr_mem_limit = current.get("memory_limit", "N/A")
        rec_mem_limit = recommended.get("memory_limit", "N/A")
        table.add_row(
            "Memory Limit",
            curr_mem_limit,
            f"[green]{rec_mem_limit}[/green]" if curr_mem_limit != rec_mem_limit else rec_mem_limit,
            "[yellow]→[/yellow]" if curr_mem_limit != rec_mem_limit else "[dim]no change[/dim]",
        )
        
        console.print(table)
    
    # Cost impact
    if "cost_impact" in data:
        cost = data["cost_impact"]
        console.print()
        console.print("[bold]Cost Impact:[/bold]")
        
        monthly_savings = cost.get("monthly_savings", 0)
        if monthly_savings > 0:
            console.print(f"  💰 Estimated monthly savings: [green]${monthly_savings:.2f}[/green]")
        elif monthly_savings < 0:
            console.print(f"  💸 Estimated monthly increase: [red]${abs(monthly_savings):.2f}[/red]")
        else:
            console.print("  [dim]No cost change expected[/dim]")
    
    # Reasoning
    if "reasoning" in data:
        console.print()
        console.print("[bold]Analysis:[/bold]")
        for reason in data["reasoning"]:
            console.print(f"  • {reason}")
    
    # Action command
    if "apply_command" in data:
        console.print()
        console.print("[bold]To apply this recommendation:[/bold]")
        console.print(f"  [cyan]{data['apply_command']}[/cyan]")
    
    # Confidence
    if "confidence" in data:
        confidence = data["confidence"] * 100
        conf_color = "green" if confidence >= 80 else "yellow" if confidence >= 60 else "red"
        console.print()
        console.print(f"[bold]Confidence:[/bold] [{conf_color}]{confidence:.0f}%[/{conf_color}]")
