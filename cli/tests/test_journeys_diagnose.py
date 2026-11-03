"""Diagnosing the journey step that breaks first (`prescale investigate` on journeys)."""

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
import yaml
from click.testing import CliRunner

from prescale_cli.investigate import Probes, classify
from prescale_cli.journeys.diagnose import (
    MIN_SAMPLES,
    diagnose_run,
    diagnose_step,
    gather_step_probes,
)
from prescale_cli.journeys.load import JourneyRun, combined_block, ramp
from prescale_cli.journeys.model import parse
from prescale_cli.journeys.replay import SEP, check
from prescale_cli.loadtest import analyze
from prescale_cli.main import cli
from prescale_cli.render import render_investigation

BASE = "http://shop.test"
ORDER = "POST /api/carts/{{cart_id}}/order"
SHOP = {
    "version": 1, "name": "checkout", "type": "checkout",
    "steps": [
        {"name": "log in", "request": {"method": "POST", "path": "/api/login"},
         "expect": {"status": 200}, "extract": {"token": "body.token"}},
        {"name": "add to cart",
         "request": {"method": "POST", "path": "/api/cart",
                     "headers": {"Authorization": "Bearer {{token}}"}},
         "expect": {"status": 201}, "extract": {"cart_id": "body.id"}},
        {"name": "place order",
         "request": {"method": "POST", "path": "/api/carts/{{cart_id}}/order",
                     "headers": {"Authorization": "Bearer {{token}}"}},
         "expect": {"status": 201}},
    ],
}
QUICKBUY = dict(SHOP, name="quickbuy")
FAST = {"seconds": 0, "cooldown": 0}


def _shop(pool: int, fail_status: int = 500):
    """Orders fail with FAIL_STATUS once more than POOL are in flight; an order
    needs the cart id and token from the earlier steps, as on a real shop."""
    state = {"in_flight": 0, "orders_without_state": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/login":
            return httpx.Response(200, json={"token": "t"})
        if path == "/api/cart":
            return httpx.Response(201, json={"id": 7})
        if path.endswith("/order"):
            if path != "/api/carts/7/order" or request.headers.get("authorization") != "Bearer t":
                state["orders_without_state"] += 1
                return httpx.Response(400)
            if state["in_flight"] >= pool:
                return httpx.Response(fail_status, text="pool exhausted")
            state["in_flight"] += 1
            try:
                await asyncio.sleep(0.02)
            finally:
                state["in_flight"] -= 1
            return httpx.Response(201, headers={"server": "gunicorn/21.2.0"})
        return httpx.Response(404)

    return httpx.MockTransport(handler), state


def _ramped(spec, transport, levels=(1, 2, 5, 10, 20)):
    journey = parse(spec)
    stages, _ = asyncio.run(ramp(journey, BASE, levels=list(levels), stage_seconds=0.2,
                                 warmup=False, env={}, transport=transport))
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    first = asyncio.run(check(journey, BASE, env={}, transport=transport))
    return JourneyRun(journey, first, report)


def _probes(run, transport, **kwargs):
    return asyncio.run(gather_step_probes(run.journey, run.report, BASE, latency_wall=2.0,
                                          error_threshold=0.02, env={}, transport=transport,
                                          **{**FAST, **kwargs}))


def test_probes_the_step_that_broke_with_the_journeys_state():
    transport, state = _shop(pool=4)
    run = _ramped(SHOP, transport)
    found = _probes(run, transport)
    p = found.probes
    assert p.culprit_route == ORDER and found.index == 3 and not found.together
    assert p.onset_users == run.report.onset_users
    # the 1-user baseline walked log in and add to cart first, so the order carried them
    assert found.samples >= MIN_SAMPLES and p.baseline_p95_ms >= 15
    assert state["orders_without_state"] == 0
    # the steps before it held while it failed
    assert p.static_route == "log in, add to cart" and p.static_ok is True
    assert p.server == "gunicorn/21.2.0"


def test_names_a_pool_when_one_step_fails_and_the_others_hold():
    transport, _ = _shop(pool=4)
    run = _ramped(SHOP, transport)
    inv = diagnose_step(_probes(run, transport))
    assert inv["culprit_journey"] == "checkout"
    assert inv["culprit_step"] == {"index": 3, "name": "place order", "route": ORDER}
    assert (inv["bottleneck_class"], inv["confidence"]) == ("connection_pool", "high")
    assert "the journey's other steps held" in inv["summary"]
    assert any("other steps (log in, add to cart) held" in e for e in inv["evidence"])
    assert any("pool" in r for r in inv["remediation"])
    assert inv["stack"] == {"server": "gunicorn/21.2.0"}
    assert inv["interference"] is None


def test_a_4xx_under_load_is_not_read_as_a_pool_or_a_queue():
    transport, _ = _shop(pool=4, fail_status=409)
    run = _ramped(SHOP, transport)
    inv = diagnose_step(_probes(run, transport))
    assert inv["bottleneck_class"] == "unexpected_answer"
    assert "unexpected 409" in inv["summary"]
    # even when throughput flattened, which alone would read as a concurrency ceiling
    probes = Probes(culprit_route=ORDER, onset_users=20, throughput_plateaued=True,
                    error_kinds={"unexpected 409": 9}, reference="the journey's other steps")
    assert classify(probes).bottleneck_class == "unexpected_answer"
    probes.error_kinds = {"missing extract": 4}
    assert classify(probes).bottleneck_class == "unexpected_answer"


def test_steps_sharing_a_route_are_not_their_own_reference():
    spec = {"version": 1, "name": "cart", "type": "write", "steps": [
        {"name": "add one", "request": {"method": "POST", "path": "/api/cart"},
         "expect": {"status": 201}},
        {"name": "view", "request": {"path": "/api/view"}},
        {"name": "add two", "request": {"method": "POST", "path": "/api/cart"},
         "expect": {"status": 201}},
    ]}
    state = {"in_flight": 0}

    async def handler(request):
        if request.url.path == "/api/cart":
            if state["in_flight"] >= 3:
                return httpx.Response(500)
            state["in_flight"] += 1
            try:
                await asyncio.sleep(0.02)
            finally:
                state["in_flight"] -= 1
            return httpx.Response(201)
        return httpx.Response(200)

    transport = httpx.MockTransport(handler)
    run = _ramped(spec, transport)
    found = _probes(run, transport)
    assert found.probes.static_route == "view" and found.probes.static_ok is True
    inv = diagnose_step(found)
    assert inv["confidence"] == "high"
    assert inv["culprit_step"]["index"] == 1
    assert any("steps 1 and 3 all call POST /api/cart" in e for e in inv["evidence"])


def test_no_baseline_from_too_few_replays_and_it_says_so():
    transport, _ = _shop(pool=4)
    run = _ramped(SHOP, transport)
    dead = httpx.MockTransport(lambda request: httpx.Response(503))
    found = _probes(run, dead)
    assert found.samples == 0 and found.probes.baseline_p95_ms is None
    inv = diagnose_step(found)
    assert any("no 1-user baseline: only 0 of 5 replays reached this step" in e
               for e in inv["evidence"])


def test_baseline_replays_stay_under_max_rps():
    transport, _ = _shop(pool=4)
    run = _ramped(SHOP, transport)
    start = time.monotonic()
    found = _probes(run, transport, max_rps=30)
    # 5 walks x 3 requests at 30 req/s is at least half a second
    assert found.walks == 5 and time.monotonic() - start >= 0.45


def _held_alone_but_not_together():
    """Two journeys sharing a 6-order pool: each holds 5 users alone; together,
    at 10 users, they break."""
    transport, _ = _shop(pool=6)
    runs = [_ramped(spec, transport, levels=(1, 2, 5)) for spec in (SHOP, QUICKBUY)]
    assert all(r.report.onset_users is None for r in runs)
    stages, _ = asyncio.run(ramp([r.journey for r in runs], BASE, levels=[1, 2, 5, 10, 20],
                                 stage_seconds=0.2, warmup=False, env={}, transport=transport))
    together = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    assert together.onset_users is not None and SEP in together.culprit_route
    return runs, together, combined_block(together, runs), transport


def test_journeys_that_only_break_together_are_diagnosed():
    runs, together, block, transport = _held_alone_but_not_together()
    inv = asyncio.run(diagnose_run(runs[0], runs, BASE, together=together, combined=block,
                                   latency_wall=2.0, error_threshold=0.02, env={},
                                   transport=transport, **FAST))
    assert inv is not None
    assert inv["culprit_journey"] == block["culprit_journey"]
    assert inv["culprit_step"]["name"] == "place order"
    assert inv["evidence"][0].startswith(f"{block['culprit_journey']} held up on its own "
                                         "(it held 5 users alone) but broke when the journeys "
                                         "ran together")
    assert inv["interference"] == block["interference"]


def test_interference_on_the_culprit_journey_is_named_and_others_noted():
    transport, _ = _shop(pool=4)
    run = _ramped(SHOP, transport)
    found = _probes(run, transport)
    starved = {"journey": "checkout", "users_at_break": 15, "held_alone": 20,
               "with": ["browse"]}
    inv = diagnose_step(found, interference=starved)
    assert inv["interference"] == starved
    assert any("with browse running too, checkout broke at 15 of its own users; "
               "alone it held 20" in e for e in inv["evidence"])
    other = dict(starved, journey="search", **{"with": ["checkout"]})
    inv = diagnose_step(found, interference=other)
    assert inv["interference"] is None
    assert any(e.startswith("also: with checkout running too, search broke at 15")
               for e in inv["evidence"])


def test_a_journey_that_held_has_nothing_to_diagnose():
    transport, _ = _shop(pool=1000)
    run = _ramped(SHOP, transport, levels=(1, 2, 5))
    assert run.report.onset_users is None
    assert _probes(run, transport) is None
    assert asyncio.run(diagnose_run(run, [run], BASE, latency_wall=2.0, error_threshold=0.02,
                                    env={}, transport=transport, **FAST)) is None


def test_url_evidence_still_says_static():
    probes = Probes(culprit_route="GET /checkout", onset_users=50, static_route="GET /app.css",
                    static_ok=True, status_counts={500: 3})
    diag = classify(probes)
    assert "static assets held" in diag.summary
    assert "static GET /app.css held at 50 users" in diag.evidence


def test_the_panel_names_the_journey_and_step(capsys):
    transport, _ = _shop(pool=4)
    run = _ramped(SHOP, transport)
    render_investigation({"investigation": diagnose_step(_probes(run, transport))})
    out = " ".join(capsys.readouterr().out.replace("│", " ").split())
    assert "checkout, step 3 place order" in out
    assert "connection_pool" in out


# --- the command, end to end -------------------------------------------------

ROOT = Path(__file__).resolve().parents[2]


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="module")
def fragile_shop():
    """The example shop, for real: 25-connection pool behind place order."""
    port = _free_port()
    proc = subprocess.Popen([sys.executable, str(ROOT / "examples" / "fragile-shop.py"),
                             str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
                break
            except OSError:
                time.sleep(0.05)
        yield f"http://127.0.0.1:{port}"
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_investigate_json_end_to_end_on_the_example_shop(fragile_shop, tmp_path, monkeypatch):
    monkeypatch.setenv("SHOP_PASSWORD", "demo")
    res = CliRunner().invoke(cli, ["investigate", fragile_shop, "--json", "--journey",
                                   "checkout", "--no-combined", "-u", "100", "-s", "0.5",
                                   "--dir", str(ROOT / "examples" / "journeys"),
                                   "--store", str(tmp_path), "--fail-under", "200"])
    assert res.exit_code == 1  # --fail-under: it breaks well below 200
    result = json.loads(res.stdout)  # stdout is the Result alone
    try:  # not a dev dependency; validated where it's installed
        import jsonschema
    except ImportError:
        jsonschema = None
    if jsonschema is not None:
        jsonschema.validate(result, json.loads(
            (ROOT / "cli/src/prescale_cli/schema/result.schema.json").read_text()))
    inv = result["investigation"]
    assert inv["culprit_journey"] == "checkout"
    assert inv["culprit_step"]["name"] == "place order"
    assert inv["bottleneck_class"] == "connection_pool"
    assert "demo" not in res.stdout


def test_run_and_ci_never_diagnose(fragile_shop, monkeypatch):
    monkeypatch.setenv("SHOP_PASSWORD", "demo")
    res = CliRunner().invoke(cli, ["run", fragile_shop, "--json", "--no-save", "--journey",
                                   "checkout", "--no-combined", "-u", "50", "-s", "0.3",
                                   "--dir", str(ROOT / "examples" / "journeys")])
    assert res.exit_code == 0, res.output
    assert "investigation" not in json.loads(res.stdout)


def _dir(tmp_path, *specs):
    d = tmp_path / "journeys"
    d.mkdir(exist_ok=True)
    for spec in specs:
        (d / f"{spec['name']}.yaml").write_text(yaml.safe_dump(spec))
    return str(d)


def test_investigate_refuses_writes_on_a_non_local_host_before_any_request(tmp_path):
    res = CliRunner().invoke(cli, ["investigate", "https://staging.example.com",
                                   "--dir", _dir(tmp_path, SHOP), "--i-own-this"])
    assert res.exit_code == 2
    assert "checkout change data" in " ".join(res.output.split())
    assert "--allow-writes staging.example.com" in res.output


def test_investigate_refuses_unset_env_before_any_request(tmp_path):
    spec = dict(SHOP, steps=[dict(SHOP["steps"][0], request={
        "method": "POST", "path": "/api/login", "json": {"password": "{{env.NOPE_UNSET}}"}})])
    os.environ.pop("NOPE_UNSET", None)
    res = CliRunner().invoke(cli, ["investigate", "http://localhost:1", "--dir",
                                   _dir(tmp_path, spec)])
    assert res.exit_code == 2 and "NOPE_UNSET" in res.output


def test_investigate_urls_and_path_skip_journeys(tmp_path, monkeypatch):
    from prescale_cli.commands import investigate as inv_cmd
    seen = {}

    async def fake(url, **kwargs):
        seen["url"] = url
        return {"id": "x", "verdict": {"survives_users": 1, "onset_users": None},
                "stages": [], "target": {"url": url, "routes": []}}

    monkeypatch.setattr(inv_cmd, "run_investigate", fake)
    monkeypatch.setattr(inv_cmd, "run_journeys", lambda *a, **k: pytest.fail("journeys ran"))
    for flags in (["--urls"], ["--path", "/x"]):
        res = CliRunner().invoke(cli, ["investigate", "http://localhost:1", "--json",
                                       "--dir", _dir(tmp_path, SHOP), *flags])
        assert res.exit_code == 0, res.output
        assert seen["url"] == "http://localhost:1"
