"""Terminal rendering of a Result — shared by `run` and `show` so both print
identically from the same stored shape, with no need for raw per-request data."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def render_terminal(result: dict) -> None:
    """Print the load-ramp table and readiness verdict for a Result."""
    verdict = result["verdict"]
    stages = result["stages"]
    warning = result.get("warning")
    latency_wall = result.get("config", {}).get("latency_wall_s", 2.0)
    multi = len(result.get("target", {}).get("routes", [])) > 1
    onset_users = verdict["onset_users"]

    console.print()
    if warning:
        console.print(f"[yellow]⚠ {warning}[/yellow]\n")

    table = Table(show_header=True, header_style="bold magenta", title="Load ramp")
    table.add_column("Users", justify="right")
    table.add_column("Req/s", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("p99", justify="right")
    table.add_column("Errors", justify="right")

    for stage in stages:
        is_onset = stage["users"] == onset_users
        table.add_row(
            str(stage["users"]),
            f"{stage['rps']:.0f}",
            _ms(stage["p50_ms"]),
            _ms(stage["p95_ms"]),
            _ms(stage["p99_ms"]),
            _err(stage["error_rate"]),
            style="bold red" if is_onset else None,
        )
    console.print(table)
    console.print()

    if onset_users is None:
        emoji, color = "✅", "green"
        headline = (f"Held up through {verdict['max_tested']} concurrent "
                    f"{_u(verdict['max_tested'])} (the most we tested).")
    else:
        emoji, color = "⚠️", "yellow"
        if verdict["survives_users"] == 0:
            emoji, color = "🛑", "red"
        headline = (f"Survives ~{verdict['survives_users']}{_band(verdict)} concurrent "
                    f"{_u(verdict['survives_users'])}.")

    lines = [f"[bold]Scale readiness:[/bold] {emoji} {headline}"]
    if onset_users is not None:
        culprit = f"{verdict['culprit_route']}  " if (multi and verdict["culprit_route"]) else ""
        if verdict["onset_reason"] == "latency":
            lines.append(f"Latency wall  {culprit}p95 crosses "
                         f"{latency_wall:g}s at ~{onset_users} {_u(onset_users)}.")
        else:
            lines.append(f"First failure  {culprit}errors climb at "
                         f"~{onset_users} {_u(onset_users)}.")
    if verdict["saturated"]:
        lines.append(f"Throughput  plateaued ~{verdict['peak_rps']:.0f} req/s around "
                     f"{verdict['saturation_users']} {_u(verdict['saturation_users'])} "
                     "(capacity ceiling).")
    if verdict["bottleneck"]:
        lines.append(f"Likely cause  {verdict['bottleneck']}")
    if verdict["marginal"]:
        lines.append("Note  only wobbled at the very top — likely some headroom.")
    conf = verdict.get("confidence") or {}
    if onset_users is not None and conf.get("stable") is False:
        lines.append(f"Confidence  likely {conf['survives_low']}–{conf['survives_high']} "
                     f"users; treat ~{verdict['survives_users']} as a ballpark.")

    prof = result.get("profile")
    if prof:
        icon = "✅" if prof["would_survive"] else "🛑"
        verb = "likely holds" if prof["would_survive"] else "unlikely"
        outcome = (f"survive ~{verdict['survives_users']}" if prof["would_survive"]
                   else f"break at ~{verdict['survives_users']}")
        lines.append(f"Launch  {icon} {prof['label']}: {verb} "
                     f"(peaks ~{prof['peak_users']}, you {outcome}).")

    console.print(Panel("\n".join(lines), title="📈 Readiness report", border_style=color))

    if multi and stages:
        _render_routes(result)


def _render_routes(result: dict) -> None:
    verdict = result["verdict"]
    stages = result["stages"]
    decisive = next((s for s in stages if s["users"] == verdict["onset_users"]), stages[-1])
    table = Table(show_header=True, header_style="bold magenta",
                  title=f"Per route @ {decisive['users']} users")
    table.add_column("Route")
    table.add_column("Req/s", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("Errors", justify="right")

    ranked = sorted(decisive["routes"].items(),
                    key=lambda kv: (kv[1]["error_rate"], kv[1]["p95_ms"]), reverse=True)
    for label, stat in ranked:
        is_culprit = label == verdict["culprit_route"]
        shown = f"[bold red]{label}[/bold red]" if is_culprit else label
        table.add_row(
            shown,
            f"{stat['rps']:.0f}",
            _ms(stat["p95_ms"]),
            _err(stat["error_rate"]),
        )
    console.print()
    console.print(table)


def render_investigation(result: dict) -> None:
    """Print the Diagnosis panel for an investigated Result (no-op if absent)."""
    inv = result.get("investigation")
    if not inv:
        return
    color = {"high": "red", "medium": "yellow", "low": "blue"}.get(inv["confidence"], "yellow")
    lines = [
        f"[bold]Likely cause:[/bold] {inv['summary']}",
        f"Bottleneck  [bold]{inv['bottleneck_class']}[/bold] "
        f"([{color}]{inv['confidence']} confidence[/{color}])  ·  culprit {inv['culprit_route']}",
    ]
    if inv.get("evidence"):
        lines.append("")
        lines.append("[bold]Evidence[/bold]")
        lines += [f"  • {e}" for e in inv["evidence"]]
    if inv.get("remediation"):
        lines.append("")
        lines.append("[bold]Try this[/bold]")
        lines += [f"  → {r}" for r in inv["remediation"]]
    console.print()
    console.print(Panel("\n".join(lines), title="🔬 Diagnosis", border_style=color))


def _band(verdict: dict) -> str:
    conf = verdict.get("confidence") or {}
    lo, hi = conf.get("survives_low"), conf.get("survives_high")
    point = verdict["survives_users"]
    if lo is None or hi is None or (lo == point and hi == point):
        return ""
    return f" ({lo}–{hi})"


def _u(n: int) -> str:
    return "user" if n == 1 else "users"


def _err(rate: float) -> str:
    color = "red" if rate >= 0.02 else "yellow" if rate > 0 else "green"
    return f"[{color}]{rate:.0%}[/{color}]"


def _ms(ms: float) -> str:
    return "-" if ms <= 0 else f"{ms:.0f}ms"
