"""A deliberately fragile demo target for trying (and recording) PreScale.

A tiny asyncio "shop" where /checkout draws from a 25-connection "DB pool" and
holds each connection ~0.1s; under load the pool exhausts and /checkout returns
500s, while the static assets and the other routes stay fast. Point PreScale at
it to watch it find — and diagnose — a real bottleneck:

    python examples/fragile-shop.py 8400
    prescale investigate http://localhost:8400 --path /search --path /product --path /checkout

It also has a small JSON API for journeys (log in, add to cart, place an order;
the order draws from the same pool), and a flash sale: buying a product locks that
product's stock row, so when everyone buys the mug they queue one at a time. The
journey files are in examples/journeys/:

    SHOP_PASSWORD=demo prescale journeys verify http://localhost:8400 --dir examples/journeys
"""

import asyncio
import itertools
import json
import random
import secrets
import sys

PAGE = (b"<!doctype html><html><head>"
        b'<link rel="stylesheet" href="/app.css">'
        b'<script src="/app.js"></script>'
        b"</head><body>acme.shop</body></html>")

_REASON = {200: "OK", 201: "Created", 400: "Bad Request", 401: "Unauthorized",
           404: "Not Found", 500: "Internal Server Error"}

PRODUCTS = [{"id": 1, "name": "mug"}, {"id": 2, "name": "tee"}, {"id": 3, "name": "cap"}]
_tokens: set[str] = set()
_carts: dict[int, str] = {}       # cart id -> owner token
_cart_ids = itertools.count(1)
# Each product's stock is one row, locked while a purchase checks and updates it:
# in a flash sale everyone buys the same product, so they queue on one lock.
_stock = {p["id"]: 10**9 for p in PRODUCTS}
_stock_locks: dict[int, asyncio.Lock] = {}


def _resp(code, body=b"ok", ctype="text/plain"):
    head = (f"HTTP/1.1 {code} {_REASON.get(code, 'OK')}\r\n"
            f"Server: gunicorn/21.2.0\r\n"
            f"Content-Type: {ctype}\r\n"
            f"Content-Length: {len(body)}\r\n"
            f"Connection: close\r\n\r\n").encode()
    return head + body


async def _handle(reader, writer, pool):
    try:
        line = await reader.readline()
        if not line:
            return
        parts = line.decode(errors="replace").split()
        method = parts[0] if parts else "GET"
        path = parts[1].split("?")[0] if len(parts) >= 2 else "/"
        headers = {}
        while True:                                      # read request headers
            header = await reader.readline()
            if header in (b"\r\n", b"\n", b""):
                break
            name, _, value = header.decode(errors="replace").partition(":")
            headers[name.strip().lower()] = value.strip()
        length = headers.get("content-length") or "0"
        if not length.isdigit():
            writer.write(_resp(400, b"bad Content-Length"))
            await writer.drain()
            return
        body = await reader.readexactly(int(length)) if int(length) else b""

        if path.startswith("/api/"):
            out = await _api(method, path, headers, body, pool)
        elif path == "/":
            await asyncio.sleep(0.005)
            out = _resp(200, PAGE, "text/html")
        elif path in ("/app.css", "/app.js"):
            out = _resp(200, b"/* static asset */")          # always fast
        elif path in ("/search", "/product"):
            await asyncio.sleep(random.uniform(0.005, 0.02))
            out = _resp(200)
        elif path == "/checkout":
            try:                                             # grab a DB connection
                await asyncio.wait_for(pool.acquire(), timeout=0.001)
            except asyncio.TimeoutError:
                out = _resp(500, b"could not acquire DB connection (pool exhausted)")
            else:
                try:
                    await asyncio.sleep(random.uniform(0.08, 0.12))
                    out = _resp(200, b"order placed")
                finally:
                    pool.release()
        else:
            out = _resp(404, b"not found")

        writer.write(out)
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
        except Exception:
            pass


def _json(code, data):
    return _resp(code, json.dumps(data).encode(), "application/json")


async def _api(method, path, headers, body, pool):
    """The shop's JSON API, used by the example journeys."""
    token = headers.get("authorization", "").removeprefix("Bearer ").strip()
    if method == "GET" and path == "/api/products":
        await asyncio.sleep(random.uniform(0.005, 0.02))
        return _json(200, PRODUCTS)
    if method == "POST" and path == "/api/login":
        try:
            creds = json.loads(body or b"{}")
        except ValueError:
            creds = None
        if not isinstance(creds, dict):
            return _json(400, {"error": "send a JSON object"})
        if not creds.get("email") or not creds.get("password"):
            return _json(401, {"error": "email and password required"})
        await asyncio.sleep(0.02)                            # password hashing
        new = secrets.token_hex(8)
        _tokens.add(new)
        return _json(200, {"token": new})
    if token not in _tokens:
        return _json(401, {"error": "log in first"})
    if method == "POST" and path == "/api/cart":
        cart = next(_cart_ids)
        _carts[cart] = token
        return _json(201, {"id": cart})
    if method == "POST" and path.startswith("/api/carts/") and path.endswith("/order"):
        cart = path.split("/")[3]
        if not cart.isdigit() or _carts.get(int(cart)) != token:
            return _json(404, {"error": "no such cart"})
        try:                                                 # grab a DB connection
            await asyncio.wait_for(pool.acquire(), timeout=0.001)
        except asyncio.TimeoutError:
            return _json(500, {"error": "could not acquire DB connection (pool exhausted)"})
        try:
            await asyncio.sleep(random.uniform(0.08, 0.12))
            return _json(201, {"order": f"o-{cart}"})
        finally:
            pool.release()
    if method == "POST" and path.startswith("/api/products/") and path.endswith("/buy"):
        product = path.split("/")[3]
        if not product.isdigit() or int(product) not in _stock:
            return _json(404, {"error": "no such product"})
        async with _stock_locks[int(product)]:               # SELECT ... FOR UPDATE
            await asyncio.sleep(random.uniform(0.035, 0.045))  # check stock, charge, write
            _stock[int(product)] -= 1
        return _json(201, {"bought": int(product)})
    return _json(404, {"error": "not found"})


async def main(port):
    pool = asyncio.Semaphore(25)                              # 25 DB connections
    _stock_locks.update({pid: asyncio.Lock() for pid in _stock})
    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, pool), "127.0.0.1", port)
    print(f"fragile-shop listening on http://127.0.0.1:{port}  (Ctrl-C to stop)")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8400))
