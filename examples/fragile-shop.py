"""A deliberately fragile demo target for trying (and recording) PreScale.

A tiny asyncio "shop" where /checkout draws from a 25-connection "DB pool" and
holds each connection ~0.1s; under load the pool exhausts and /checkout returns
500s, while the static assets and the other routes stay fast. Point PreScale at
it to watch it find — and diagnose — a real bottleneck:

    python examples/fragile-shop.py 8400
    prescale investigate http://localhost:8400 --path /search --path /product --path /checkout
"""

import asyncio
import random
import sys

PAGE = (b"<!doctype html><html><head>"
        b'<link rel="stylesheet" href="/app.css">'
        b'<script src="/app.js"></script>'
        b"</head><body>acme.shop</body></html>")

_REASON = {200: "OK", 404: "Not Found", 500: "Internal Server Error"}


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
        path = parts[1].split("?")[0] if len(parts) >= 2 else "/"
        while True:                                      # drain request headers
            header = await reader.readline()
            if header in (b"\r\n", b"\n", b""):
                break

        if path == "/":
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


async def main(port):
    pool = asyncio.Semaphore(25)                              # 25 DB connections
    server = await asyncio.start_server(
        lambda r, w: _handle(r, w, pool), "127.0.0.1", port)
    print(f"fragile-shop listening on http://127.0.0.1:{port}  (Ctrl-C to stop)")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]) if len(sys.argv) > 1 else 8400))
