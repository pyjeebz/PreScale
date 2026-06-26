"""Tests for the pure logic of the prescale audit checks."""

from prescale_cli.audit import (
    _asset_caching_finding,
    _asset_cookie_finding,
    _cdn_finding,
    _compression_finding,
    _http_version_finding,
    extract_assets,
)


def test_extract_assets_same_origin_only():
    html = """
    <link rel="stylesheet" href="/app.css">
    <script src="https://app.com/app.js"></script>
    <img src="/logo.png">
    <script src="https://cdn.other.com/x.js"></script>
    <img src="data:image/png;base64,AAAA">
    """
    assets = extract_assets(html, "https://app.com")
    assert assets == [
        "https://app.com/app.css",
        "https://app.com/app.js",
        "https://app.com/logo.png",
    ]


def test_compression_finding():
    assert _compression_finding("br").status == "pass"
    assert _compression_finding("gzip").status == "pass"
    assert _compression_finding(None).status == "warn"


def test_http_version_finding():
    assert _http_version_finding("HTTP/2").status == "pass"
    assert _http_version_finding("HTTP/1.1").status == "warn"
    assert _http_version_finding(None).status == "info"


def test_cdn_finding():
    assert _cdn_finding([{"cf-cache-status": "HIT"}]).status == "pass"
    assert _cdn_finding([{"server": "cloudflare"}]).status == "pass"
    assert _cdn_finding([{"content-type": "text/html"}]).status == "warn"


def test_asset_caching_finding():
    cached = [("https://a/x.css", {"cache-control": "max-age=31536000, immutable"})]
    assert _asset_caching_finding(cached).status == "pass"

    uncached = [("https://a/x.css", {"content-type": "text/css"})]
    assert _asset_caching_finding(uncached).status == "fail"

    mixed = [
        ("https://a/x.css", {"etag": "abc"}),
        ("https://a/y.js", {"content-type": "text/javascript"}),
    ]
    assert _asset_caching_finding(mixed).status == "warn"

    assert _asset_caching_finding([]).status == "info"


def test_asset_cookie_finding():
    assert _asset_cookie_finding([("https://a/x.css", {"set-cookie": "s=1"})]).status == "warn"
    assert _asset_cookie_finding([("https://a/x.css", {"etag": "z"})]).status == "pass"
