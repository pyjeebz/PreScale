"""A ready-to-paste prompt for a coding agent, from an investigated Result.

Built from the Result's own fields (where it broke, at how many users, the
diagnosis, its evidence and fixes), so it says nothing the run didn't measure.
No model writes it. It never includes response bodies, headers sent, or secrets:
only what's already in the Result, with any credentials in the URL removed.
"""

from __future__ import annotations

import shlex
from urllib.parse import urlsplit, urlunsplit


def _safe_url(url: str) -> str:
    """URL without user:password@, query or fragment."""
    parts = urlsplit(url)
    host = parts.hostname or ""
    if ":" in host:  # IPv6
        host = f"[{host}]"
    if parts.port:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, "", ""))


def fix_prompt(result: dict) -> str | None:
    """The prompt, or None when there's no diagnosis to act on."""
    inv = result.get("investigation")
    if not inv:
        return None
    verdict = result["verdict"]
    url = _safe_url(result["target"]["url"])
    step = inv.get("culprit_step")
    journey = inv.get("culprit_journey")
    route = inv["culprit_route"]

    if step and journey:
        where = (f'journey "{journey}", step {step["index"]} "{step["name"]}" '
                 f"({step['route']})")
    else:
        where = route
    conf = verdict.get("confidence") or {}
    band = ""
    if conf.get("survives_low") is not None and conf.get("survives_high") is not None:
        band = f" (likely {conf['survives_low']}–{conf['survives_high']})"
    together = (result.get("combined") or {})
    if verdict.get("onset_users") is not None:
        when = (f"It survives ~{verdict['survives_users']} concurrent users{band}; "
                f"{verdict.get('onset_reason') or 'it fails'} at ~{verdict['onset_users']}.")
    elif together.get("onset_users") is not None:
        when = (f"Each journey held on its own, but together they survive "
                f"~{together['survives_users']} concurrent users in total.")
    else:
        when = "It degraded under load."

    lines = [
        f"PreScale load-tested {url} and found what breaks first under load.",
        "",
        f"Where: {where}",
        f"When: {when}",
        f"Likely cause ({inv['bottleneck_class']}, {inv['confidence']} confidence): "
        f"{inv['summary']}",
    ]
    if inv.get("evidence"):
        lines += ["", "Evidence:"] + [f"- {e}" for e in inv["evidence"]]
    if inv.get("remediation"):
        lines += ["", "Suggested fixes:"] + [f"- {r}" for r in inv["remediation"]]
    stack = inv.get("stack") or {}
    if stack:
        lines += ["", "Detected: " + ", ".join(f"{k} {v}" for k, v in stack.items())]

    rerun = f"prescale investigate {shlex.quote(url)}"
    if journey:
        rerun += f" --journey {shlex.quote(journey)}"
    lines += [
        "",
        f"Find the code that handles {route} (and what it depends on: database pool, "
        "workers, locks, upstream calls). Check it against the diagnosis above, make the "
        "smallest change that fixes the cause, and explain it. Don't change the test "
        f"setup to make the number look better. Then re-run `{rerun}` to confirm the "
        "capacity went up.",
    ]
    return "\n".join(lines)
