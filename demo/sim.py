#!/usr/bin/env python3
"""Staged reproduction of a `prescale investigate` run, for the landing-page hero.

This is a *scripted* representation of the real tool's output (wording, table, and
Diagnosis mirror prescale_cli.render / .investigate) — staged so the video can show
the telemetry table, then errors creeping in on /checkout, then the Diagnosis.
It clears nothing: the typed command and ramp stay on screen the whole time.

Run under asciinema:  asciinema rec -c "python3 -u demo/sim.py" demo.cast
"""
import sys
import time

# ── brand palette (truecolor; bg comes from the agg theme) ───────────────────
CREAM = "\x1b[38;2;231;227;216m"   # #e7e3d8 text
VERM  = "\x1b[38;2;227;83;53m"     # #e35335 accent / errors / high-confidence
MUTE  = "\x1b[38;2;143;140;131m"   # #8f8c83 muted
GREEN = "\x1b[38;2;125;150;110m"   # healthy 0%
BOLD  = "\x1b[1m"
R     = "\x1b[0m"

# ── pacing (seconds) ─────────────────────────────────────────────────────────
CPS        = 0.048   # per keystroke
RAMP_STEP  = 0.09    # spinner frame
WAIT       = 1.0     # the two deliberate beats
CREEP_STEP = 0.18    # per error-climb frame
HOLD       = 4.0     # final held screen

CMD = ("prescale investigate http://localhost:8400 "
       "--path /search --path /product --path /checkout")


def w(s):
    sys.stdout.write(s)
    sys.stdout.flush()


def type_out(s, cps=CPS):
    for ch in s:
        w(ch)
        time.sleep(cps)


# ── telemetry table (mirrors render._render_routes: Route | Req/s | p95 | Errors)
def hrule(l, m, r):
    return CREAM + l + "─" * 11 + m + "─" * 7 + m + "─" * 7 + m + "─" * 8 + r + R


def header():
    c = CREAM
    return (c + "│ " + BOLD + f"{'Route':<9}" + R + c + " │ " + BOLD + f"{'Req/s':>5}" + R
            + c + " │ " + BOLD + f"{'p95':>5}" + R + c + " │ " + BOLD + f"{'Errors':>6}" + R
            + c + " │" + R)


def row(route, rps, p95, err, color):
    c = CREAM
    return (c + "│ " + color + f"{route:<9}" + c + " │ " + color + f"{rps:>5}" + c
            + " │ " + color + f"{p95:>5}" + c + " │ " + color + f"{err:>6}" + c + " │" + R)


def title_line():
    t = "Per route @ 150 users"
    return CREAM + " " * ((38 - len(t)) // 2) + BOLD + t + R


# ── Diagnosis panel (mirrors render.render_investigation, high-confidence => red)
PW = 120                       # panel width in cells
INNER = PW - 2                 # between the ╭ ╮
PAD = PW - 4                   # content width (1 space padding each side)


def ptop():
    t = " 🔬 Diagnosis "       # 🔬 counts as 2 cells -> 14 visible
    left = (INNER - 14) // 2
    return VERM + "╭" + "─" * left + t + "─" * (INNER - 14 - left) + "╮" + R


def pbot():
    return VERM + "╰" + "─" * INNER + "╯" + R


def pline(plain, styled=None):
    styled = CREAM + plain + R if styled is None else styled
    return VERM + "│" + R + " " + styled + " " * max(0, PAD - len(plain)) + " " + VERM + "│" + R


def main():
    time.sleep(0.6)
    w(VERM + "❯ " + CREAM)
    type_out(CMD)
    time.sleep(0.35)
    w("\n")

    # ramping load spinner, 10 -> 200
    frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    for c in (10, 20, 50, 100, 150, 200):
        for _ in range(6):
            w("\r" + VERM + frames[i % len(frames)] + " " + CREAM
              + f"Ramping load — {c} virtual users…" + "      " + R)
            i += 1
            time.sleep(RAMP_STEP)
    w("\r" + VERM + "✓ " + CREAM + "Ramped to 200 virtual users"
      + " " * 18 + R + "\n")

    # telemetry table — healthy at first
    print()
    print(title_line())
    print(hrule("┌", "┬", "┐"))
    print(header())
    print(hrule("├", "┼", "┤"))
    print(row("/checkout", 156, "300ms", "0%", GREEN))
    print(row("/product", 156, "256ms", "0%", GREEN))
    print(row("/search", 156, "252ms", "0%", GREEN))
    print(row("/", 157, "230ms", "0%", GREEN))
    print(hrule("└", "┴", "┘"))
    sys.stdout.flush()

    time.sleep(WAIT)

    # errors creep in on /checkout — rewrite that row in place (no screen clear)
    w("\x1b7")                                  # save cursor (below the table)
    for p95, e in [(316, 5), (332, 11), (350, 18), (365, 24), (378, 29), (385, 31)]:
        color = VERM + BOLD if e else GREEN
        w("\x1b8")                              # back to below the table
        w("\x1b[5A\r")                          # up to the /checkout row
        w(row("/checkout", 156, f"{p95}ms", f"{e}%", color))
        w("\x1b8")                              # leave cursor below the table
        time.sleep(CREEP_STEP)

    time.sleep(WAIT)

    # the Diagnosis
    summary = ("5xx under load while static assets held — the app/backend is the "
               "wall (often a DB or upstream pool).")
    print()
    print(ptop())
    print(pline("Likely cause: " + summary,
                BOLD + "Likely cause:" + R + CREAM + " " + summary + R))
    print(pline("Bottleneck  connection_pool (high confidence)  ·  culprit /checkout",
                CREAM + "Bottleneck  " + BOLD + "connection_pool" + R + CREAM + " ("
                + VERM + "high confidence" + CREAM + ")  ·  culprit /checkout" + R))
    print(pline(""))
    print(pline("Evidence", BOLD + "Evidence" + R))
    for e in ("culprit p95 118ms at 1 user vs 385ms at 150 users",
              "static /app.css held at 150 users",
              "errors under load: 5xx (57)",
              "server: gunicorn/21.2.0"):
        print(pline("  • " + e))
    print(pline(""))
    print(pline("Try this", BOLD + "Try this" + R))
    for rec in ("Increase the DB/upstream connection-pool size.",
                "Add a pooler (e.g. pgbouncer) and check the pool checkout timeout.",
                "Make sure connections are released promptly under load (no leaks).",
                "gunicorn detected — increase --workers (and/or --threads)."):
        print(pline("  → " + rec))
    print(pbot())
    sys.stdout.flush()

    time.sleep(HOLD)
    w(R)          # final no-op event so the hold is recorded


if __name__ == "__main__":
    main()
