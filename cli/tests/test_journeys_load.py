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
