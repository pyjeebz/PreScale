"""The fix prompt for coding agents, and the diagnosis in the HTML report."""

import asyncio

import httpx

from prescale_cli.fixprompt import fix_prompt
from prescale_cli.investigate import investigate
from prescale_cli.report import render_html

INV = {
    "culprit_route": "POST /api/carts/{{cart_id}}/order", "culprit_journey": "checkout",
    "culprit_step": {"index": 3, "name": "place order",
                     "route": "POST /api/carts/{{cart_id}}/order"},
    "bottleneck_class": "connection_pool", "confidence": "high",
    "summary": "5xx under load while the journey's other steps held.",
    "evidence": ["the journey's other steps (log in, add to cart) held at 30 users"],
    "remediation": ["Increase the DB/upstream connection-pool size."],
    "stack": {"server": "gunicorn/21.2.0"}, "interference": None,
}


def _result(url="http://localhost:8400", **inv):
    return {
        "target": {"url": url},
        "verdict": {"survives_users": 30, "onset_users": 50, "onset_reason": "errors climb",
                    "confidence": {"survives_low": 20, "survives_high": 30}},
        "investigation": {**INV, **inv},
    }


def test_no_diagnosis_no_prompt():
    assert fix_prompt({"target": {"url": "http://x"}, "verdict": {}}) is None


def test_a_journey_prompt_says_where_when_why_and_how_to_check():
    prompt = fix_prompt(_result())
    assert prompt.startswith("PreScale load-tested http://localhost:8400 and found")
    assert ('Where: journey "checkout", step 3 "place order" '
            "(POST /api/carts/{{cart_id}}/order)") in prompt
    assert "It survives ~30 concurrent users (likely 20–30); errors climb at ~50." in prompt
    assert "Likely cause (connection_pool, high confidence): 5xx under load" in prompt
    assert "- the journey's other steps (log in, add to cart) held at 30 users" in prompt
    assert "- Increase the DB/upstream connection-pool size." in prompt
    assert "Detected: server gunicorn/21.2.0" in prompt
    assert "`prescale investigate http://localhost:8400 --journey checkout`" in prompt
    assert "Don't change the test setup" in prompt


def test_credentials_and_query_never_reach_the_prompt():
    prompt = fix_prompt(_result(url="https://admin:hunter2@staging.example.com:8443/app"
                                    "?token=abc#x"))
    assert "hunter2" not in prompt and "admin" not in prompt and "token=abc" not in prompt
    assert "https://staging.example.com:8443/app" in prompt
    assert "[::1]:8000" in fix_prompt(_result(url="http://[::1]:8000/"))


def test_a_name_with_spaces_is_quoted_in_the_command():
    prompt = fix_prompt(_result(culprit_journey="quick buy"))
    assert "--journey 'quick buy'`" in prompt


def test_a_break_only_together_reads_that_way():
    result = _result()
    result["verdict"].update(onset_users=None, survives_users=100)
    result["combined"] = {"onset_users": 40, "survives_users": 30}
    assert ("Each journey held on its own, but together they survive ~30 concurrent users "
            "in total.") in fix_prompt(result)


def test_url_investigate_adds_the_prompt():
    async def handler(request):
        if request.url.path == "/slow":
            await asyncio.sleep(0.01)
            return httpx.Response(500 if handler.n > 3 else 200)
        return httpx.Response(200, text="<html></html>")
    handler.n = 0

    class Counting(httpx.MockTransport):
        async def handle_async_request(self, request):
            if request.url.path == "/slow":
                handler.n += 1
            return await super().handle_async_request(request)

    result = asyncio.run(investigate("http://localhost:9", paths=("/slow",), max_users=20,
                                     stage_seconds=0.2, store=None,
                                     transport=Counting(handler)))
    assert result["investigation"]["culprit_route"] == "/slow"
    assert result["fix_prompt"] == fix_prompt(result)
    assert "Where: /slow" in result["fix_prompt"]


def test_the_html_report_shows_the_diagnosis_and_prompt_escaped():
    base = {
        "id": "x", "kind": "run", "tool_version": "1", "created_at": "2026-11-03T08:00:00Z",
        "warning": None,
        "target": {"url": "http://localhost:8400", "host": "localhost",
                   "routes": ["POST /api/orders"]},
        "config": {"method": "GET", "stage_seconds": 1, "max_users": 50,
                   "latency_wall_s": 2.0},
        "stages": [],
        "verdict": {"survives_users": 30, "max_tested": 50, "onset_users": 50,
                    "onset_reason": "errors", "culprit_route": "POST /api/orders",
                    "bottleneck": "5xx", "saturated": False, "saturation_users": None,
                    "marginal": False, "peak_rps": 10.0,
                    "confidence": {"survives_low": 20, "survives_high": 30, "stable": True}},
    }
    result = {**base, "investigation": {**INV, "evidence": ["<script>x</script> held"]}}
    result["fix_prompt"] = fix_prompt(result)
    page = render_html(result)
    assert "<h3>Diagnosis</h3>" in page
    assert "checkout, step 3 <b>place order</b>" in page
    assert "&lt;script&gt;x&lt;/script&gt; held" in page and "<script>x</script>" not in page
    assert "Fix prompt for your coding agent" in page and ">Copy</button>" in page
    # no diagnosis, no section
    assert "<h3>Diagnosis</h3>" not in render_html(base)
