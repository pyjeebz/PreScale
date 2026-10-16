"""`prescale upload` - send a saved run to the hosted app (opt-in).

Also home to the `--upload` / `--header` options that `run` and `investigate`
share, and the post-run upload step they both call.
"""

from __future__ import annotations

import json

import click
from rich.console import Console

from prescale_cli.cloud import CloudError, parse_headers, require_credentials, upload_result
from prescale_cli.result import ResultError, latest_id, load_result

console = Console()
err_console = Console(stderr=True)


def _headers_callback(_ctx, _param, values: tuple[str, ...]) -> dict[str, str]:
    try:
        return parse_headers(values)
    except ValueError as exc:
        raise click.BadParameter(str(exc)) from None


header_option = click.option(
    "--header", "-H", "headers", multiple=True, callback=_headers_callback,
    help="Extra request header for the target, e.g. -H 'x-vercel-protection-bypass: …' "
         "(repeatable). Never saved or uploaded.")

upload_option = click.option(
    "--upload", "upload", is_flag=True,
    help="After the run, upload the saved Result to your PreScale dashboard.")


def upload_after_run(result: dict, *, as_json: bool) -> None:
    """Upload a finished run, reporting to stderr in --json mode so stdout stays
    machine-readable. Exits non-zero on failure; the run itself is already saved."""
    out = err_console if as_json else console
    try:
        response = upload_result(result, require_credentials())
    except CloudError as exc:
        err_console.print(f"[red]✗ upload failed:[/red] {exc}")
        err_console.print(f"[dim]The run is saved locally. Retry with "
                          f"[bold]prescale upload {result['id']}[/bold].[/dim]")
        raise SystemExit(1)
    _report_upload(response, out)


def _report_upload(response: dict, out: Console) -> None:
    target = response.get("target", {})
    verb = "Uploaded" if response.get("created", True) else "Already uploaded"
    out.print(f"[green]✓[/green] {verb} → [cyan]{response.get('url')}[/cyan]")
    if target.get("created"):
        out.print(f"  [dim]New target {target.get('hostname')} added. Verify you own it "
                  "to sign off its capacity.[/dim]")
    elif target.get("verified") is False:
        out.print(f"  [dim]{target.get('hostname')} isn't verified yet, so this run is "
                  "labeled unverified.[/dim]")


@click.command()
@click.argument("run_id", required=False)
@click.option("--dry-run", "dry_run", is_flag=True,
              help="Print exactly what would be sent, and send nothing.")
@click.option("--store", "store", type=click.Path(file_okay=False), default=None,
              help="Directory for saved runs (default: ./.prescale).")
def upload(run_id: str | None, dry_run: bool, store: str | None) -> None:
    """Upload a saved run (default: the latest) to your PreScale dashboard.

    The payload is the saved Result file, unchanged. Use --dry-run to see it.

    \b
    Examples:
        prescale upload                 # the latest run
        prescale upload 20261015T1200Z  # a specific run (id or unique prefix)
        prescale upload --dry-run       # show the exact payload, send nothing
    """
    if run_id is None:
        run_id = latest_id(store=store)
        if run_id is None:
            console.print("[dim]No saved runs yet. Try "
                          "[bold]prescale investigate <url>[/bold] first.[/dim]")
            raise SystemExit(1)

    try:
        result = load_result(run_id, store=store)
    except ResultError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(1)

    if dry_run:
        click.echo(json.dumps(result, indent=2))
        err_console.print(f"[dim]Dry run: this is the full payload for {result['id']}. "
                          "Nothing was sent.[/dim]")
        return

    try:
        response = upload_result(result, require_credentials())
    except CloudError as exc:
        console.print(f"[red]✗ upload failed:[/red] {exc}")
        raise SystemExit(1)
    _report_upload(response, console)
