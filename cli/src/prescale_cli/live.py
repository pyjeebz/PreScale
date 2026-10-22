"""Progress while `run`, `investigate` and `ci` ramp.

In a terminal, a live Load-ramp table (the same one `render.py` prints) fills in
stage by stage, so you watch latency and errors climb as the load rises. In CI
logs and pipes, where a table can't redraw, each finished stage prints one line,
so a minute-long ramp is never silent. `--json` prints nothing until the result.
"""

from __future__ import annotations

from rich.console import Console
from rich.live import Live
from rich.table import Table

from prescale_cli.loadtest import StageResult
from prescale_cli.render import _err, _ms, latency_bar


def _ramp_table(rows: list[tuple[int, StageResult | None]], latency_wall: float,
                caption: str | None = None) -> Table:
    """Build the Load-ramp table. A `None` stage is a level still in flight."""
    table = Table(show_header=True, header_style="bold magenta", title="Load ramp",
                  caption=caption, caption_style="dim")
    table.add_column("Users", justify="right")
    table.add_column("Req/s", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")
    table.add_column(f"vs {latency_wall:g}s wall", no_wrap=True)
    table.add_column("p99", justify="right")
    table.add_column("Errors", justify="right")
    for users, stage in rows:
        if stage is None:
            dim = "[dim]…[/dim]"
            table.add_row(str(users), dim, dim, dim, dim, dim, "[dim]running…[/dim]")
            continue
        p95 = stage.pct(0.95) * 1000
        crossed = stage.error_rate >= 0.02 or p95 >= latency_wall * 1000
        table.add_row(
            str(stage.users),
            f"{stage.rps:.0f}",
            _ms(stage.pct(0.5) * 1000),
            _ms(p95),
            latency_bar(p95, latency_wall, broke=crossed),
            _ms(stage.pct(0.99) * 1000),
            _err(stage.error_rate),
            style="bold red" if crossed else None,
        )
    return table


class LiveRamp:
    """Context manager wiring a live ramp table to the loadtest callbacks:
    pass `.starting` as `progress_cb` and `.finished` as `on_stage`."""

    def __init__(self, console: Console, *, latency_wall: float = 2.0) -> None:
        self.latency_wall = latency_wall
        self._order: list[int] = []
        self._stage: dict[int, StageResult | None] = {}
        self._caption: str | None = "warming up…"
        self._live = Live(self._render(), console=console,
                          refresh_per_second=12, transient=False)

    def _render(self) -> Table:
        return _ramp_table([(u, self._stage.get(u)) for u in self._order],
                           self.latency_wall, self._caption)

    def starting(self, users: int) -> None:
        if users not in self._stage:
            self._order.append(users)
        self._stage[users] = None
        self._caption = None  # rows now show the activity
        self._live.update(self._render())

    def finished(self, stage: StageResult) -> None:
        if stage.users not in self._stage:
            self._order.append(stage.users)
        self._stage[stage.users] = stage
        self._live.update(self._render())

    def diagnosing(self) -> None:
        """Ramp is done; the probes are running — label the pause."""
        self._caption = "diagnosing the culprit route…"
        self._live.update(self._render())

    def __enter__(self) -> LiveRamp:
        self._live.__enter__()
        return self

    def __exit__(self, *exc: object) -> None:
        self._live.__exit__(*exc)


class PlainRamp:
    """One line per finished stage, for CI logs and pipes."""

    def __init__(self, console: Console, *, latency_wall: float = 2.0) -> None:
        self.console = console
        self.latency_wall = latency_wall

    def starting(self, users: int) -> None:
        pass

    def finished(self, stage: StageResult) -> None:
        p95 = stage.pct(0.95) * 1000
        crossed = stage.error_rate >= 0.02 or p95 >= self.latency_wall * 1000
        line = (f"  {stage.users:>4} users · {stage.rps:,.0f} req/s · p95 {_ms(p95)} · "
                f"{stage.error_rate:.0%} errors")
        self.console.print(f"[red]{line}[/red]" if crossed else line, highlight=False)

    def diagnosing(self) -> None:
        self.console.print("  diagnosing the culprit route…", highlight=False)

    def __enter__(self) -> PlainRamp:
        self.console.print("[dim]Ramping load…[/dim]")
        return self

    def __exit__(self, *exc: object) -> None:
        pass


class QuietRamp:
    """No progress: `--json` keeps stdout for the result alone."""

    def starting(self, users: int) -> None:
        pass

    def finished(self, stage: StageResult) -> None:
        pass

    def diagnosing(self) -> None:
        pass

    def __enter__(self) -> QuietRamp:
        return self

    def __exit__(self, *exc: object) -> None:
        pass


def ramp_progress(console: Console, *, latency_wall: float = 2.0, as_json: bool = False):
    """The progress display for this output: live table, plain lines, or nothing."""
    if as_json:
        return QuietRamp()
    if console.is_terminal:
        return LiveRamp(console, latency_wall=latency_wall)
    return PlainRamp(console, latency_wall=latency_wall)
