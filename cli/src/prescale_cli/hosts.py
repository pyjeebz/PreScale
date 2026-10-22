"""Hosts that restrict load testing, recognised from their response headers.

Some platforms only allow load tests by arrangement: Vercel permits them on
Enterprise plans with prior notice, Netlify needs its express permission, and
Cloudflare treats them as attacks unless arranged. PreScale checks the first
response before sending any load and won't continue against these hosts until
the user says they have permission (`--host-permission`, or
PRESCALE_HOST_PERMISSION=1 where nobody can be asked).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

PERMISSION_ENV = "PRESCALE_HOST_PERMISSION"


@dataclass(frozen=True)
class HostRule:
    name: str
    rule: str
    link: str


VERCEL = HostRule(
    "Vercel",
    "Vercel only permits load testing on Enterprise plans, with prior notice to Vercel.",
    "https://vercel.com/kb/guide/what-s-vercel-s-policy-regarding-load-testing-deployments",
)
NETLIFY = HostRule(
    "Netlify",
    "Netlify doesn't allow load testing without its express permission, arranged in advance.",
    "https://www.netlify.com/legal/acceptable-use-policy/",
)
CLOUDFLARE = HostRule(
    "Cloudflare",
    "Cloudflare treats load tests as attacks and blocks them unless you arrange the test "
    "with Cloudflare first.",
    "https://developers.cloudflare.com/fundamentals/reference/scans-penetration/",
)


def detect_host(headers) -> HostRule | None:
    """The restricting host serving this response, if any. A site behind several
    (Vercel behind Cloudflare, say) reports the platform closest to the app."""
    if headers is None:
        return None
    server = (headers.get("server") or "").strip().lower()
    if headers.get("x-vercel-id") or server == "vercel":
        return VERCEL
    if headers.get("x-nf-request-id") or server.startswith("netlify"):
        return NETLIFY
    if headers.get("cf-ray") or server == "cloudflare":
        return CLOUDFLARE
    return None


def permission_from_env() -> bool:
    return os.environ.get(PERMISSION_ENV, "").strip().lower() in {"1", "true", "yes"}


def refusal(rule: HostRule) -> str:
    """Why PreScale stopped, and what to do instead."""
    return (f"{rule.rule} ({rule.link}) PreScale won't send load until you confirm you have "
            f"{rule.name}'s permission (--host-permission, or {PERMISSION_ENV}=1). Without it, "
            "test your app locally, or on staging you're allowed to load.")
