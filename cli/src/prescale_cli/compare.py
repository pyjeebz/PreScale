"""Capacity comparison between two saved Results — the basis for `prescale compare`
and regression gating in CI. Pure logic + operand resolution (no network)."""

from __future__ import annotations

from prescale_cli.bars import bar_rows
from prescale_cli.result import list_results, load_result
from prescale_cli.throughput import capacity_rps

_DEFAULT_THRESHOLD = 0.2


def _facts(result: dict) -> dict:
    v = result["verdict"]
    conf = v.get("confidence") or {}
    env = result.get("environment") or {}
    return {
        "id": result.get("id"),
        "survives_users": v["survives_users"],
        "survives_low": conf.get("survives_low"),
        "survives_high": conf.get("survives_high"),
        "peak_rps": v["peak_rps"],
        "capacity_rps": capacity_rps(result),
        "onset_users": v["onset_users"],
        "max_tested": v.get("max_tested"),
        "commit": env.get("git_commit"),
        "branch": env.get("git_branch"),
        "created_at": result.get("created_at"),
        "target": result.get("target", {}).get("url"),
    }


def compare_results(old: dict, new: dict, *, threshold: float = _DEFAULT_THRESHOLD) -> dict:
    """Diff two Results by capacity. A regression is a >threshold drop in
    survives_users; it's 'confident' when the M1 bands don't overlap. A new run
    that held to its max below the old level is 'inconclusive', not a drop."""
    o, n = _facts(old), _facts(new)
    o_surv, n_surv = o["survives_users"], n["survives_users"]
    pct = (n_surv - o_surv) / o_surv if o_surv else 0.0
    inconclusive = (n["onset_users"] is None and n["max_tested"] is not None
                    and n["max_tested"] < o_surv * (1 - threshold))
    regressed = not inconclusive and pct <= -threshold
    improved = pct >= threshold
    confident = False
    if regressed and o["survives_low"] is not None and n["survives_high"] is not None:
        confident = n["survives_high"] < o["survives_low"]
    elif improved and o["survives_high"] is not None and n["survives_low"] is not None:
        confident = n["survives_low"] > o["survives_high"]
    return {
        "old": o,
        "new": n,
        "survives_delta": n_surv - o_surv,
        "survives_pct": round(pct, 3),
        "peak_rps_pct": (round((n["peak_rps"] - o["peak_rps"]) / o["peak_rps"], 3)
                         if o["peak_rps"] else 0.0),
        "regressed": regressed,
        "improved": improved,
        "inconclusive": inconclusive,
        "confident": confident,
        "summary": _summary(o, n, pct, regressed, improved, inconclusive),
    }


def _summary(o: dict, n: dict, pct: float, regressed: bool, improved: bool,
             inconclusive: bool = False) -> str:
    arrow = f"{o['survives_users']} → {n['survives_users']}"
    if inconclusive:
        return (f"Capacity inconclusive: held to all {n['max_tested']} users tested, below "
                f"the previous ~{o['survives_users']}. Re-run with a higher --max-users.")
    since = f" since {o['commit']}" if o.get("commit") else ""
    if regressed:
        return f"Capacity regressed: {arrow} users ({pct:+.0%}){since}."
    if improved:
        return f"Capacity improved: {arrow} users ({pct:+.0%})."
    return f"Capacity steady: {arrow} users ({pct:+.0%})."


def resolve(operand: str | None, *, store=None, exclude: str | None = None) -> dict | None:
    """Resolve an operand (run id, unique prefix, or .json path) to a Result.
    None → the most recent saved run (optionally excluding one id)."""
    if operand is not None:
        return load_result(operand, store=store)
    for r in list_results(store=store):
        if r["id"] != exclude:
            return load_result(r["id"], store=store)
    return None


def to_markdown(cmp: dict) -> str:
    o, n = cmp["old"], cmp["new"]
    if cmp["regressed"]:
        emoji = "🔴" if cmp["confident"] else "🟠"
    elif cmp["improved"]:
        emoji = "🟢"
    else:
        emoji = "⚪"
    return "\n".join([
        f"### {emoji} PreScale — {cmp['summary']}",
        "",
        "| | survives | peak req/s | commit |",
        "|---|---:|---:|---|",
        f"| old | {o['survives_users']} | {o['peak_rps']:.0f} | `{o['commit'] or '-'}` |",
        f"| new | {n['survives_users']} | {n['peak_rps']:.0f} | `{n['commit'] or '-'}` |",
        "",
        "```text",
        *bar_rows(
            [("old", o["survives_users"], f"~{o['survives_users']}"),
             ("new", n["survives_users"], f"~{n['survives_users']}")],
            max(o["survives_users"], n["survives_users"], 1) * 1.1,
        ),
        "```",
    ])
