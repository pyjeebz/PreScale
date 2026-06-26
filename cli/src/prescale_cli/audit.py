"""Static scaling-hygiene audit for `prescale audit`.

Fetches a page and a few of its static assets and flags the HTTP-level footguns
that decide how a site handles traffic — compression, caching, CDN, HTTP
version, cookies on assets — in about a second, without generating load.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import httpx

from prescale_cli import __version__

_USER_AGENT = f"prescale/{__version__}"

# Response/header markers that reveal a CDN or edge cache in front of the origin.
_CDN_MARKERS = {
    "cf-cache-status": "Cloudflare",
    "x-vercel-cache": "Vercel",
    "x-amz-cf-id": "CloudFront",
    "x-served-by": "Fastly/Varnish",
    "x-fastly-request-id": "Fastly",
    "fly-request-id": "Fly",
    "x-cache": "edge cache",
}


class AuditError(Exception):
    """Raised when the target can't be reached at all."""


@dataclass
class Finding:
    name: str
    status: str  # "pass" | "warn" | "fail" | "info"
    detail: str
    fix: str | None = None


class _AssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        a = dict(attrs)
        rel = a.get("rel", "").lower()
        if tag == "link" and rel in ("stylesheet", "preload") and a.get("href"):
            self.urls.append(a["href"])
        elif tag == "script" and a.get("src"):
            self.urls.append(a["src"])
        elif tag == "img" and a.get("src"):
            self.urls.append(a["src"])


def extract_assets(html: str, base_url: str) -> list[str]:
    """Same-origin static asset URLs referenced by the page, de-duplicated."""
    parser = _AssetParser()
    try:
        parser.feed(html)
    except Exception:
        pass
    base = urlparse(base_url)
    origin = (base.scheme, base.netloc)
    out: list[str] = []
    seen: set[str] = set()
    for raw in parser.urls:
        full = urljoin(base_url, raw)
        parsed = urlparse(full)
        if parsed.scheme not in ("http", "https") or (parsed.scheme, parsed.netloc) != origin:
            continue
        if full not in seen:
            seen.add(full)
            out.append(full)
    return out


def _lower(headers) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()}


def _compression_finding(content_encoding: str | None) -> Finding:
    if content_encoding and any(
        e in content_encoding.lower() for e in ("gzip", "br", "deflate", "zstd")
    ):
        return Finding("Compression", "pass", f"Responses are compressed ({content_encoding}).")
    return Finding(
        "Compression", "warn", "Responses aren't compressed.",
        "Enable gzip or brotli at the server/CDN — smaller payloads, less bandwidth.",
    )


def _http_version_finding(version: str | None) -> Finding:
    if version is None:
        return Finding("HTTP version", "info", "Couldn't determine (install httpx[http2]).")
    if version.lower().startswith(("http/2", "http/3", "h2", "h3")):
        return Finding("HTTP version", "pass", f"Negotiated {version}.")
    return Finding(
        "HTTP version", "warn", f"Served over {version}.",
        "Enable HTTP/2 — better multiplexing and fewer connection limits under load.",
    )


def _cdn_finding(headers_list: list[dict[str, str]]) -> Finding:
    for headers in headers_list:
        for marker, label in _CDN_MARKERS.items():
            if marker in headers:
                return Finding("CDN / edge cache", "pass",
                               f"Detected ({label}: {headers[marker]}).")
        if "cloudflare" in headers.get("server", "").lower():
            return Finding("CDN / edge cache", "pass", "Detected (Cloudflare).")
    return Finding(
        "CDN / edge cache", "warn", "No CDN/edge-cache headers seen.",
        "Put a CDN in front so the origin doesn't serve every request.",
    )


def _asset_caching_finding(assets: list[tuple[str, dict[str, str]]]) -> Finding:
    if not assets:
        return Finding("Static asset caching", "info", "No static assets found to check.")
    uncached = []
    for url, headers in assets:
        cc = headers.get("cache-control", "").lower()
        cacheable = ("immutable" in cc) or (
            "max-age" in cc and not any(x in cc for x in ("no-store", "no-cache", "max-age=0"))
        )
        validator = "etag" in headers or "last-modified" in headers
        if not (cacheable or validator):
            uncached.append(url)
    if not uncached:
        return Finding("Static asset caching", "pass",
                       f"All {len(assets)} sampled assets are cacheable.")
    status = "fail" if len(uncached) == len(assets) else "warn"
    return Finding(
        "Static asset caching", status,
        f"{len(uncached)} of {len(assets)} sampled assets have no caching headers.",
        "Set Cache-Control: max-age (or an ETag) so clients and CDNs don't re-fetch them.",
    )


def _asset_cookie_finding(assets: list[tuple[str, dict[str, str]]]) -> Finding:
    if not assets:
        return Finding("Cookies on assets", "info", "No static assets found to check.")
    cookied = [url for url, headers in assets if "set-cookie" in headers]
    if not cookied:
        return Finding("Cookies on assets", "pass", "No cookies set on sampled static assets.")
    return Finding(
        "Cookies on assets", "warn", f"{len(cookied)} asset(s) set cookies.",
        "Don't set cookies on static assets — it defeats CDN and proxy caching.",
    )


def _baseline_finding(size_bytes: int, seconds: float) -> Finding:
    kb = size_bytes / 1024
    detail = f"HTML {kb:.0f} KB, responded in {seconds * 1000:.0f} ms."
    if kb > 1024:
        return Finding("Baseline", "warn", detail,
                       "Large HTML payload — trim, split, or stream it.")
    if seconds > 1.0:
        return Finding("Baseline", "warn", detail,
                       "Slow baseline response — investigate work on the main route.")
    return Finding("Baseline", "info", detail)


async def run_audit(url: str, *, timeout: float = 10.0, max_assets: int = 6) -> list[Finding]:
    """Fetch the page and a sample of its assets; return scaling-hygiene findings."""
    headers = {"User-Agent": _USER_AGENT, "Accept-Encoding": "gzip, deflate, br"}
    try:
        client = httpx.AsyncClient(http2=True, timeout=timeout,
                                   follow_redirects=True, headers=headers)
        http2_capable = True
    except ImportError:  # h2 not installed
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=headers)
        http2_capable = False

    async with client:
        start = time.perf_counter()
        try:
            resp = await client.get(url)
        except httpx.HTTPError as exc:
            raise AuditError(f"Couldn't reach {url}: {exc}") from exc
        elapsed = time.perf_counter() - start
        page_headers = _lower(resp.headers)

        asset_results: list[tuple[str, dict[str, str]]] = []
        for asset in extract_assets(resp.text, url)[:max_assets]:
            try:
                ar = await client.get(asset)
            except httpx.HTTPError:
                continue
            asset_results.append((asset, _lower(ar.headers)))

    all_headers = [page_headers] + [h for _, h in asset_results]
    return [
        _compression_finding(page_headers.get("content-encoding")),
        _http_version_finding(resp.http_version if http2_capable else None),
        _cdn_finding(all_headers),
        _asset_caching_finding(asset_results),
        _asset_cookie_finding(asset_results),
        _baseline_finding(len(resp.content), elapsed),
    ]
