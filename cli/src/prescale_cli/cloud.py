"""Opt-in bridge to the hosted PreScale app.

Nothing here runs unless the user asks for it (`prescale login`, `--upload`,
`prescale upload`). The only thing ever sent is a saved Result envelope, byte
for byte what's in `.prescale/runs/<id>.json`. `--header` values, request and
response bodies, and cookies never leave the machine.

Credentials live in `$XDG_CONFIG_HOME/prescale/credentials.json` (mode 0600).
`PRESCALE_TOKEN` / `PRESCALE_URL` override the file, for CI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

import httpx

from prescale_cli import __version__

DEFAULT_URL = "https://prescale.dev/dashboard"
TOKEN_PREFIX = "psk_"

_TIMEOUT = 15.0
_USER_AGENT = f"prescale-cli/{__version__}"


class CloudError(Exception):
    """A user-facing failure talking to the hosted app."""


@dataclass(frozen=True)
class Credentials:
    url: str
    token: str
    source: str  # "env" | "file"


def config_dir() -> Path:
    override = os.environ.get("PRESCALE_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "prescale"


def credentials_path() -> Path:
    return config_dir() / "credentials.json"


def normalize_url(url: str) -> str:
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def load_credentials() -> Credentials | None:
    """Env vars win (CI); otherwise the saved login; otherwise None."""
    env_token = os.environ.get("PRESCALE_TOKEN")
    if env_token:
        url = normalize_url(os.environ.get("PRESCALE_URL") or DEFAULT_URL)
        return Credentials(url=url, token=env_token.strip(), source="env")

    path = credentials_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return Credentials(url=normalize_url(data["url"]), token=data["token"], source="file")
    except (OSError, ValueError, KeyError, TypeError):
        raise CloudError(f"{path} is unreadable. Run `prescale login` again.") from None


def save_credentials(url: str, token: str) -> Path:
    path = credentials_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Create with 0600 from the start so the token is never world-readable.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump({"url": normalize_url(url), "token": token}, fh, indent=2)
        fh.write("\n")
    os.chmod(path, 0o600)
    return path


def clear_credentials() -> bool:
    path = credentials_path()
    if path.exists():
        path.unlink()
        return True
    return False


def upload_source() -> str:
    """Where this upload comes from, as shown in the app."""
    return "action" if os.environ.get("GITHUB_ACTIONS") == "true" else "cli"


def _client(creds: Credentials, transport: httpx.BaseTransport | None) -> httpx.Client:
    return httpx.Client(
        base_url=creds.url,
        timeout=_TIMEOUT,
        transport=transport,
        headers={
            "Authorization": f"Bearer {creds.token}",
            "User-Agent": _USER_AGENT,
            "X-PreScale-Source": upload_source(),
        },
    )


def _error_message(response: httpx.Response, creds: Credentials) -> str:
    try:
        detail = response.json().get("error")
    except ValueError:
        detail = None
    if response.status_code == 401:
        hints = {"env": " Check PRESCALE_TOKEN.", "file": " Run `prescale login` again."}
        hint = hints.get(creds.source, "")
        return f"{detail or 'The token was rejected.'}{hint}"
    return detail or f"{creds.url} returned HTTP {response.status_code}."


def _request(creds: Credentials, method: str, path: str, *, transport=None,
             **kwargs) -> dict:
    try:
        with _client(creds, transport) as client:
            response = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise CloudError(f"Couldn't reach {creds.url}: {exc}") from exc
    if response.status_code >= 400:
        raise CloudError(_error_message(response, creds))
    try:
        return response.json()
    except ValueError:
        raise CloudError(f"{creds.url} sent a response PreScale couldn't read.") from None


def whoami(creds: Credentials, *, transport=None) -> dict:
    """Validate a token. Returns `{"user": {...}, "token": {...}}`."""
    return _request(creds, "GET", "/api/v1/whoami", transport=transport)


def upload_result(result: dict, creds: Credentials, *, transport=None,
                  pr: int | None = None, target: str | None = None) -> dict:
    """POST a Result envelope. Idempotent on the Result id.

    `target` attaches the run to that PreScale target (a hostname) whatever URL
    was tested, for preview deploys that get a fresh URL each time. Returns
    `{"id", "url", "created", "comparison", "target": {...}}`.
    """
    headers = {"Content-Type": "application/json"}
    if pr is not None:
        headers["X-PreScale-PR"] = str(pr)
    if target:
        headers["X-PreScale-Target"] = target
    body = json.dumps(result).encode("utf-8")
    return _request(creds, "POST", "/api/v1/results", transport=transport,
                    content=body, headers=headers)


# --- browser sign-in (RFC 8628 device authorization) ------------------------

@dataclass(frozen=True)
class DeviceLogin:
    device_code: str
    user_code: str
    verification_url: str
    verification_url_complete: str
    expires_in: int
    interval: int


def _anonymous_post(url: str, path: str, body: dict, transport=None) -> httpx.Response:
    try:
        with httpx.Client(base_url=url, timeout=_TIMEOUT, transport=transport,
                          headers={"User-Agent": _USER_AGENT}) as client:
            return client.post(path, json=body)
    except httpx.HTTPError as exc:
        raise CloudError(f"Couldn't reach {url}: {exc}") from exc


def start_device_login(url: str, device_name: str, platform: str, *,
                       transport=None) -> DeviceLogin:
    """Ask the app for a login code to approve in the browser."""
    response = _anonymous_post(url, "/api/v1/auth/device",
                               {"device_name": device_name, "platform": platform}, transport)
    if response.status_code == 404:
        raise CloudError(f"{url} doesn't support browser sign-in yet. "
                         "Use `prescale login --paste` with a token from Connect.")
    try:
        data = response.json()
    except ValueError:
        raise CloudError(f"{url} sent a response PreScale couldn't read.") from None
    if response.status_code >= 400:
        raise CloudError(data.get("error") or f"{url} returned HTTP {response.status_code}.")
    try:
        return DeviceLogin(
            device_code=data["device_code"], user_code=data["user_code"],
            verification_url=data["verification_url"],
            verification_url_complete=data["verification_url_complete"],
            expires_in=int(data["expires_in"]), interval=int(data["interval"]),
        )
    except (KeyError, TypeError, ValueError):
        raise CloudError(f"{url} sent a login response PreScale couldn't read.") from None


def poll_device_login(url: str, device_code: str, *, transport=None) -> tuple[str, dict]:
    """One poll. Returns ("approved", {"token", "user"}) or (error_code, {"message"}).

    Error codes follow RFC 8628: authorization_pending, slow_down,
    access_denied, expired_token (plus invalid_grant for an unknown code).
    """
    response = _anonymous_post(url, "/api/v1/auth/device/token",
                               {"device_code": device_code}, transport)
    try:
        data = response.json()
    except ValueError:
        raise CloudError(f"{url} sent a response PreScale couldn't read.") from None
    if response.status_code == 200 and str(data.get("token", "")).startswith(TOKEN_PREFIX):
        return "approved", data
    if response.status_code == 400 and data.get("error"):
        return data["error"], data
    raise CloudError(data.get("message") or data.get("error")
                     or f"{url} returned HTTP {response.status_code}.")


def require_credentials() -> Credentials:
    creds = load_credentials()
    if creds is None:
        raise CloudError(
            "Not logged in. Run `prescale login` (or set PRESCALE_TOKEN in CI) to upload."
        )
    return creds


def parse_headers(values: tuple[str, ...]) -> dict[str, str]:
    """`--header "Name: value"` (repeatable) → dict. Raises ValueError on bad input."""
    headers: dict[str, str] = {}
    for raw in values:
        name, sep, value = raw.partition(":")
        name = name.strip()
        if not sep or not name or any(c.isspace() for c in name):
            raise ValueError(f"'{raw}' isn't a header. Use --header 'Name: value'.")
        headers[name] = value.strip()
    return headers
