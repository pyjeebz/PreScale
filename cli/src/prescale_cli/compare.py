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
        "mode": (result.get("config") or {}).get("mode") or "urls",
        "culprit_journey": v.get("culprit_journey"),
    }


def compare_results(old: dict, new: dict, *, threshold: float = _DEFAULT_THRESHOLD) -> dict:
    """Diff two Results by capacity. A regression is a >threshold drop in
    survives_users; it's 'confident' when the M1 bands don't overlap. A new run
    that held to its max below the old level is 'inconclusive', not a drop."""
    o, n = _facts(old), _facts(new)
    if o["mode"] != n["mode"]:
        # URL capacity and journey capacity measure different things: never a regression.
        return _not_comparable(o, n)
    d = _diff(o, n, threshold)
    cmp = {
        "old": o,
        "new": n,
        "survives_delta": n["survives_users"] - o["survives_users"],
        "survives_pct": round(d["pct"], 3),
        "peak_rps_pct": (round((n["peak_rps"] - o["peak_rps"]) / o["peak_rps"], 3)
                         if o["peak_rps"] else 0.0),
        "regressed": d["regressed"],
        "improved": d["improved"],
        "inconclusive": d["inconclusive"],
        "confident": d["confident"],
        "summary": (_summary(o, n, d["pct"], d["regressed"], d["improved"], d["inconclusive"])
                    + _journey_note(o, n)),
    }
    if o["mode"] == "journeys":
        cmp["journeys"] = compare_journeys(old, new, threshold=threshold)
        worse = [j for j in cmp["journeys"] if j.get("regressed")]
        if worse:
            # A drop in any one journey is a regression, even if it isn't the weakest.
            # Confidence only comes from drops: a confident overall gain says nothing
            # about whether a journey's drop is noise.
            cmp["regressed"] = True
            cmp["confident"] = ((d["confident"] and d["regressed"])
                                or any(j["confident"] for j in worse))
            if not d["regressed"]:
                cmp["improved"] = False
                cmp["summary"] = "Capacity regressed: " + "; ".join(
                    f"{j['name']} {j['old']} → {j['new']} users ({j['pct']:+.0%})"
                    for j in worse) + "."
                if d["improved"]:
                    cmp["summary"] += (f" (Overall: {o['survives_users']} → "
                                       f"{n['survives_users']} users, {d['pct']:+.0%}.)")
    return cmp


def _diff(o: dict, n: dict, threshold: float) -> dict:
    """The capacity change between two sets of facts (a run, or one journey)."""
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
    return {"pct": pct, "regressed": regressed, "improved": improved,
            "inconclusive": inconclusive, "confident": confident}


def _journey_facts(j: dict) -> dict:
    conf = j.get("confidence") or {}
    return {"survives_users": j["survives_users"], "survives_low": conf.get("survives_low"),
            "survives_high": conf.get("survives_high"), "onset_users": j["onset_users"],
            "max_tested": j.get("max_tested")}


def compare_journeys(old: dict, new: dict, *, threshold: float = _DEFAULT_THRESHOLD) -> list:
    """Per-journey capacity change, matched by name. A journey that is new, gone,
    or not load-tested on either side is listed with its status, never as a drop."""
    before = {j["name"]: j for j in old.get("journeys") or []}
    after = {j["name"]: j for j in new.get("journeys") or []}
    rows = []
    for name in [*before, *(n for n in after if n not in before)]:
        o, n = before.get(name), after.get(name)
        if o is None or n is None:
            rows.append({"name": name, "status": "new" if o is None else "removed",
                         "regressed": False, "confident": False})
            continue
        if o["status"] != "ok" or n["status"] != "ok":
            rows.append({"name": name, "status": f"{o['status']} → {n['status']}",
                         "regressed": False, "confident": False})
            continue
        d = _diff(_journey_facts(o), _journey_facts(n), threshold)
        step = (n.get("culprit_step") or {}).get("name")
        rows.append({"name": name, "status": "ok", "old": o["survives_users"],
                     "new": n["survives_users"], "pct": round(d["pct"], 3),
                     "old_held_all": o["onset_users"] is None,
                     "new_held_all": n["onset_users"] is None,
                     "regressed": d["regressed"], "improved": d["improved"],
                     "inconclusive": d["inconclusive"], "confident": d["confident"],
                     "breaks_at": step})
    return rows


def journey_users(row: dict, side: str) -> str:
    """A journey's capacity in a compare row: "~20", or "200+" if it held every level."""
    return f"{row[side]}+" if row.get(f"{side}_held_all") else f"~{row[side]}"


def journey_change(row: dict, *, markers: bool = False) -> str:
    """The change cell: the percentage, or "inconclusive" when the new run held
    everything it tested but was never pushed as far as the old one."""
    if row.get("inconclusive"):
        return "inconclusive"
    mark = ""
    if markers:
        mark = " 🔴" if row["regressed"] else (" 🟢" if row.get("improved") else "")
    return f"{row['pct']:+.0%}{mark}"


def _cell(text: str) -> str:
    """Text safe inside a markdown table cell (journey and step names come from YAML)."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _not_comparable(o: dict, n: dict) -> dict:
    kinds = {"urls": "tested URLs", "journeys": "replayed journeys"}
    return {
        "old": o, "new": n, "survives_delta": 0, "survives_pct": 0.0, "peak_rps_pct": 0.0,
        "regressed": False, "improved": False, "inconclusive": True, "confident": False,
        "summary": (f"Not comparable: the old run {kinds.get(o['mode'], o['mode'])}, the new "
                    f"run {kinds.get(n['mode'], n['mode'])}. Compare runs of the same kind."),
    }


def _journey_note(o: dict, n: dict) -> str:
    if o["culprit_journey"] and n["culprit_journey"] \
            and o["culprit_journey"] != n["culprit_journey"]:
        return (f" The journey that breaks first changed: {o['culprit_journey']} → "
                f"{n['culprit_journey']}.")
    return ""


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
    lines = [
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
    ]
    if cmp.get("journeys"):
        lines += ["", "| journey | old | new | change | breaks at |", "|---|---:|---:|---:|---|"]
        for j in cmp["journeys"]:
            name = _cell(j["name"])
            if j["status"] != "ok":
                lines.append(f"| {name} | | | {j['status']} | |")
                continue
            step = _cell(j.get("breaks_at") or "—")
            lines.append(f"| {name} | {journey_users(j, 'old')} | {journey_users(j, 'new')} | "
                         f"{journey_change(j, markers=True)} | {step} |")
    return "\n".join(lines)
