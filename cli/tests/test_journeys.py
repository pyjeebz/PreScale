"""Journey files: the format, its safety rules, and replaying a journey once."""

import asyncio
import json

import httpx
import pytest
from click.testing import CliRunner

from prescale_cli.journeys.model import (
    JourneyError,
    TemplateError,
    load_dir,
    parse,
    render,
)
from prescale_cli.journeys.replay import check
from prescale_cli.main import cli

CHECKOUT = {
    "version": 1,
    "name": "checkout",
    "type": "checkout",
    "steps": [
        {"name": "log in",
         "request": {"method": "POST", "path": "/api/login",
                     "json": {"email": "{{unique.email}}", "password": "{{env.PW}}"}},
         "expect": {"status": 200},
         "extract": {"token": "body.token"}},
        {"name": "add to cart",
         "request": {"method": "POST", "path": "/api/cart",
                     "headers": {"Authorization": "Bearer {{token}}"}},
         "expect": {"status": [200, 201]},
         "extract": {"cart_id": "body.id"}},
        {"name": "place order",
         "request": {"method": "POST", "path": "/api/carts/{{cart_id}}/order",
                     "headers": {"Authorization": "Bearer {{token}}"}},
         "think": "500ms"},
    ],
}


def _with(**changes):
    doc = json.loads(json.dumps(CHECKOUT))
    doc.update(changes)
    return doc


def _step(i, **changes):
    doc = json.loads(json.dumps(CHECKOUT))
    doc["steps"][i].update(changes)
    return doc


# --- the format -------------------------------------------------------------

def test_parse_valid_journey():
    j = parse(CHECKOUT)
    assert j.name == "checkout" and j.type == "checkout"
    assert j.weight == 5  # the type's default share
    assert [s.label for s in j.steps] == [
        "POST /api/login", "POST /api/cart", "POST /api/carts/{{cart_id}}/order"]
    assert j.steps[1].expect == [200, 201]
    assert j.steps[2].expect is None and j.steps[2].think == 0.5
    assert j.writes
    assert j.env_names() == {"PW"}


def test_read_only_journey_does_not_write():
    j = parse({"version": 1, "name": "browse", "steps": [{"request": {"path": "/"}}]})
    assert j.type == "browse" and not j.writes
    assert j.steps[0].method == "GET" and j.steps[0].name == "step 1"


@pytest.mark.parametrize("doc, message", [
    (_with(version=2), "version must be 1"),
    (_with(name="Check Out"), "name must be lowercase"),
    (_with(type="spam"), "type must be one of"),
    (_with(weight=0), "weight must be a positive number"),
    (_with(steps=[]), "steps must be a non-empty list"),
    (_with(extra=True), "unknown field(s): extra"),
    (_step(0, request={"method": "POST", "path": "https://evil.example/x"}), "single /"),
    (_step(0, request={"method": "DELETE", "path": "//evil.example/x"}), "single /"),
    (_with(weight=float("nan")), "weight must be a positive number"),
    (_with(weight=float("inf")), "weight must be a positive number"),
    (_step(0, request={"method": "BREW", "path": "/"}), "method BREW isn't supported"),
    (_step(0, expect={"status": "ok"}), "HTTP status codes"),
    (_step(0, extract={"token": "cookie.sid"}), "body.<field> or header.<name>"),
    (_step(0, think="soon"), "think must be seconds"),
])
def test_parse_rejects_bad_journeys(doc, message):
    with pytest.raises(JourneyError, match=message.replace("(", r"\(").replace(")", r"\)")):
        parse(doc)


@pytest.mark.parametrize("jtype", ["side_effect", "destructive"])
def test_refused_types_are_never_loaded(jtype):
    with pytest.raises(JourneyError, match="never replayed"):
        parse(_with(type=jtype))


def test_placeholder_must_be_extracted_by_an_earlier_step():
    doc = json.loads(json.dumps(CHECKOUT))
    del doc["steps"][0]["extract"]
    with pytest.raises(JourneyError, match=r"uses \{\{token\}\}, but no earlier step"):
        parse(doc)


def test_unknown_unique_placeholder_is_rejected():
    doc = _step(0, request={"method": "GET", "path": "/u/{{unique.phone}}"})
    with pytest.raises(JourneyError, match="unique.email or unique.id"):
        parse(doc)


@pytest.mark.parametrize("request_part", [
    {"json": {"email": "a@b.co", "password": "hunter2"}},
    {"headers": {"Authorization": "Bearer abc123"}},
    {"json": {"user": {"api_key": "sk-live"}}},
])
def test_literal_secrets_are_refused(request_part):
    doc = _step(0, request={"method": "POST", "path": "/api/login", **request_part})
    with pytest.raises(JourneyError, match="literal value"):
        parse(doc)


@pytest.mark.parametrize("request_part", [
    {"body": '{"email": "a@b.co", "password": "hunter2"}'},
    {"body": "user=a&password=hunter2"},
    {"path": "/a?api_key=sk_live_123"},
    {"json": {"password": 123456}},
    {"headers": {"Authorization": "Basic dXNlcjpwdw== {{unique.id}}"}},
])
def test_literal_secrets_are_refused_anywhere(request_part):
    request_part.setdefault("path", "/api/login")
    doc = _step(0, request={"method": "POST", "path": "/api/login", **request_part})
    with pytest.raises(JourneyError, match="literal value"):
        parse(doc)


@pytest.mark.parametrize("request_part", [
    {"json": {"passenger_name": "Ada", "passport": "X1", "token_type": "bearer",
              "cookie_consent": "yes", "bypass": "no"}},
    {"headers": {"Authorization": "Bearer {{env.TOKEN}}", "X-Api-Key": "{{env.KEY}}"}},
    {"headers": {"Authorization": "Basic {{env.BASIC}}"}},
])
def test_ordinary_fields_and_placeholder_secrets_are_allowed(request_part):
    parse(_step(0, request={"method": "POST", "path": "/api/login", **request_part}))


def test_load_dir_reports_bad_files_and_duplicate_names(tmp_path):
    (tmp_path / "a.yaml").write_text(json.dumps(CHECKOUT))
    (tmp_path / "b.yml").write_text(json.dumps(CHECKOUT))       # same name
    (tmp_path / "c.yaml").write_text("version: 1\nname: [oops\n")  # not YAML
    found, errors = load_dir(tmp_path)
    assert [j.name for j in found] == ["checkout", "checkout"]
    assert any("not valid YAML" in e for e in errors)
    assert any("already used" in e for e in errors)


def test_load_dir_missing_directory_is_empty(tmp_path):
    assert load_dir(tmp_path / "nope") == ([], [])


# --- templating -------------------------------------------------------------

def test_render_keeps_type_of_whole_placeholder():
    variables = {"id": 7, "token": "t1"}
    assert render({"cart": "{{id}}"}, variables, {}) == {"cart": 7}
    assert render("/carts/{{id}}/order", variables, {}) == "/carts/7/order"
    assert render("Bearer {{token}}", variables, {}) == "Bearer t1"
    assert render("{{env.PW}}", {}, {"PW": "s3cret"}) == "s3cret"


def test_render_missing_env_is_an_error():
    with pytest.raises(TemplateError, match="PW isn't set"):
        render("{{env.PW}}", {}, {})


# --- replaying once ----------------------------------------------------------

def _shop(order_status=201, cart_path="/api/cart"):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.path == "/api/login":
            body = json.loads(request.content)
            assert body["password"] == "pw" and body["email"].endswith("@example.com")
            return httpx.Response(200, json={"token": "t1"})
        assert request.headers["authorization"] == "Bearer t1"
        if request.url.path == cart_path:
            return httpx.Response(201, json={"id": 42})
        if request.url.path == "/api/carts/42/order":
            return httpx.Response(order_status, text="pool exhausted")
        return httpx.Response(404, json={"error": "not found"})

    return httpx.MockTransport(handler), seen


def _check(transport):
    return asyncio.run(check(parse(CHECKOUT), "http://shop.test/", env={"PW": "pw"},
                             transport=transport))


def test_check_replays_and_carries_extracted_values():
    transport, seen = _shop()
    result = _check(transport)
    assert result.ok and not result.stale
    assert [s.status for s in result.steps] == [200, 201, 201]
    assert str(seen[2].url) == "http://shop.test/api/carts/42/order"


def test_check_marks_a_changed_app_as_stale():
    transport, _ = _shop(cart_path="/api/basket")
    result = _check(transport)
    assert not result.ok and result.stale
    assert len(result.steps) == 2  # stops at the failing step
    assert result.failed.problem.startswith("returned 404, expected 200 or 201")


def test_check_without_expect_fails_on_4xx_and_5xx():
    transport, _ = _shop(order_status=500)
    result = _check(transport)
    # a 5xx with one user is the app failing, not a stale journey
    assert result.outcome == "error" and not result.stale
    assert result.failed.problem == "returned 500, expected a status below 400"
    assert result.failed.snippet == "pool exhausted"


def test_response_bodies_are_kept_apart_and_secrets_masked():
    import httpx as _httpx

    def echo(request):
        # validation errors often echo the input, secrets included
        return _httpx.Response(422, text=request.content.decode())

    result = asyncio.run(check(parse(CHECKOUT), "http://shop.test/",
                               env={"PW": "TopSecret123"},
                               transport=_httpx.MockTransport(echo)))
    assert result.stale
    assert "TopSecret123" not in result.failed.problem
    assert "TopSecret123" not in result.failed.snippet and "***" in result.failed.snippet


def test_check_unreachable_app_is_not_stale():
    def boom(request):
        raise httpx.ConnectError("refused")
    result = _check(httpx.MockTransport(boom))
    assert not result.ok and not result.stale
    assert result.failed.problem.startswith("couldn't reach the app")


def test_check_missing_extract_fails_the_step():
    def handler(request):
        return httpx.Response(200, json={"no_token": True})
    result = _check(httpx.MockTransport(handler))
    assert "couldn't find body.token" in result.failed.problem


def _one_step(path="/next", **request):
    return parse({"version": 1, "name": "j", "steps": [
        {"request": {"method": "GET", "path": "/start"}, "extract": {"next": "body.next"}},
        {"request": {"method": "POST", "path": path, **request}}]})


def test_rendered_path_cannot_change_host():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        if request.url.path == "/start":
            return httpx.Response(200, json={"next": "/evil.example/x", "pid": 1})
        return httpx.Response(200)

    j = _one_step(path="/{{next}}")
    result = asyncio.run(check(j, "http://shop.test", env={}, transport=httpx.MockTransport(handler)))
    assert seen == ["http://shop.test/start"]  # nothing sent off the app
    assert not result.ok and "single /" in result.failed.problem


def test_base_url_path_prefix_is_kept():
    seen = []

    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(200, json={"next": "x"})

    asyncio.run(check(_one_step(), "http://shop.test/app/", env={},
                      transport=httpx.MockTransport(handler)))
    assert seen == ["/app/start", "/app/next"]


def test_redirect_to_another_host_fails_the_step():
    seen = []

    def handler(request):
        seen.append(request.url.host)
        if request.url.path == "/start":
            return httpx.Response(200, json={"next": "x"})
        return httpx.Response(307, headers={"Location": "https://evil.example/steal"})

    result = asyncio.run(check(_one_step(), "http://shop.test", env={},
                               transport=httpx.MockTransport(handler)))
    assert "evil.example" not in seen
    assert not result.ok and "outside the app" in result.failed.problem


def test_extracted_number_in_a_header_is_sent_as_text():
    sent = {}

    def handler(request):
        if request.url.path == "/start":
            return httpx.Response(200, json={"next": 7})
        sent["x-id"] = request.headers["x-id"]
        return httpx.Response(200)

    result = asyncio.run(check(_one_step(headers={"X-Id": "{{next}}"}), "http://shop.test",
                               env={}, transport=httpx.MockTransport(handler)))
    assert result.ok and sent["x-id"] == "7"


# --- the command -------------------------------------------------------------

def _out(res):
    return " ".join(res.output.split())  # rich wraps long lines


def _write(tmp_path, doc=CHECKOUT, name="checkout.yaml"):
    (tmp_path / name).write_text(json.dumps(doc))
    return tmp_path


def test_journeys_lists_files(tmp_path):
    res = CliRunner().invoke(cli, ["journeys", "--dir", str(_write(tmp_path))])
    assert res.exit_code == 0, res.output
    assert "checkout" in res.output and "yes" in res.output


def test_verify_refuses_writes_on_a_non_local_host(tmp_path):
    res = CliRunner().invoke(cli, ["journeys", "verify", "https://shop.example.com",
                                   "--dir", str(_write(tmp_path))], env={"PW": "pw"})
    assert res.exit_code == 2
    assert "--allow-writes shop.example.com" in _out(res)


def test_verify_refuses_when_env_is_missing(tmp_path):
    res = CliRunner().invoke(cli, ["journeys", "verify", "http://localhost:1",
                                   "--dir", str(_write(tmp_path))], env={"PW": None})
    assert res.exit_code == 2
    assert "aren't set: PW" in _out(res)


def test_verify_reports_invalid_files(tmp_path):
    bad = _with(name="Bad Name")
    res = CliRunner().invoke(cli, ["journeys", "verify", "http://localhost:1",
                                   "--dir", str(_write(tmp_path, bad))])
    assert res.exit_code == 2
    assert "name must be lowercase" in _out(res)


def test_verify_prints_markup_like_names_safely(tmp_path):
    doc = {"version": 1, "name": "j", "steps": [
        {"name": "[/bold] oops", "request": {"method": "GET", "path": "/"}}]}
    res = CliRunner().invoke(cli, ["journeys", "verify", "http://127.0.0.1:9",
                                   "--dir", str(_write(tmp_path, doc))])
    assert res.exit_code == 1, res.output
    assert "[/bold] oops" in res.output


def test_verify_unknown_journey_name(tmp_path):
    res = CliRunner().invoke(cli, ["journeys", "verify", "http://localhost:1",
                                   "--dir", str(_write(tmp_path)), "--journey", "nope"],
                             env={"PW": "pw"})
    assert res.exit_code == 2
    assert "no journey named nope" in _out(res)
