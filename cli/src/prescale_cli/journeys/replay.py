"""Run a journey's steps against an app.

A step's path is relative to the URL the journey runs against: with
`http://host/app`, the path `/api/cart` is `http://host/app/api/cart`. Every
request, redirects included, must stay on that URL's scheme, host and port.

`check` replays a journey once, as a single user, to see whether it still works
against the app as it is now. A step that fails its expectation here, with no
load at all, means the journey is stale (the app changed), not that the app
broke under load. `journey_vu` is the same journey as a virtual user for a load
test: it walks the steps over and over until the stage ends.

Every run of a journey has its own cookies and extracted values, so a login or
a cart never leaks from one user to another, even on a shared client.
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from http.cookiejar import CookieJar, DefaultCookiePolicy
from typing import Any

import httpx

from prescale_cli.journeys.model import (
    SENSITIVE_KEY,
    Journey,
    Step,
    TemplateError,
    fresh_uniques,
    render,
)
from prescale_cli.loadtest import client_headers

_SNIPPET = 160
# Separates journey and step in labels when several journeys run together.
SEP = " › "
_MAX_REDIRECTS = 10


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


def client_options(base_url: str) -> dict:
    """Settings for any client that runs journeys: requests (redirect hops too)
    must stay on BASE_URL's origin, and the client itself keeps no cookies, since
    each run of a journey carries its own."""
    origin = _origin(httpx.URL(base_url))

    async def same_origin(request: httpx.Request) -> None:
        if _origin(request.url) != origin:
            raise OffOriginError(f"redirected to {request.url.host}, outside the app")

    return {
        "event_hooks": {"request": [same_origin]},
        "cookies": CookieJar(policy=DefaultCookiePolicy(allowed_domains=[])),
    }


@dataclass
class StepCheck:
    step: Step
    status: int | None = None
    latency: float = 0.0
    ok: bool = False
    problem: str | None = None   # why it failed, in plain words (no response body)
    kind: str | None = None      # a short failure kind for load reports
    # The start of the response body, secrets masked. Shown in a local terminal
    # only: never in CI output, a PR comment or an uploaded Result.
    snippet: str | None = None
    headers: httpx.Headers | None = None


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
    def outcome(self) -> str:
        """ok; stale (the app answered, but not as the journey expects, e.g. a
        404: the app changed); error (a 5xx with a single user: the app is
        broken); unreachable (no answer at all)."""
        failed = self.failed
        if failed is None and self.ok:
            return "ok"
        if failed is None or failed.status is None:
            return "unreachable"
        return "error" if failed.status >= 500 else "stale"

    @property
    def stale(self) -> bool:
        return self.outcome == "stale"


async def check(journey: Journey, base_url: str, *, timeout: float = 10.0,
                headers: dict[str, str] | None = None, env: dict[str, str] | None = None,
                transport: httpx.AsyncBaseTransport | None = None) -> JourneyCheck:
    """Replay JOURNEY once against BASE_URL and stop at the first step that fails."""
    env = dict(os.environ) if env is None else env
    result = JourneyCheck(journey)
    variables: dict[str, Any] = fresh_uniques()
    secrets = secret_values(journey, env)
    jar = httpx.Cookies()
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                 headers=client_headers(headers), transport=transport,
                                 **client_options(base_url)) as client:
        for step in journey.steps:
            outcome = await run_step(client, step, base_url, variables, env, jar, secrets)
            result.steps.append(outcome)
            if not outcome.ok:
                break
    return result


def apportion(users: int, weights: list[float]) -> list[int]:
    """Split USERS into whole numbers proportional to WEIGHTS (largest remainder),
    so the counts always add up to USERS."""
    total = sum(weights)
    exact = [users * w / total for w in weights]
    counts = [int(x) for x in exact]
    by_remainder = sorted(range(len(weights)), key=lambda i: exact[i] - counts[i], reverse=True)
    for i in by_remainder[:users - sum(counts)]:
        counts[i] += 1
    return counts


def journey_vu(journeys: Journey | list[Journey], base_url: str,
               env: dict[str, str] | None = None, think: float = 0.0):
    """A load-test virtual user: walk a journey's steps, pausing for each step's
    think time, and start again with a fresh identity until the stage deadline.
    A failed step ends that walk (after its pause), like a real user giving up.

    Given several JOURNEYS, the stage's users are split between them by `weight`
    (see `apportion`) and each user stays on its journey for the whole stage, so
    a journey's weight is its share of the users in the app at once, whatever
    its walks take. Steps are then labelled `journey › step`. Each step is
    recorded under its label, so the report can name the step that broke. THINK
    is the pause for steps that don't set their own (`--think-time`, or a launch
    profile's)."""
    env = dict(os.environ) if env is None else env
    mix = [journeys] if isinstance(journeys, Journey) else list(journeys)
    weights = [j.weight for j in mix]

    async def vu(client: httpx.AsyncClient, deadline: float, sink, gate=None,
                 index: int = 0, users: int = 1) -> None:
        loop = asyncio.get_running_loop()
        journey = mix[0]
        if len(mix) > 1:
            seats = [j for j, n in zip(mix, apportion(users, weights)) for _ in range(n)]
            journey = seats[index]
        prefix = f"{journey.name}{SEP}" if len(mix) > 1 else ""
        while loop.time() < deadline:
            variables: dict[str, Any] = fresh_uniques()
            jar = httpx.Cookies()
            for step in journey.steps:
                if gate is not None and not await gate.wait(deadline):
                    return
                if loop.time() >= deadline:
                    return
                outcome = await run_step(client, step, base_url, variables, env, jar)
                _record(sink, outcome, prefix)
                # A user pauses after a step either way; restarting the instant a step
                # fails would hammer the app harder than real users who hit an error.
                pause = step.think or think
                if pause:
                    remaining = deadline - loop.time()
                    if remaining <= 0:
                        return
                    await asyncio.sleep(min(pause, remaining))
                if not outcome.ok:
                    break
            # Never spin: a walk that failed without awaiting must still yield.
            await asyncio.sleep(0)

    return vu


def _record(sink, outcome: StepCheck, prefix: str = "") -> None:
    """One step's outcome into the stage's numbers. An answer the journey didn't
    expect counts as a failure, even a 4xx: under load that's a step going wrong."""
    label = prefix + outcome.step.label
    if outcome.status is None:
        sink.record_error(label, outcome.kind or "network")
    elif outcome.ok or outcome.status >= 500 or outcome.status == 429:
        sink.record_response(label, outcome.status, outcome.latency, outcome.headers)
    else:
        sink.record_error(label, outcome.kind or f"unexpected {outcome.status}")


def secret_values(journey: Journey, env: dict[str, str]) -> set[str]:
    """The secrets a journey sends: the environment variables it reads."""
    return {env[name] for name in journey.env_names() if env.get(name)}


def _mask(text: str, secrets: set[str], variables: dict[str, Any]) -> str:
    """TEXT with every secret replaced by ***: the journey's env values, and any
    extracted value whose name looks secret (a token, a session id)."""
    hidden = set(secrets) | {str(v) for k, v in variables.items()
                             if SENSITIVE_KEY.search(k) and isinstance(v, str)}
    for value in sorted(hidden, key=len, reverse=True):
        if len(value) >= 4:
            text = text.replace(value, "***")
    return text


async def run_step(client: httpx.AsyncClient, step: Step, base_url: str,
                   variables: dict[str, Any], env: dict[str, str],
                   jar: httpx.Cookies, secrets: set[str] | None = None) -> StepCheck:
    """Send one step with this journey run's cookies (JAR), judge it against
    `expect`, and pull its `extract` values into VARIABLES for the steps after it."""
    outcome = StepCheck(step)
    try:
        url = step_url(base_url, str(render(step.path, variables, env)))
        req_headers = {k: str(v) for k, v in render(step.headers, variables, env).items()}
        payload = render(step.json, variables, env) if step.json is not None else None
        body = render(step.body, variables, env) if step.body is not None else None
    except (TemplateError, OffOriginError) as exc:
        outcome.problem, outcome.kind = str(exc), "journey error"
        return outcome

    request = client.build_request(step.method, url, headers=req_headers, json=payload,
                                   content=body)
    start = time.perf_counter()
    try:
        resp = await _send(client, request, jar)
    except OffOriginError as exc:
        outcome.problem, outcome.kind = str(exc), "left the app"
        return outcome
    except httpx.TimeoutException:
        outcome.problem, outcome.kind = "timed out", "timeout"
        return outcome
    except httpx.ConnectError:
        outcome.problem, outcome.kind = "couldn't reach the app (ConnectError)", \
            "connection refused"
        return outcome
    except httpx.HTTPError as exc:
        outcome.problem = f"couldn't reach the app ({exc.__class__.__name__})"
        outcome.kind = "network"
        return outcome
    outcome.latency = time.perf_counter() - start
    outcome.status = resp.status_code
    outcome.headers = resp.headers

    if not step.accepts(resp.status_code):
        wanted = (" or ".join(map(str, step.expect)) if step.expect else "a status below 400")
        outcome.problem = f"returned {resp.status_code}, expected {wanted}"
        # Bodies can echo what was sent (validation errors often do), secrets included.
        snippet = _mask(resp.text.strip().replace("\n", " "), secrets or set(), variables)
        outcome.snippet = snippet[:_SNIPPET] or None
        return outcome

    for name, source in step.extract.items():
        value = extract(resp, source)
        if value is None:
            outcome.problem = f"couldn't find {source} in the response to extract {name}"
            outcome.kind = "missing extract"
            return outcome
        variables[name] = value
    outcome.ok = True
    return outcome


async def _send(client: httpx.AsyncClient, request: httpx.Request,
                jar: httpx.Cookies) -> httpx.Response:
    """Send REQUEST with this run's cookies, following redirects one hop at a time
    so every hop carries the cookies earlier hops set (a login that redirects to
    /account stays logged in). The client keeps no cookies of its own, and its
    same-origin hook checks each hop."""
    for _ in range(_MAX_REDIRECTS + 1):
        if "cookie" in request.headers:
            del request.headers["cookie"]
        jar.set_cookie_header(request)
        resp = await client.send(request, follow_redirects=False)
        jar.extract_cookies(resp)
        if resp.next_request is None:
            return resp
        await resp.aclose()
        request = resp.next_request
    raise httpx.TooManyRedirects("too many redirects", request=request)


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
