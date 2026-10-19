"""Capacity in requests per second, and what that means in real visitors.

A PreScale virtual user sends requests back to back; a real visitor pauses for
seconds between clicks. So "survives ~200 users" can be far more traffic than
200 people. To say what the number means, we report:

  * the throughput at capacity: requests per second at the highest stage the
    app survived (not the peak, which can come from a stage already failing);
  * a rough visitor equivalent: that rate times VISITOR_INTERVAL_S, i.e. how
    many real visitors making one request every 10 seconds produce the same
    load. An estimate, always labelled as one.

Mirrored in the dashboard (web/src/lib/throughput.ts); keep the two in step.
"""

from __future__ import annotations

VISITOR_INTERVAL_S = 10
VISITOR_NOTE = f"one request per visitor every {VISITOR_INTERVAL_S}s"


def capacity_rps(result: dict) -> float | None:
    """Requests per second at the highest stage at or below the survives level."""
    verdict = result.get("verdict") or {}
    survives = verdict.get("survives_users") or 0
    held = [s for s in result.get("stages") or [] if s.get("users", 0) <= survives and s.get("rps")]
    if held:
        return max(held, key=lambda stage: stage["users"])["rps"]
    return None


def visitors_for(rps: float) -> int:
    """Real visitors that would send `rps`, rounded to two significant figures."""
    raw = rps * VISITOR_INTERVAL_S
    if raw < 100:
        return int(round(raw))
    digits = len(str(int(raw))) - 2
    return int(round(raw, -digits))


def describe(result: dict) -> str | None:
    """'≈ 640 req/s, roughly 6,400 real visitors' for a Result, or None if unknown."""
    rps = capacity_rps(result)
    if not rps:
        return None
    return f"≈ {rps:,.0f} req/s, roughly {visitors_for(rps):,} real visitors"
