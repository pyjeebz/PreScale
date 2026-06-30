# Examples

## `fragile-shop.py` — a demo target that breaks under load

A tiny asyncio "shop" whose `/checkout` route draws from a 25-connection "DB
pool". Under load the pool exhausts and `/checkout` returns 500s, while the
static assets and the other routes stay fast — so PreScale has a real bottleneck
to find and diagnose.

```bash
python examples/fragile-shop.py 8400          # terminal 1 — the target
prescale investigate http://localhost:8400 \
    --path /search --path /product --path /checkout    # terminal 2
```

PreScale reports that `/checkout` breaks first, then diagnoses it as a
connection-pool ceiling and suggests raising the pool / adding pgbouncer. It's
the app behind the demo in the README. Tune the `Semaphore(25)` to move the
breaking point.
