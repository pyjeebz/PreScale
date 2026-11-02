"""Journeys at load: virtual users walk whole journeys, each ramped on its own."""

import asyncio
import json

import httpx
from click.testing import CliRunner

from prescale_cli.journeys.load import JourneyRun, first_to_break, journeys_block, ramp
from prescale_cli.journeys.model import parse
from prescale_cli.journeys.replay import check
from prescale_cli.loadtest import analyze
from prescale_cli.main import cli

SHOP = {
    "version": 1, "name": "checkout", "type": "checkout",
    "steps": [
        {"name": "log in", "request": {"method": "POST", "path": "/api/login"},
         "expect": {"status": 200}, "extract": {"token": "body.token"}},
        {"name": "place order",
         "request": {"method": "POST", "path": "/api/orders",
                     "headers": {"Authorization": "Bearer {{token}}"}},
         "expect": {"status": 201}},
    ],
}
BROWSE = {"version": 1, "name": "browse", "steps": [{"request": {"path": "/"}}]}


def _shop(pool: int):
    """A mock shop whose order step fails once more than POOL orders are in
    flight at once, and which checks every order carries its own login's token
    and cookie."""
    state = {"in_flight": 0, "logins": 0, "mixed": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/api/login":
            state["logins"] += 1
            token = f"t{state['logins']}"
            return httpx.Response(200, json={"token": token},
                                  headers={"set-cookie": f"sid={token}; Path=/"})
        if request.url.path == "/api/orders":
            token = request.headers["authorization"].removeprefix("Bearer ")
            if request.headers.get("cookie") != f"sid={token}":
                state["mixed"] += 1
            if state["in_flight"] >= pool:
                return httpx.Response(500, text="pool exhausted")
            state["in_flight"] += 1
            try:
                await asyncio.sleep(0.02)
            finally:
                state["in_flight"] -= 1
            return httpx.Response(201)
        return httpx.Response(200)

    return httpx.MockTransport(handler), state


def _ramp(journey, transport, levels=(1, 2, 5, 10, 20)):
    return asyncio.run(ramp(journey, "http://shop.test", levels=list(levels),
                            stage_seconds=0.2, warmup=False, transport=transport))


def test_ramp_records_each_step_and_finds_the_step_that_breaks():
    transport, state = _shop(pool=4)
    stages, _ = _ramp(parse(SHOP), transport)
    assert set(stages[0].routes) == {"POST /api/login", "POST /api/orders"}
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert report.onset_reason == "errors"
    assert report.culprit_route == "POST /api/orders"
    assert 1 <= report.survives_users < 20
    # every order went out with its own user's token and cookie
    assert state["mixed"] == 0 and state["logins"] > 20


def test_journeys_block_names_the_step_and_skips_stale_journeys():
    transport, _ = _shop(pool=4)
    checkout, browse = parse(SHOP), parse(BROWSE)
    stages, _ = _ramp(checkout, transport)
    ok = JourneyRun(checkout, asyncio.run(check(checkout, "http://shop.test", env={},
                                                transport=transport)),
                    report=analyze(stages, latency_wall=2.0, error_threshold=0.02))

    def gone(request):
        return httpx.Response(404, text="moved")
    stale = JourneyRun(browse, asyncio.run(check(browse, "http://shop.test", env={},
                                                 transport=httpx.MockTransport(gone))))

    block = journeys_block([ok, stale])
    assert block[0]["status"] == "ok"
    assert block[0]["culprit_step"] == {"index": 2, "name": "place order",
                                        "route": "POST /api/orders"}
    assert [s["route"] for s in block[0]["steps"]] == ["POST /api/login", "POST /api/orders"]
    assert block[0]["steps"][1]["error_rate"] > 0
    assert block[1] == {"name": "browse", "type": "browse", "weight": 60.0,
                        "status": "stale",
                        "reason": "step 1 (step 1): returned 404, expected a status "
                                  "below 400: moved"}
    assert first_to_break([ok, stale]) is ok
    json.dumps(block)  # it goes into the saved Result


def test_first_to_break_prefers_the_lowest_capacity():
    transport, _ = _shop(pool=4)
    weak = JourneyRun(parse(SHOP), None,
                      report=analyze(_ramp(parse(SHOP), transport)[0],
                                     latency_wall=2.0, error_threshold=0.02))
    strong = JourneyRun(parse(BROWSE), None,
                        report=analyze(_ramp(parse(BROWSE), transport)[0],
                                       latency_wall=2.0, error_threshold=0.02))
    assert strong.report.onset_users is None
    assert first_to_break([strong, weak]) is weak
    assert first_to_break([JourneyRun(parse(BROWSE), None)]) is None


# --- `prescale run` picks journeys ---------------------------------------------

def _dir(tmp_path, *docs):
    for doc in docs:
        (tmp_path / f"{doc['name']}.yaml").write_text(json.dumps(doc))
    return str(tmp_path)


def _out(res):
    return " ".join(res.output.split())


def test_run_refuses_journey_writes_on_a_non_local_host(tmp_path):
    res = CliRunner().invoke(cli, ["run", "https://shop.example.com", "--i-own-this",
                                   "--dir", _dir(tmp_path, SHOP)])
    assert res.exit_code == 2
    assert "--allow-writes shop.example.com" in _out(res)


def test_run_stops_on_a_broken_journey_file(tmp_path):
    res = CliRunner().invoke(cli, ["run", "http://localhost:1",
                                   "--dir", _dir(tmp_path, {**BROWSE, "version": 9})])
    assert res.exit_code == 2
    assert "version must be 1" in _out(res)


def test_run_journey_flag_conflicts_with_url_mode(tmp_path):
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--urls", "--journey", "x",
                                   "--dir", _dir(tmp_path, BROWSE)])
    assert res.exit_code == 2
    assert "--journey can't be combined" in _out(res)


def test_run_unknown_journey(tmp_path):
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--journey", "nope",
                                   "--dir", _dir(tmp_path, BROWSE)])
    assert res.exit_code == 2
    assert "no journey named nope" in _out(res)


# --- review fixes -------------------------------------------------------------

LOGIN_REDIRECT = {
    "version": 1, "name": "account", "type": "account",
    "steps": [
        {"name": "log in", "request": {"method": "POST", "path": "/login"},
         "expect": {"status": 200}, "extract": {"user": "body.user"}},
        {"name": "update cart", "request": {"method": "POST", "path": "/cart"},
         "expect": {"status": 200}, "extract": {"again": "body.user"}},
    ],
}


def _login_redirects():
    """POST /login sets a cookie on a 302; POST /cart answers 303. The pages they
    redirect to only know the user if the cookie came along."""
    logins = iter(range(10_000))

    def handler(request):
        cookie = request.headers.get("cookie")
        if request.url.path == "/login":
            return httpx.Response(302, headers={"location": "/me",
                                                "set-cookie": f"sid=u{next(logins)}; Path=/"})
        if request.url.path == "/cart":
            return httpx.Response(303, headers={"location": "/cartview"})
        if request.url.path in ("/me", "/cartview"):
            return httpx.Response(200, json={"user": cookie} if cookie else {})
        if request.url.path == "/":
            return httpx.Response(302, headers={"location": "https://sso.example.com/"})
        return httpx.Response(404)

    return httpx.MockTransport(handler)


def test_cookies_survive_redirects_in_verify():
    result = asyncio.run(check(parse(LOGIN_REDIRECT), "http://shop.test", env={},
                               transport=_login_redirects()))
    assert result.ok, result.failed and result.failed.problem


def test_cookies_survive_redirects_at_load_and_root_redirect_is_fine():
    # "/" redirects to an SSO host: journeys don't probe it, so no OffOriginError.
    stages, warning = _ramp(parse(LOGIN_REDIRECT), _login_redirects(), levels=(1, 5))
    assert warning is None
    for stage in stages:
        assert all(stat.errors == 0 for stat in stage.routes.values()), stage.routes


def _fake_checks(monkeypatch, stale_names=()):
    """Replace the network in `run`'s journey mode: CHECK says which journeys are
    stale; RAMP returns a run that holds at every level."""
    from prescale_cli.commands import run as run_cmd
    from prescale_cli.journeys.replay import JourneyCheck, StepCheck
    from prescale_cli.loadtest import RouteStat, StageResult

    async def fake_check_all(journeys, url, *, timeout, headers):
        out = []
        for j in journeys:
            c = JourneyCheck(j)
            ok = j.name not in stale_names
            c.steps = [StepCheck(s, status=200 if ok else 404, ok=ok,
                                 problem=None if ok else "returned 404, expected 200")
                       for s in j.steps[:1]] if not ok else \
                [StepCheck(s, status=200, ok=True) for s in j.steps]
            out.append(c)
        return out

    async def fake_ramp(journey, url, *, levels, **kwargs):
        mix = journey if isinstance(journey, list) else [journey]
        routes = {(f"{j.name} › " if len(mix) > 1 else "") + s.label:
                  RouteStat(total=10, latencies=[0.01] * 10) for j in mix for s in j.steps}
        return [StageResult(users=u, duration=1.0, routes=dict(routes)) for u in levels], None

    monkeypatch.setattr(run_cmd, "_check_all", fake_check_all)
    monkeypatch.setattr(run_cmd, "ramp", fake_ramp)


def test_run_json_stays_pure_when_a_journey_is_stale(tmp_path, monkeypatch):
    _fake_checks(monkeypatch, stale_names={"browse"})
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--json", "--no-save",
                                   "-u", "5", "--dir", _dir(tmp_path, SHOP, BROWSE)])
    assert res.exit_code == 0, res.output
    result = json.loads(res.stdout)  # nothing but the Result on stdout
    assert "stale, not load-tested" in res.stderr
    statuses = {j["name"]: j["status"] for j in result["journeys"]}
    assert statuses == {"browse": "stale", "checkout": "ok"}
    # nothing broke, so there's no culprit journey
    assert result["verdict"]["onset_users"] is None
    assert result["verdict"]["culprit_journey"] is None
    assert result["config"]["mode"] == "journeys"


def test_run_applies_think_time_to_steps_without_their_own(tmp_path, monkeypatch):
    seen = {}
    _fake_checks(monkeypatch)
    from prescale_cli.commands import run as run_cmd
    inner = run_cmd.ramp

    async def spy(journey, url, **kwargs):
        seen[journey.name] = kwargs.get("think")
        return await inner(journey, url, **kwargs)

    monkeypatch.setattr(run_cmd, "ramp", spy)
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--json", "--no-save",
                                   "-u", "5", "--think-time", "1.5",
                                   "--dir", _dir(tmp_path, BROWSE)])
    assert res.exit_code == 0, res.output
    assert seen == {"browse": 1.5}


# --- the combined pass and --expect ------------------------------------------------

def test_apportion_adds_up_and_follows_weights():
    from prescale_cli.journeys.replay import apportion
    assert apportion(10, [9, 1]) == [9, 1]
    assert apportion(30, [1, 1]) == [15, 15]
    assert apportion(3, [60, 25, 8, 5, 2]) == [2, 1, 0, 0, 0]
    assert sum(apportion(97, [60, 25, 8, 5, 2])) == 97


def test_mixed_users_stay_on_their_journey_whatever_its_walk_takes():
    from prescale_cli.journeys.replay import journey_vu
    from prescale_cli.loadtest import _Sink

    quick = parse({**BROWSE, "name": "quick", "weight": 1})
    slow = parse({**BROWSE, "name": "slow", "weight": 1,
                  "steps": [{"request": {"path": "/slow"}, "think": "1s"}]})
    vu = journey_vu([quick, slow], "http://shop.test", env={})
    sinks = [_Sink(labels=False) for _ in range(10)]

    async def go():
        transport = httpx.MockTransport(lambda r: httpx.Response(200))
        async with httpx.AsyncClient(transport=transport) as c:
            deadline = asyncio.get_running_loop().time() + 0.3
            await asyncio.gather(*(vu(c, deadline, sinks[i], None, i, 10) for i in range(10)))
    asyncio.run(go())
    # each user only ever walked one journey; half the users are on each
    walked = [set(s.routes) for s in sinks]
    assert all(len(w) == 1 for w in walked)
    assert sum(w == {"quick › GET /"} for w in walked) == 5
    assert sum(w == {"slow › GET /slow"} for w in walked) == 5


def _report(survives, onset, culprit=None, max_tested=100):
    from prescale_cli.loadtest import RunReport
    return RunReport(stages=[], survives_users=survives, max_tested=max_tested,
                     onset_users=onset, onset_reason="errors" if onset else None,
                     culprit_route=culprit, survives_low=survives, survives_high=survives)


def test_combined_block_flags_interference():
    from prescale_cli.journeys.load import combined_block
    checkout = parse({**SHOP, "weight": 1})
    search = parse({**BROWSE, "name": "search", "weight": 3})
    runs = [JourneyRun(checkout, None, report=_report(40, 50, "POST /api/orders")),
            JourneyRun(search, None, report=_report(100, None))]
    # together: breaks at 60 users in total, at checkout's order step.
    # checkout had only 60 * 1/4 = 15 of its own users there, but held 40 alone.
    block = combined_block(_report(50, 60, "checkout › POST /api/orders"), runs)
    assert block["mix"] == {"checkout": 25.0, "search": 75.0}
    assert block["culprit_journey"] == "checkout"
    assert block["culprit_step"] == {"index": 2, "name": "place order",
                                     "route": "POST /api/orders"}
    assert block["interference"] == {"journey": "checkout", "users_at_break": 15.0,
                                     "held_alone": 40, "with": ["search"]}
    # breaking with more of its own users than it held alone is not interference
    calm = combined_block(_report(150, 200, "checkout › POST /api/orders"), runs)
    assert calm["interference"] is None
    held = combined_block(_report(100, None), runs)
    assert held["culprit_journey"] is None and held["interference"] is None


def test_expect_splits_users_across_journeys_by_weight():
    from prescale_cli.commands.run import expect_block
    result = {
        "verdict": {"survives_users": 20, "onset_users": 30},
        "journeys": [
            {"name": "browse", "status": "ok", "weight": 60, "survives_users": 400,
             "onset_users": None},
            {"name": "checkout", "status": "ok", "weight": 5, "survives_users": 20,
             "onset_users": 30},
            {"name": "old", "status": "stale", "weight": 5},
        ],
        "combined": {"survives_users": 400, "onset_users": None},
    }
    exp = expect_block(result, 300)
    assert exp["meets"] is False
    # the stale journey still takes its share of the users (weights total 70)
    assert [(j["name"], j["users"], j["meets"]) for j in exp["journeys"]] == [
        ("browse", 257.1, True), ("checkout", 21.4, False)]
    assert exp["combined"] == {"survives_users": 400, "meets": True}
    assert exp["untested"] == ["old"]
    # every tested share fits, but "old" was never tested: unknown, not a yes
    assert expect_block(result, 100)["meets"] is None
    fresh = {**result, "journeys": result["journeys"][:2]}
    assert expect_block(fresh, 100)["meets"] is True
    # more users than were ever tested on a journey that never broke: unknown
    assert expect_block(fresh, 6000)["journeys"][0]["meets"] is None


def test_expect_on_a_url_run():
    from prescale_cli.commands.run import expect_block
    broke = {"verdict": {"survives_users": 90, "onset_users": 100}}
    assert expect_block(broke, 50)["meets"] is True
    assert expect_block(broke, 200)["meets"] is False
    held = {"verdict": {"survives_users": 200, "onset_users": None}}
    assert expect_block(held, 500)["meets"] is None


def test_run_combined_pass_and_expect_end_to_end(tmp_path, monkeypatch):
    _fake_checks(monkeypatch)
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--json", "--no-save",
                                   "-u", "5", "--expect", "4",
                                   "--dir", _dir(tmp_path, SHOP, BROWSE)])
    assert res.exit_code == 0, res.output
    result = json.loads(res.stdout)
    assert result["combined"]["mix"] == {"browse": 92.3, "checkout": 7.7}
    assert result["expect"]["meets"] is True
    res = CliRunner().invoke(cli, ["run", "http://localhost:1", "--json", "--no-save",
                                   "-u", "5", "--no-combined",
                                   "--dir", _dir(tmp_path, SHOP, BROWSE)])
    assert "combined" not in json.loads(res.stdout)
