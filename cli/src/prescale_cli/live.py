"""Live-updating ramp table shown while `run` / `investigate` ramp, in a TTY.

Renders the same Load-ramp table as `render.py`, but fills it in stage-by-stage
so you watch latency and errors climb as the load rises — instead of a bare
spinner. Non-TTY and `--json` callers skip this entirely.
"""

from __future__ import annotations

from rich.console import Console
from rich.live import Live
from rich.table import Table

from prescale_cli.loadtest import StageResult
from prescale_cli.render import _err, _ms


def _ramp_table(rows: list[tuple[int, StageResult | None]], latency_wall: float,
                caption: str | None = None) -> Table:
    """Build the Load-ramp table. A `None` stage is a level still in flight."""
    table = Table(show_header=True, header_style="bold magenta", title="Load ramp",
                  caption=caption, caption_style="dim")
    table.add_column("Users", justify="right")
    table.add_column("Req/s", justify="right")
    table.add_column("p50", justify="right")
    table.add_column("p95", justify="right")
    table.add_column("p99", justify="right")
    table.add_column("Errors", justify="right")
    for users, stage in rows:
        if stage is None:
            dim = "[dim]…[/dim]"
            table.add_row(str(users), dim, dim, dim, dim, "[dim]running…[/dim]")
            continue
        p95 = stage.pct(0.95) * 1000
        crossed = stage.error_rate >= 0.02 or p95 >= latency_wall * 1000
        table.add_row(
            str(stage.users),
            f"{stage.rps:.0f}",
            _ms(stage.pct(0.5) * 1000),
            _ms(p95),
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
