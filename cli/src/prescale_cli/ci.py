"""CI glue for `prescale ci`: read the GitHub Actions context, find the PR for
a deploy, and keep one capacity comment per PR (and target) up to date.

Pure helpers plus small GitHub REST calls with an injectable transport, so the
whole flow is testable without GitHub.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from prescale_cli.bars import bar_rows, route_rows
from prescale_cli.throughput import VISITOR_NOTE, capacity_rps, visitors_for

_SHA = re.compile(r"^[0-9a-f]{40}$")
_TIMEOUT = 15.0


@dataclass
class GitHubContext:
    repository: str | None = None
    api_url: str = "https://api.github.com"
    event_name: str | None = None
    sha: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    deployment_url: str | None = None
    deployment_state: str | None = None
    deployment_environment: str | None = None

    @property
    def short_sha(self) -> str | None:
        return self.sha[:7] if self.sha else None

    @property
    def is_production(self) -> bool:
        return "prod" in (self.deployment_environment or "").lower()


def github_context(env: dict[str, str] | None = None) -> GitHubContext:
    """What we can learn from the Actions environment and event payload.

    `deployment_status` events (Vercel, Netlify, …) carry the deploy URL and sha;
    `pull_request` events carry the PR and branch; `push` carries the branch.
    """
    env = dict(os.environ) if env is None else env
    ctx = GitHubContext(
        repository=env.get("GITHUB_REPOSITORY"),
        api_url=env.get("GITHUB_API_URL", "https://api.github.com"),
        event_name=env.get("GITHUB_EVENT_NAME"),
        sha=env.get("GITHUB_SHA"),
        branch=env.get("GITHUB_HEAD_REF") or None,
    )
    if not ctx.branch and env.get("GITHUB_REF", "").startswith("refs/heads/"):
        ctx.branch = env["GITHUB_REF"].removeprefix("refs/heads/")

    event: dict = {}
    if env.get("GITHUB_EVENT_PATH"):
        try:
            event = json.loads(Path(env["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            event = {}

    if ctx.event_name == "deployment_status":
        status = event.get("deployment_status") or {}
        deployment = event.get("deployment") or {}
        ctx.deployment_state = status.get("state")
        ctx.deployment_url = status.get("environment_url") or status.get("target_url")
        ctx.deployment_environment = deployment.get("environment")
        ctx.sha = deployment.get("sha") or ctx.sha
        ref = deployment.get("ref")
        # Some platforms put the branch in `ref`, others the sha.
        ctx.branch = ref if ref and not _SHA.match(ref) else None
    elif ctx.event_name in ("pull_request", "pull_request_target"):
        pr = event.get("pull_request") or {}
        ctx.pr_number = pr.get("number")
        ctx.sha = (pr.get("head") or {}).get("sha") or ctx.sha
        ctx.branch = (pr.get("head") or {}).get("ref") or ctx.branch

    return ctx


def _github(ctx: GitHubContext, token: str, transport=None) -> httpx.Client:
    return httpx.Client(
        base_url=ctx.api_url,
        timeout=_TIMEOUT,
        transport=transport,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "prescale-ci",
        },
    )


def find_pull_request(ctx: GitHubContext, token: str, *, transport=None) -> dict | None:
    """The open PR whose head is this commit (deployment events don't name it)."""
    if not (ctx.repository and ctx.sha):
        return None
    with _github(ctx, token, transport) as gh:
        response = gh.get(f"/repos/{ctx.repository}/commits/{ctx.sha}/pulls")
    if response.status_code != 200:
        return None
    pulls = [pr for pr in response.json() if pr.get("state") == "open"]
    exact = [pr for pr in pulls if (pr.get("head") or {}).get("sha") == ctx.sha]
    return (exact or pulls or [None])[0]


def comment_marker(target: str) -> str:
    return f"<!-- prescale:capacity:{target} -->"


def upsert_pr_comment(ctx: GitHubContext, token: str, pr_number: int, body: str,
                      marker: str, *, transport=None) -> str:
    """Edit our earlier comment on the PR if there is one, else post a new one.
    Returns "updated" or "created"."""
    with _github(ctx, token, transport) as gh:
        page = 1
        while page <= 10:
            response = gh.get(f"/repos/{ctx.repository}/issues/{pr_number}/comments",
                              params={"per_page": 100, "page": page})
            response.raise_for_status()
            comments = response.json()
            for comment in comments:
                if marker in (comment.get("body") or ""):
                    gh.patch(f"/repos/{ctx.repository}/issues/comments/{comment['id']}",
                             json={"body": body}).raise_for_status()
                    return "updated"
            if len(comments) < 100:
                break
            page += 1
        gh.post(f"/repos/{ctx.repository}/issues/{pr_number}/comments",
                json={"body": body}).raise_for_status()
        return "created"


# --- the comment --------------------------------------------------------------

_HEADLINE = {
    "regressed": ("🔴", "Capacity regressed"),
    "possible": ("🟠", "Possible capacity regression"),
    "improved": ("🟢", "Capacity improved"),
    "steady": ("⚪", "Capacity steady"),
    "inconclusive": ("⚪", "Capacity inconclusive"),
}


def _pct(pct: float) -> str:
    sign = "+" if pct > 0 else "−" if pct < 0 else "±"
    return f"{sign}{abs(round(pct * 100))}%"


def _onset(verdict: dict) -> str:
    users = verdict.get("onset_users")
    if users is None:
        return f"held to the {verdict.get('max_tested')} users tested"
    reason = verdict.get("onset_reason")
    if reason == "latency":
        return f"p95 crossed the latency wall at ~{users} users"
    return f"errors climbed at ~{users} users"


def render_host_skip(rule, *, target: str) -> str:
    """The PR comment when the deploy's host restricts load testing."""
    return "\n".join([
        comment_marker(target),
        "### ⏸️ PreScale skipped this deploy",
        "",
        f"{rule.rule} ([policy]({rule.link}))",
        "",
        f"PreScale doesn't load-test {rule.name} deploys unless you confirm you have "
        "permission. If you do, set `host-permission: true` in the PreScale action. "
        "Otherwise, test a staging copy on infrastructure you're allowed to load.",
    ])


def render_comment(result: dict, upload: dict, *, target: str, sha: str | None) -> str:
    """The PR comment: the change vs baseline, what breaks first, why, the fix."""
    verdict = result["verdict"]
    conf = verdict.get("confidence") or {}
    comparison = upload.get("comparison")
    target_info = upload.get("target") or {}
    baseline_branch = target_info.get("baselineBranch") or "main"
    tested_host = result["target"].get("host") or result["target"]["url"]
    commit = (result.get("environment") or {}).get("git_commit") or (sha[:7] if sha else None)
    replica = bool((result.get("config") or {}).get("replica"))
    subject = "this build" if replica else "this deploy"

    lines = [comment_marker(target)]
    band = f"{conf.get('survives_low')}–{conf.get('survives_high')}"
    rps = capacity_rps(result)
    survives = f"~{verdict['survives_users']} users ({band})"

    if comparison:
        emoji, title = _HEADLINE[comparison["kind"]]
        base = comparison["baseline"]
        lines.append(f"### {emoji} {title}: {base['survives']} → {verdict['survives_users']} "
                     f"users ({_pct(comparison['pct'])})")
        lines.append(f"`{tested_host}` vs `{comparison['against']}` · **{target}**")
        if rps:
            base_rps = base.get("capacityRps")
            was = (f" (was ≈ {base_rps:,.0f} req/s, roughly {visitors_for(base_rps):,})"
                   if base_rps else "")
            lines += ["", f"At capacity {subject} handles ≈ {rps:,.0f} req/s, roughly "
                          f"{visitors_for(rps):,} real visitors{was}. "
                          f"<sub>Visitors assume {VISITOR_NOTE}.</sub>"]
        lines += [
            "",
            "| | Survives | Band | Peak req/s | Commit |",
            "|---|---:|---|---:|---|",
            f"| baseline | ~{base['survives']} | {base['low']}–{base['high']} | "
            f"{round(base['peakRps'])} | `{base.get('commit') or '-'}` |",
            f"| {subject} | ~{verdict['survives_users']} | {conf.get('survives_low')}–"
            f"{conf.get('survives_high')} | {round(verdict['peak_rps'])} | `{commit or '-'}` |",
            "",
            # The same comparison in PreScale's bar: ░ sparse → ▒ → █ the measured capacity.
            "```text",
            *bar_rows(
                [(comparison["against"], base["survives"], f"~{base['survives']}"),
                 (subject, verdict["survives_users"],
                  f"~{verdict['survives_users']}  {_pct(comparison['pct'])}")],
                max(base["survives"], base.get("high") or 0, verdict["survives_users"], 1) * 1.1,
            ),
            "```",
        ]
        if comparison["kind"] == "inconclusive":
            lines += ["", f"This run held to all {verdict['max_tested']} users it tested, below "
                          f"the baseline's ~{base['survives']}, so it can't show a regression. "
                          "Raise `max-users` to compare."]
        if comparison["kind"] == "possible":
            lines += ["", "The confidence bands overlap, so this may be noise. Another run "
                          "will confirm or clear it."]
    else:
        lines.append(f"### ⚪ First capacity run: survives {survives}")
        lines.append(f"`{tested_host}` · **{target}**")
        if rps:
            lines += ["", f"That's ≈ {rps:,.0f} req/s, roughly {visitors_for(rps):,} real "
                          f"visitors. <sub>Visitors assume {VISITOR_NOTE}.</sub>"]
        lines += ["", f"No `{baseline_branch}` baseline yet. Later pushes to this PR compare "
                      f"with this run; once `{baseline_branch}` has a run, PRs compare with it."]

    investigation = result.get("investigation")
    lines.append("")
    if verdict.get("onset_users") is None:
        lines.append(f"**Held:** {_onset(verdict)} without crossing a failure threshold.")
    else:
        culprit = verdict.get("culprit_route")
        lines.append(f"**Breaks first:** `{culprit}` · {_onset(verdict)}" if culprit
                     else f"**Breaks first:** {_onset(verdict)}")
        if investigation:
            lines.append(f"**Why:** `{investigation['bottleneck_class']}` "
                         f"({investigation['confidence']} confidence) · {investigation['summary']}")
            if investigation.get("remediation"):
                lines += ["", "**Fix:**"] + [f"- {fix}" for fix in investigation["remediation"]]
        # The routes at the stage that broke, as bars toward the latency wall (│).
        stages = result.get("stages", [])
        stage = next((s for s in stages if s.get("users") == verdict["onset_users"]), None)
        wall = (result.get("config") or {}).get("latency_wall_s", 2.0)
        if stage and len(stage.get("routes") or {}) > 1:
            caption = f"p95 per route at {stage['users']} users · ┆ = the {wall:g}s latency wall"
            lines += ["", f"<sub>{caption}</sub>", "", "```text", *route_rows(stage, wall), "```"]

    links = [f"[Open the run]({upload['url']})"] if upload.get("url") else []
    if target_info.get("url"):
        links.append(f"[Capacity timeline]({target_info['url']})")
    if links:
        lines += ["", " · ".join(links)]

    notes = []
    if replica:
        notes.append("Measured on a build of this commit in CI, not on your host: absolute "
                     f"numbers are indicative, the change vs `{baseline_branch}` is the signal.")
    elif tested_host != target:
        notes.append("Measured on a preview deploy: absolute numbers are indicative, the "
                     f"change vs `{baseline_branch}` is the signal.")
    if target_info.get("verified") is False:
        notes.append(f"{target} isn't verified yet, so runs can't be signed off.")
    lines += ["", f"<sub>PreScale{' · ' + ' '.join(notes) if notes else ''}</sub>"]
    return "\n".join(lines) + "\n"
