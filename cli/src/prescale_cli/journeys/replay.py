"""Run a journey's steps against an app.

A step's path is relative to the URL the journey runs against: with
`http://host/app`, the path `/api/cart` is `http://host/app/api/cart`. Every
request, redirects included, must stay on that URL's scheme, host and port.

`check` replays a journey once, as a single user, to see whether it still works
against the app as it is now. A step that fails its expectation here, with no
load at all, means the journey is stale (the app changed), not that the app
broke under load. Each run gets its own client, so cookies and extracted values
never leak between users.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from prescale_cli.journeys.model import Journey, Step, TemplateError, fresh_uniques, render
from prescale_cli.loadtest import client_headers

_SNIPPET = 160


class OffOriginError(Exception):
    """A request that would leave the app the journey runs against."""


def step_url(base_url: str, path: str) -> str:
    """The step's URL: PATH appended to BASE_URL, refused if it leaves its origin.
    Appending (not urljoin) keeps a base path like /app and never lets a rendered
    path such as //other-host/x change the host."""
    if not path.startswith("/") or path.startswith(("//", "/\\")):
        raise OffOriginError(f"path {path!r} must start with a single /")
    url = base_url.rstrip("/") + path
    if _origin(httpx.URL(url)) != _origin(httpx.URL(base_url)):
        raise OffOriginError(f"{url} isn't on {base_url}")
    return url


def _origin(url: httpx.URL) -> tuple[str, str, int | None]:
    return url.scheme, url.host, url.port


@dataclass
class StepCheck:
    step: Step
    status: int | None = None
    latency: float = 0.0
    ok: bool = False
    problem: str | None = None   # why it failed, in plain words


@dataclass
class JourneyCheck:
    journey: Journey
    steps: list[StepCheck] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return len(self.steps) == len(self.journey.steps) and all(s.ok for s in self.steps)

    @property
    def failed(self) -> StepCheck | None:
        return next((s for s in self.steps if not s.ok), None)

    @property
    def stale(self) -> bool:
        """The app answered, but not the way the journey expects."""
        failed = self.failed
        return failed is not None and failed.status is not None


async def check(journey: Journey, base_url: str, *, timeout: float = 10.0,
                headers: dict[str, str] | None = None, env: dict[str, str] | None = None,
                transport: httpx.AsyncBaseTransport | None = None) -> JourneyCheck:
    """Replay JOURNEY once against BASE_URL and stop at the first step that fails."""
    env = dict(os.environ) if env is None else env
    result = JourneyCheck(journey)
    variables: dict[str, Any] = fresh_uniques()
    origin = _origin(httpx.URL(base_url))

    async def same_origin(request: httpx.Request) -> None:
        # Runs for redirect hops too, so an app can't bounce a write elsewhere.
        if _origin(request.url) != origin:
            raise OffOriginError(f"redirected to {request.url.host}, outside the app")

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                 headers=client_headers(headers), transport=transport,
                                 event_hooks={"request": [same_origin]}) as client:
        for step in journey.steps:
            outcome = await run_step(client, step, base_url, variables, env)
            result.steps.append(outcome)
            if not outcome.ok:
                break
    return result


async def run_step(client: httpx.AsyncClient, step: Step, base_url: str,
                   variables: dict[str, Any], env: dict[str, str]) -> StepCheck:
    """Send one step, judge it against `expect`, and pull its `extract` values
    into VARIABLES for the steps after it."""
    outcome = StepCheck(step)
    try:
        url = step_url(base_url, str(render(step.path, variables, env)))
        req_headers = {k: str(v) for k, v in render(step.headers, variables, env).items()}
        payload = render(step.json, variables, env) if step.json is not None else None
        body = render(step.body, variables, env) if step.body is not None else None
    except (TemplateError, OffOriginError) as exc:
        outcome.problem = str(exc)
        return outcome

    start = time.perf_counter()
    try:
        resp = await client.request(step.method, url, headers=req_headers, json=payload,
                                    content=body)
    except OffOriginError as exc:
        outcome.problem = str(exc)
        return outcome
    except httpx.TimeoutException:
        outcome.problem = "timed out"
        return outcome
    except httpx.HTTPError as exc:
        outcome.problem = f"couldn't reach the app ({exc.__class__.__name__})"
        return outcome
    outcome.latency = time.perf_counter() - start
    outcome.status = resp.status_code

    if not step.accepts(resp.status_code):
        wanted = (" or ".join(map(str, step.expect)) if step.expect else "a status below 400")
        outcome.problem = f"returned {resp.status_code}, expected {wanted}"
        snippet = resp.text.strip().replace("\n", " ")[:_SNIPPET]
        if snippet:
            outcome.problem += f": {snippet}"
        return outcome

    for name, source in step.extract.items():
        value = extract(resp, source)
        if value is None:
            outcome.problem = f"couldn't find {source} in the response to extract {name}"
            return outcome
        variables[name] = value
    outcome.ok = True
    return outcome


def extract(resp: httpx.Response, source: str) -> Any:
    """Read `body.a.b.0` (JSON) or `header.Name` from a response; None if missing."""
    kind, _, where = source.partition(".")
    if kind == "header":
        return resp.headers.get(where)
    try:
        value: Any = resp.json()
    except ValueError:
        return None
    for part in where.split("."):
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.isdigit() and int(part) < len(value):
            value = value[int(part)]
        else:
            return None
    return value
