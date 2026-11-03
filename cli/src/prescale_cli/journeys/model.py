"""The journey file format (version 1), and the templating its steps use.

A journey file is YAML, one journey per file, committed to the app's repo:

    version: 1
    name: checkout
    type: checkout
    steps:
      - name: log in
        request: {method: POST, path: /api/login,
                  json: {email: "{{unique.email}}", password: "{{env.SHOP_PASSWORD}}"}}
        expect: {status: 200}
        extract: {token: body.token}
      - name: place order
        request: {method: POST, path: /api/orders,
                  headers: {Authorization: "Bearer {{token}}"}}
        expect: {status: [200, 201]}

Placeholders: `{{name}}` is a value an earlier step extracted; `{{unique.email}}`
and `{{unique.id}}` are fresh for each run of the journey; `{{env.NAME}}` reads an
environment variable, which is how secrets stay out of the file. Everything here
is pure: loading never touches the network.
"""

from __future__ import annotations

import json
import math
import re
import secrets
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlsplit

import yaml

FORMAT_VERSION = 1
DEFAULT_DIR = Path("prescale") / "journeys"

# Journey types PreScale replays, and each one's default share of the traffic mix.
TYPES: dict[str, int] = {
    "browse": 60, "search": 25, "account": 8, "checkout": 5, "write": 5, "auth": 2,
}
# Types PreScale never replays: they message real people or destroy data.
REFUSED_TYPES = {
    "side_effect": "it sends email, SMS or invites to real people",
    "destructive": "it deletes data or changes admin settings",
}
METHODS = {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}

_PLACEHOLDER = re.compile(r"\{\{\s*([A-Za-z_][\w.]*)\s*\}\}")
# A key is secret-looking when it is, or ends with, one of these words:
# password, client_secret, x-api-key, access_token, Authorization, Cookie.
SENSITIVE_KEY = re.compile(
    r"(^|[-_.])(password|passwd|pwd|secret|token|api[-_]?key|authorization|cookie)$",
    re.IGNORECASE)
# The secret itself must be a placeholder, optionally after an auth scheme.
_SECRET_OK = re.compile(r"((Bearer|Basic|Token)\s+)?\{\{\s*[A-Za-z_][\w.]*\s*\}\}",
                        re.IGNORECASE)
_UNIQUE = {"email", "id"}
_SOURCES = ("body", "header")


class JourneyError(Exception):
    """A journey file that can't be used, with a message that says how to fix it."""


@dataclass
class Step:
    name: str
    method: str
    path: str
    headers: dict[str, str] = field(default_factory=dict)
    json: Any = None
    body: str | None = None
    expect: list[int] | None = None   # None: any status below 400
    extract: dict[str, str] = field(default_factory=dict)
    think: float = 0.0

    @property
    def label(self) -> str:
        """The route as reports show it: method plus path, placeholders kept."""
        return f"{self.method} {self.path.split('?')[0]}"

    def accepts(self, status: int) -> bool:
        if self.expect is None:
            return status < 400
        return status in self.expect


@dataclass
class Journey:
    name: str
    type: str
    weight: float
    steps: list[Step]
    source: Path | None = None

    @property
    def writes(self) -> bool:
        """Whether replaying it can change data on the target."""
        return any(step.method not in READ_METHODS for step in self.steps)

    def env_names(self) -> set[str]:
        """Environment variables its steps read."""
        return {name[4:] for step in self.steps for name in _names(_step_values(step))
                if name.startswith("env.")}


# --- loading --------------------------------------------------------------

def load_dir(directory: Path = DEFAULT_DIR) -> tuple[list[Journey], list[str]]:
    """Every journey in DIRECTORY, sorted by name, plus one error message per file
    that couldn't be loaded. A missing directory is no journeys, not an error."""
    if not directory.is_dir():
        return [], []
    journeys: list[Journey] = []
    errors: list[str] = []
    for path in sorted([*directory.glob("*.yaml"), *directory.glob("*.yml")]):
        try:
            journeys.append(load_file(path))
        except JourneyError as exc:
            errors.append(f"{path}: {exc}")
    seen: dict[str, Path] = {}
    for journey in journeys:
        if journey.name in seen:
            errors.append(f"{journey.source}: the name '{journey.name}' is already used by "
                          f"{seen[journey.name]}")
        seen.setdefault(journey.name, journey.source)
    return sorted(journeys, key=lambda j: j.name), errors


def load_file(path: Path) -> Journey:
    try:
        data = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        raise JourneyError(f"not valid YAML ({exc})") from exc
    journey = parse(data)
    journey.source = path
    return journey


def parse(data: Any) -> Journey:
    """Check a decoded journey document and build a `Journey`."""
    if not isinstance(data, dict):
        raise JourneyError("a journey file must be a mapping with version, name and steps")
    _only(data, {"version", "name", "type", "weight", "steps"}, "the journey")
    if data.get("version") != FORMAT_VERSION:
        raise JourneyError(f"version must be {FORMAT_VERSION} (got {data.get('version')!r})")
    name = data.get("name")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]*", name):
        raise JourneyError("name must be lowercase letters, digits, - or _ (e.g. checkout)")
    jtype = data.get("type", "browse")
    if jtype in REFUSED_TYPES:
        raise JourneyError(f"type '{jtype}' is never replayed: {REFUSED_TYPES[jtype]}")
    if jtype not in TYPES:
        raise JourneyError(f"type must be one of {', '.join(TYPES)} (got {jtype!r})")
    weight = data.get("weight", TYPES[jtype])
    if isinstance(weight, bool) or not isinstance(weight, (int, float)) \
            or not math.isfinite(weight) or weight <= 0:
        raise JourneyError("weight must be a positive number")
    raw_steps = data.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise JourneyError("steps must be a non-empty list")

    steps = [_parse_step(raw, i) for i, raw in enumerate(raw_steps, 1)]
    _check_placeholders(steps)
    return Journey(name=name, type=jtype, weight=float(weight), steps=steps)


def _parse_step(raw: Any, index: int) -> Step:
    where = f"step {index}"
    if not isinstance(raw, dict):
        raise JourneyError(f"{where} must be a mapping with name and request")
    _only(raw, {"name", "request", "expect", "extract", "think"}, where)
    name = raw.get("name") or f"step {index}"
    if not isinstance(name, str):
        raise JourneyError(f"{where}: name must be text")
    if raw.get("name"):
        where = f"step {index} ({name})"

    request = raw.get("request")
    if not isinstance(request, dict):
        raise JourneyError(f"{where}: request must be a mapping with method and path")
    _only(request, {"method", "path", "headers", "json", "body"}, f"{where} request")
    method = str(request.get("method", "GET")).upper()
    if method not in METHODS:
        raise JourneyError(f"{where}: method {method} isn't supported")
    path = request.get("path")
    if not isinstance(path, str) or not path.startswith("/") or path.startswith(("//", "/\\")):
        raise JourneyError(f"{where}: path must start with a single / (it's relative to the "
                           "URL the journey runs against, and never reaches another site)")
    headers = request.get("headers") or {}
    if not isinstance(headers, dict) or not all(isinstance(v, str) for v in headers.values()):
        raise JourneyError(f"{where}: headers must map names to text")
    if "json" in request and "body" in request:
        raise JourneyError(f"{where}: give either json or body, not both")
    body = request.get("body")
    if body is not None and not isinstance(body, str):
        raise JourneyError(f"{where}: body must be text (use json for structured data)")
    _check_secrets({"headers": headers, "json": request.get("json"),
                    "query": dict(parse_qsl(urlsplit(path).query)),
                    "body": _decode_body(body)}, where)

    return Step(
        name=name, method=method, path=path,
        headers={str(k): v for k, v in headers.items()},
        json=request.get("json"), body=body,
        expect=_parse_expect(raw.get("expect"), where),
        extract=_parse_extract(raw.get("extract"), where),
        think=_parse_seconds(raw.get("think", 0), where),
    )


def _parse_expect(raw: Any, where: str) -> list[int] | None:
    if raw is None:
        return None
    if not isinstance(raw, dict) or set(raw) != {"status"}:
        raise JourneyError(f"{where}: expect must be {{status: 200}} or {{status: [200, 201]}}")
    status = raw["status"]
    codes = status if isinstance(status, list) else [status]
    if not codes or not all(isinstance(c, int) and 100 <= c <= 599 for c in codes):
        raise JourneyError(f"{where}: expect status must be HTTP status codes")
    return codes


def _parse_extract(raw: Any, where: str) -> dict[str, str]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise JourneyError(f"{where}: extract must map names to body.<field> or header.<name>")
    for name, source in raw.items():
        if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z_]\w*", name) \
                or name in {"env", "unique"}:
            raise JourneyError(f"{where}: can't extract into {name!r}")
        if not isinstance(source, str) or source.split(".", 1)[0] not in _SOURCES \
                or "." not in source:
            raise JourneyError(f"{where}: extract {name} must come from body.<field> "
                               "or header.<name>")
    return dict(raw)


def _parse_seconds(raw: Any, where: str) -> float:
    if isinstance(raw, bool):
        raise JourneyError(f"{where}: think must be seconds, e.g. 2 or 2s or 500ms")
    if isinstance(raw, (int, float)) and raw >= 0:
        return float(raw)
    match = re.fullmatch(r"(\d+(?:\.\d+)?)(ms|s)", str(raw).strip())
    if not match:
        raise JourneyError(f"{where}: think must be seconds, e.g. 2 or 2s or 500ms")
    value = float(match.group(1))
    return value / 1000 if match.group(2) == "ms" else value


def _only(data: dict, allowed: set[str], where: str) -> None:
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise JourneyError(f"{where} has unknown field(s): {', '.join(map(str, unknown))}")


def _decode_body(body: str | None) -> Any:
    """A string body as data, so secrets in it are checked too (JSON or a form)."""
    if not body:
        return None
    try:
        return json.loads(body)
    except ValueError:
        return dict(parse_qsl(body))


def _check_secrets(value: Any, where: str, key: str = "") -> None:
    """Refuse a literal value under a secret-looking key: secrets come from {{env.*}}
    (or an earlier step's extract), so they never end up committed in the file."""
    if isinstance(value, dict):
        for k, v in value.items():
            _check_secrets(v, where, str(k))
    elif isinstance(value, list):
        for v in value:
            _check_secrets(v, where, key)
    elif value is not None and key and SENSITIVE_KEY.search(key) \
            and not (isinstance(value, str) and _SECRET_OK.fullmatch(value.strip())):
        raise JourneyError(f"{where}: {key} has a literal value. Put secrets in an "
                           f"environment variable and write \"{{{{env.NAME}}}}\" instead")


def _check_placeholders(steps: list[Step]) -> None:
    """Every {{name}} must be extracted by an earlier step, or be env./unique."""
    known: set[str] = set()
    for i, step in enumerate(steps, 1):
        for name in _names(_step_values(step)):
            if name.startswith("env."):
                continue
            if name.startswith("unique."):
                if name[7:] not in _UNIQUE:
                    raise JourneyError(f"step {i} ({step.name}): {{{{{name}}}}} isn't known; "
                                       "use unique.email or unique.id")
                continue
            if name not in known:
                raise JourneyError(f"step {i} ({step.name}) uses {{{{{name}}}}}, but no "
                                   "earlier step extracts it")
        known.update(step.extract)


def _step_values(step: Step) -> list[Any]:
    return [step.path, step.headers, step.json, step.body]


def _names(value: Any) -> list[str]:
    if isinstance(value, str):
        return _PLACEHOLDER.findall(value)
    if isinstance(value, dict):
        return [n for k, v in value.items() for n in (*_names(k), *_names(v))]
    if isinstance(value, list):
        return [n for v in value for n in _names(v)]
    return []


# --- templating -----------------------------------------------------------

class TemplateError(Exception):
    """A placeholder with no value at replay time (e.g. an unset env variable)."""


def fresh_uniques() -> dict[str, str]:
    """Values for {{unique.*}}, new for each run of a journey."""
    token = secrets.token_hex(6)
    # example.com is reserved for examples (RFC 2606): mail to it goes nowhere.
    return {"unique.email": f"prescale+{token}@example.com", "unique.id": token}


def render(value: Any, variables: dict[str, Any], env: dict[str, str]) -> Any:
    """Fill placeholders in a step value. A string that is exactly one placeholder
    keeps the value's type (an extracted id stays a number in JSON)."""
    if isinstance(value, str):
        whole = _PLACEHOLDER.fullmatch(value.strip())
        if whole:
            return _lookup(whole.group(1), variables, env)
        return _PLACEHOLDER.sub(lambda m: str(_lookup(m.group(1), variables, env)), value)
    if isinstance(value, dict):
        return {render(k, variables, env): render(v, variables, env) for k, v in value.items()}
    if isinstance(value, list):
        return [render(v, variables, env) for v in value]
    return value


def _lookup(name: str, variables: dict[str, Any], env: dict[str, str]) -> Any:
    if name.startswith("env."):
        if name[4:] not in env:
            raise TemplateError(f"environment variable {name[4:]} isn't set")
        return env[name[4:]]
    if name not in variables:
        raise TemplateError(f"{{{{{name}}}}} has no value")
    return variables[name]
