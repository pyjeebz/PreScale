"""Capacity comparison between two saved Results — the basis for `prescale compare`
and regression gating in CI. Pure logic + operand resolution (no network)."""

from __future__ import annotations

from prescale_cli.result import list_results, load_result

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
        "onset_users": v["onset_users"],
        "commit": env.get("git_commit"),
        "branch": env.get("git_branch"),
        "created_at": result.get("created_at"),
        "target": result.get("target", {}).get("url"),
    }


def compare_results(old: dict, new: dict, *, threshold: float = _DEFAULT_THRESHOLD) -> dict:
    """Diff two Results by capacity. A regression is a >threshold drop in
    survives_users; it's 'confident' when the M1 bands don't overlap."""
    o, n = _facts(old), _facts(new)
    o_surv, n_surv = o["survives_users"], n["survives_users"]
    pct = (n_surv - o_surv) / o_surv if o_surv else 0.0
    regressed = pct <= -threshold
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
        "confident": confident,
        "summary": _summary(o, n, pct, regressed, improved),
    }


def _summary(o: dict, n: dict, pct: float, regressed: bool, improved: bool) -> str:
    arrow = f"{o['survives_users']} → {n['survives_users']}"
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
    ])
