"""Diagnosing the journey step that breaks first (`prescale investigate` on journeys)."""

import asyncio

import httpx

from prescale_cli.investigate import Probes, classify
from prescale_cli.journeys.diagnose import diagnose_step, gather_step_probes
from prescale_cli.journeys.load import JourneyRun, ramp
from prescale_cli.journeys.model import parse
from prescale_cli.journeys.replay import check
from prescale_cli.loadtest import analyze
from prescale_cli.render import render_investigation

BASE = "http://shop.test"
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


def _shop(pool: int):
    """Orders fail once more than POOL are in flight; an order needs the cart id
    and token from the earlier steps, as on a real shop."""
    state = {"in_flight": 0, "orders_without_state": 0}

    async def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/api/login":
            return httpx.Response(200, json={"token": "t"}, headers={"server": "gunicorn"})
        if path == "/api/cart":
            return httpx.Response(201, json={"id": 7})
        if path.endswith("/order"):
            if path != "/api/carts/7/order" or request.headers.get("authorization") != "Bearer t":
                state["orders_without_state"] += 1
                return httpx.Response(400)
            if state["in_flight"] >= pool:
                return httpx.Response(500, text="pool exhausted")
            state["in_flight"] += 1
            try:
                await asyncio.sleep(0.02)
            finally:
                state["in_flight"] -= 1
            return httpx.Response(201, headers={"server": "gunicorn/21.2.0"})
        return httpx.Response(404)

    return httpx.MockTransport(handler), state


def _broken_run(pool: int = 4):
    transport, state = _shop(pool)
    journey = parse(SHOP)
    stages, _ = asyncio.run(ramp(journey, BASE, levels=[1, 2, 5, 10, 20], stage_seconds=0.2,
                                 warmup=False, env={}, transport=transport))
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    first = asyncio.run(check(journey, BASE, env={}, transport=transport))
    return JourneyRun(journey, first, report), transport, state


def _probes(run, transport, walks=3):
    return asyncio.run(gather_step_probes(run, BASE, latency_wall=2.0, error_threshold=0.02,
                                          env={}, transport=transport, walks=walks))


def test_probes_the_step_that_broke_with_the_journeys_state():
    run, transport, state = _broken_run()
    probes = _probes(run, transport)
    assert probes.culprit_route == "POST /api/carts/{{cart_id}}/order"
    assert probes.onset_users == run.report.onset_users
    # the 1-user baseline walked log in and add to cart first, so the order carried them
    assert probes.baseline_p95_ms is not None and probes.baseline_p95_ms >= 15
    assert state["orders_without_state"] == 0
    # the steps before it held while it failed
    assert probes.static_route == "log in, add to cart"
    assert probes.static_ok is True
    assert "5xx" in probes.error_kinds or 500 in probes.status_counts
    assert probes.server == "gunicorn/21.2.0"


def test_names_a_pool_when_one_step_fails_and_the_others_hold():
    run, transport, _ = _broken_run()
    inv = diagnose_step(run, _probes(run, transport))
    assert inv["culprit_journey"] == "checkout"
    assert inv["culprit_step"] == {"index": 3, "name": "place order",
                                   "route": "POST /api/carts/{{cart_id}}/order"}
    assert inv["bottleneck_class"] == "connection_pool"
    assert inv["confidence"] == "high"
    assert "the journey's other steps held" in inv["summary"]
    assert any("other steps (log in, add to cart) held" in e for e in inv["evidence"])
    assert any("pool" in r for r in inv["remediation"])
    assert inv["stack"] == {"server": "gunicorn/21.2.0"}
    assert inv["interference"] is None


def test_the_whole_server_failing_reads_differently_from_one_step():
    probes = Probes(culprit_route="POST /api/orders", onset_users=20, static_ok=False,
                    static_route="log in", status_counts={500: 9},
                    reference="the journey's other steps")
    diag = classify(probes)
    assert diag.bottleneck_class == "connection_pool" and diag.confidence == "medium"


def test_interference_on_the_culprit_journey_is_named():
    run, transport, _ = _broken_run()
    starved = {"journey": "checkout", "users_at_break": 15, "held_alone": 20,
               "with": ["browse"]}
    inv = diagnose_step(run, _probes(run, transport), interference=starved)
    assert inv["interference"] == starved
    assert any("with browse running too, checkout broke at 15 of its own users; "
               "alone it held 20" in e for e in inv["evidence"])
    # interference on another journey isn't this step's story
    other = dict(starved, journey="search")
    assert diagnose_step(run, _probes(run, transport), interference=other)["interference"] is None


def test_a_journey_that_held_has_nothing_to_probe():
    transport, _ = _shop(pool=1000)
    journey = parse(SHOP)
    stages, _ = asyncio.run(ramp(journey, BASE, levels=[1, 2, 5], stage_seconds=0.1,
                                 warmup=False, env={}, transport=transport))
    report = analyze(stages, latency_wall=2.0, error_threshold=0.02)
    run = JourneyRun(journey, asyncio.run(check(journey, BASE, env={}, transport=transport)),
                     report)
    assert report.onset_users is None
    assert _probes(run, transport) is None


def test_url_evidence_still_says_static():
    probes = Probes(culprit_route="GET /checkout", onset_users=50, static_route="GET /app.css",
                    static_ok=True, status_counts={500: 3})
    diag = classify(probes)
    assert "static assets held" in diag.summary
    assert "static GET /app.css held at 50 users" in diag.evidence


def test_the_panel_names_the_journey_and_step(capsys):
    run, transport, _ = _broken_run()
    render_investigation({"investigation": diagnose_step(run, _probes(run, transport))})
    out = " ".join(capsys.readouterr().out.replace("│", " ").split())
    assert "checkout, step 3 place order" in out
    assert "connection_pool" in out


def test_investigate_refuses_writes_on_a_non_local_host_before_any_request(tmp_path):
    import yaml
    from click.testing import CliRunner

    from prescale_cli.main import cli

    (tmp_path / "checkout.yaml").write_text(yaml.safe_dump(SHOP))
    out = CliRunner().invoke(cli, ["investigate", "https://staging.example.com",
                                   "--dir", str(tmp_path), "--i-own-this"])
    assert out.exit_code == 2
    assert "checkout change data" in " ".join(out.output.split())
    assert "--allow-writes staging.example.com" in out.output
