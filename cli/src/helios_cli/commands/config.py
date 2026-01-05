"""Configuration commands for Helios CLI."""

import json
import os
from pathlib import Path

import click
import yaml
from rich.console import Console
from rich.table import Table

console = Console()

CONFIG_DIR = Path.home() / ".helios"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


@click.group()
def config() -> None:
    """Manage Helios CLI configuration.
    
    Configure endpoints, credentials, and preferences for the Helios CLI.
    """
    pass


@config.command()
@click.pass_context
def show(ctx: click.Context) -> None:
    """Show current configuration.
    
    Displays all configured settings including endpoint and preferences.
    """
    output_format = ctx.obj.get("output", "table")
    
    config_data = _load_config()
    
    # Add runtime config
    config_data["runtime"] = {
        "endpoint": ctx.obj.get("endpoint", "http://localhost:8000"),
        "api_key_set": bool(ctx.obj.get("api_key")),
    }
    
    if output_format == "json":
        # Mask API key
        if "api_key" in config_data:
            config_data["api_key"] = "***" if config_data["api_key"] else None
        console.print(json.dumps(config_data, indent=2))
    elif output_format == "yaml":
        if "api_key" in config_data:
            config_data["api_key"] = "***" if config_data["api_key"] else None
        console.print(yaml.dump(config_data, default_flow_style=False))
    else:
        _display_config(config_data)


@config.command()
@click.argument("key")
@click.argument("value")
def set(key: str, value: str) -> None:
    """Set a configuration value.
    
    Available keys:
    
    \b
      endpoint    - Helios API endpoint URL
      api_key     - API key for authentication
      output      - Default output format (table, json, yaml)
    
    Examples:
    
    \b
      helios config set endpoint http://helios.example.com:8000
      helios config set output json
    """
    valid_keys = ["endpoint", "api_key", "output"]
    
    if key not in valid_keys:
        console.print(f"[red]Error:[/red] Invalid key '{key}'. Valid keys: {', '.join(valid_keys)}")
        raise SystemExit(1)
    
    if key == "output" and value not in ["table", "json", "yaml"]:
        console.print(f"[red]Error:[/red] Invalid output format. Must be: table, json, or yaml")
        raise SystemExit(1)
    
    config_data = _load_config()
    config_data[key] = value
    _save_config(config_data)
    
    display_value = "***" if key == "api_key" else value
    console.print(f"[green]✓[/green] Set {key} = {display_value}")


@config.command()
@click.argument("key")
def unset(key: str) -> None:
    """Remove a configuration value.
    
    Example:
        helios config unset api_key
    """
    config_data = _load_config()
    
    if key in config_data:
        del config_data[key]
        _save_config(config_data)
        console.print(f"[green]✓[/green] Removed {key}")
    else:
        console.print(f"[yellow]![/yellow] Key '{key}' not found in configuration")


@config.command()
def init() -> None:
    """Initialize configuration interactively.
    
    Guides you through setting up the Helios CLI configuration.
    """
    console.print("[bold]Helios CLI Configuration[/bold]")
    console.print()
    
    # Endpoint
    default_endpoint = "http://localhost:8000"
    endpoint = click.prompt(
        "Helios API endpoint",
        default=default_endpoint,
    )
    
    # API Key
    api_key = click.prompt(
        "API key (leave empty for none)",
        default="",
        hide_input=True,
        show_default=False,
    )
    
    # Output format
    output = click.prompt(
        "Default output format",
        type=click.Choice(["table", "json", "yaml"]),
        default="table",
    )
    
    config_data = {
        "endpoint": endpoint,
        "output": output,
    }
    
    if api_key:
        config_data["api_key"] = api_key
    
    _save_config(config_data)
    
    console.print()
    console.print(f"[green]✓[/green] Configuration saved to {CONFIG_FILE}")
    console.print()
    console.print("[bold]Test your connection:[/bold]")
    console.print("  helios status")


@config.command()
def path() -> None:
    """Show configuration file path."""
    console.print(f"Configuration file: {CONFIG_FILE}")
    console.print(f"Exists: {'Yes' if CONFIG_FILE.exists() else 'No'}")


def _load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return yaml.safe_load(f) or {}
    return {}


def _save_config(config_data: dict) -> None:
    """Save configuration to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)
    # Set restrictive permissions for API key security
    os.chmod(CONFIG_FILE, 0o600)


def _display_config(config_data: dict) -> None:
    """Display configuration in table format."""
    console.print()
    console.print(f"[bold]Configuration File:[/bold] {CONFIG_FILE}")
    console.print()
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting")
    table.add_column("Value")
    table.add_column("Source")
    
    # File config
    file_config = {k: v for k, v in config_data.items() if k != "runtime"}
    runtime = config_data.get("runtime", {})
    
    # Endpoint
    file_endpoint = file_config.get("endpoint", "")
    runtime_endpoint = runtime.get("endpoint", "http://localhost:8000")
    effective_endpoint = file_endpoint or runtime_endpoint
    source = "config file" if file_endpoint else "default/env"
    table.add_row("endpoint", effective_endpoint, source)
    
    # API Key
    api_key = file_config.get("api_key", "")
    api_key_display = "***" if api_key else "(not set)"
    api_key_source = "config file" if api_key else "env: HELIOS_API_KEY" if runtime.get("api_key_set") else "(not set)"
    table.add_row("api_key", api_key_display, api_key_source)
    
    # Output
    output = file_config.get("output", "table")
    table.add_row("output", output, "config file" if "output" in file_config else "default")
    
    console.print(table)
    
    console.print()
    console.print("[bold]Environment Variables:[/bold]")
    console.print("  HELIOS_ENDPOINT - Override API endpoint")
    console.print("  HELIOS_API_KEY  - API key for authentication")
