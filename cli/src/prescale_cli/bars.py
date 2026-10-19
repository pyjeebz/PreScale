"""PreScale's bar in text, for terminals and PR comments.

The brand's dot-matrix bar runs from sparse dots through a checkerboard into a
solid end, like load ramping up until something gives. In text that's three
block characters: ░ (sparse), ▒ (checkerboard), █ (the solid end, the measured
value). A ┆ marks a threshold such as the latency wall or a launch's peak.

    text_bar(150, 250, width=20, marker=200)  ->  "░░░░░░░▒▒▒██    ┆   "
"""

from __future__ import annotations

SPARSE = "░"
CHECKER = "▒"
SOLID = "█"
MARKER = "┆"  # dashed, so it never reads as a table border


def text_bar(value: float, scale: float, *, width: int = 20, marker: float | None = None,
             cap: int = 2, checker: int = 3) -> str:
    """A bar `value / scale` of `width` characters, always exactly `width` long.

    Anything above zero shows at least one solid cell, so a tiny value still
    reads as "measured" rather than "missing". Values past `scale` fill the bar.
    """
    if width <= 0:
        return ""
    fraction = 0.0 if scale <= 0 else min(max(value / scale, 0.0), 1.0)
    length = round(fraction * width)
    if value > 0 and length == 0:
        length = 1
    solid = min(cap, length)
    checks = min(checker, length - solid)
    cells = [SPARSE] * (length - solid - checks) + [CHECKER] * checks + [SOLID] * solid
    cells += [" "] * (width - length)
    if marker is not None and scale > 0:
        at = min(max(round(marker / scale * width), 0), width - 1)
        # The marker sits on empty track; a bar that has passed it keeps its cells.
        if cells[at] == " ":
            cells[at] = MARKER
    return "".join(cells)


def wall_scale(wall_ms: float, *values_ms: float) -> float:
    """A shared scale for latency bars: a little past the wall, or the worst value."""
    return max(wall_ms * 1.25, *values_ms) if values_ms else wall_ms * 1.25


def bar_rows(rows: list[tuple[str, float, str]], scale: float, *, width: int = 24,
             marker: float | None = None) -> list[str]:
    """Labelled bars on one scale, aligned for a monospace block (a PR comment's
    ```text fence, `compare --md`). Each row is (label, value, trailing text)."""
    pad = max((len(label) for label, _, _ in rows), default=0)
    return [
        f"{label.ljust(pad)}  {text_bar(value, scale, width=width, marker=marker)}  {tail}"
        .rstrip()
        for label, value, tail in rows
    ]


def route_rows(stage: dict, wall_s: float, *, limit: int = 6) -> list[str]:
    """A stage's routes as latency bars toward the wall, slowest first."""
    measured = [(name, stat) for name, stat in (stage.get("routes") or {}).items()
                if stat.get("total", 1)]
    routes = sorted(measured, key=lambda item: item[1]["p95_ms"], reverse=True)[:limit]
    wall_ms = wall_s * 1000
    scale = wall_scale(wall_ms)
    return bar_rows(
        [(name, stat["p95_ms"], _fmt_ms(stat["p95_ms"]).rjust(6)) for name, stat in routes],
        scale, width=20, marker=wall_ms,
    )


def _fmt_ms(ms: float) -> str:
    return f"{ms / 1000:.1f}s" if ms >= 1000 else f"{ms:.0f}ms"
