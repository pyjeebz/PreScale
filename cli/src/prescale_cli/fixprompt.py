"""A ready-to-paste prompt for a coding agent, from an investigated Result.

Built from the Result's own fields (where it broke, at how many users, the
diagnosis, its evidence and fixes), so it says nothing the run didn't measure.
No model writes it. It never includes response bodies, headers sent, or secrets:
only what's already in the Result, with any credentials in the URL removed.
"""

from __future__ import annotations

import re
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


# key=value in a query string: the value may be a token (e.g. a preview's
# protection bypass), so it never leaves in a prompt or a PR comment.
_QUERY_VALUE = re.compile(r"([?&][^\s=&?#]+)=[^\s&#)`'\"|<>]*")


def redact_query(text: str) -> str:
    """TEXT with every query-string value replaced by ***."""
    return _QUERY_VALUE.sub(r"\1=***", str(text))


def _server(value: str) -> str:
    """A Server header as a short product token: the app controls it, so it gets
    no room to carry instructions into an agent's prompt."""
    return re.sub(r"[^\w./()+ -]", "", value)[:60].strip()


def _when(result: dict) -> str:
    verdict = result["verdict"]
    config = result.get("config") or {}
    together = result.get("combined") or {}
    conf = verdict.get("confidence") or {}
    band = ""
    if conf.get("survives_low") is not None and conf.get("survives_high") is not None:
        band = f" (likely {conf['survives_low']}–{conf['survives_high']})"
    if verdict.get("onset_users") is not None:
        reason = {
            "errors": f"errors crossed {config.get('error_threshold', 0.02):.0%}",
            "latency": f"p95 latency crossed the {config.get('latency_wall_s', 2.0):g}s wall",
        }.get(verdict.get("onset_reason"), verdict.get("onset_reason") or "it failed")
        return (f"It survives ~{verdict['survives_users']} concurrent users{band}; "
                f"{reason} at ~{verdict['onset_users']}.")
    if together.get("onset_users") is not None:
        return (f"Each journey held on its own, but together they survive "
                f"~{together['survives_users']} concurrent users in total.")
    return "It degraded under load."


def _rerun(result: dict, url: str) -> str:
    """The command that reproduces this run's diagnosis."""
    inv = result["investigation"]
    verdict = result["verdict"]
    together = result.get("combined") or {}
    cmd = f"prescale investigate {shlex.quote(url)}"
    if (result.get("config") or {}).get("mode") == "journeys" or inv.get("culprit_journey"):
        if verdict.get("onset_users") is None and together.get("onset_users") is not None:
            # It broke only with the journeys together: rerun all of them.
            names = together.get("journeys") or []
        else:
            names = [inv["culprit_journey"]] if inv.get("culprit_journey") else []
        return cmd + "".join(f" --journey {shlex.quote(n)}" for n in names)
    cmd += " --urls"
    route = urlsplit(inv["culprit_route"]).path
    if route and route != "/":
        cmd += f" --path {shlex.quote(route)}"
    return cmd


def fix_prompt(result: dict) -> str | None:
    """The prompt, or None when there's no diagnosis to act on."""
    inv = result.get("investigation")
    if not inv:
        return None
    url = _safe_url(result["target"]["url"])
    step = inv.get("culprit_step")
    journey = inv.get("culprit_journey")
    route = redact_query(inv["culprit_route"])

    if step and journey:
        where = (f'journey "{journey}", step {step["index"]} "{step["name"]}" '
                 f"({redact_query(step['route'])})")
    else:
        where = route

    lines = [
        f"PreScale load-tested {url} and found what breaks first under load.",
        "",
        f"Where: {where}",
        f"When: {_when(result)}",
        f"Likely cause ({inv['bottleneck_class']}, {inv['confidence']} confidence): "
        f"{inv['summary']}",
    ]
    evidence = [(f"server: {_server(e[8:])}" if e.startswith("server: ") else redact_query(e))
                for e in inv.get("evidence") or []]
    if evidence:
        lines += ["", "Evidence:"] + [f"- {e}" for e in evidence]
    if inv.get("remediation"):
        lines += ["", "Suggested fixes:"] + [f"- {r}" for r in inv["remediation"]]
    stack = {k: _server(v) for k, v in (inv.get("stack") or {}).items()}
    if stack:
        lines += ["", "Detected: " + ", ".join(f"{k} {v}" for k, v in stack.items())]

    lines += [
        "",
        f"Find the code that handles {route} (and what it depends on: database pool, "
        "workers, locks, upstream calls). Check it against the diagnosis above, make the "
        "smallest change that fixes the cause, and explain it. Don't change the test "
        f"setup to make the number look better. Then re-run `{_rerun(result, url)}` to "
        "confirm the capacity went up.",
    ]
    return "\n".join(lines)
