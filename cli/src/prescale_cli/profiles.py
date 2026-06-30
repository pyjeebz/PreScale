"""Launch profiles — map a named real-world spike to a peak concurrency and a
think-time, so the verdict reads as "would survive a Product Hunt launch". Pure;
the numbers are relatable anchors, not promises.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Profile:
    name: str
    label: str
    peak_users: int
    think_time_s: float


PROFILES: dict[str, Profile] = {
    "steady-10k-dau": Profile("steady-10k-dau", "steady traffic (~10k daily users)", 25, 1.0),
    "product-hunt": Profile("product-hunt", "a Product Hunt #1 launch", 100, 0.5),
    "reddit": Profile("reddit", "a top Reddit post spike", 300, 0.3),
    "hn-frontpage": Profile("hn-frontpage", "a Hacker News front-page hug", 300, 0.3),
    "black-friday": Profile("black-friday", "sustained Black Friday load", 500, 0.5),
}


def lookup(name: str) -> Profile | None:
    return PROFILES.get(name.lower().strip()) if name else None


def scenario_block(profile: Profile, survives_users: int) -> dict:
    """The `profile` block attached to a Result: does the run clear the peak?"""
    return {
        "name": profile.name,
        "label": profile.label,
        "peak_users": profile.peak_users,
        "would_survive": survives_users >= profile.peak_users,
    }
