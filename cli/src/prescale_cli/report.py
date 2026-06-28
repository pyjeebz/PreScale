"""Self-contained HTML readiness report for `prescale run --html` and `show`.

Linear-styled (dark canvas, lavender accent, hairline borders), built from a
Result with no external dependencies — inline CSS, system font stack, an
inline-SVG chart. One file you can open offline, email, or attach to a PR.
"""

from __future__ import annotations

import html
from datetime import datetime

_CSS = """
:root{
  --canvas:#010102;--s1:#0f1011;--s2:#141516;--hair:#23252a;
  --ink:#f7f8f8;--muted:#d0d6e0;--subtle:#8a8f98;--tertiary:#62666d;
  --accent:#5e6ad2;--green:#3fbf5f;--amber:#f2994a;--red:#eb5757;
  --amber-bg:rgba(242,153,74,.12);--red-bg:rgba(235,87,87,.09);--green-bg:rgba(39,166,68,.12);
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,'SF Pro Display',
    system-ui,sans-serif;
  --mono:ui-monospace,'SF Mono','JetBrains Mono',Menlo,Consolas,monospace;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--canvas);color:var(--ink);font-family:var(--sans);
  -webkit-font-smoothing:antialiased;line-height:1.5;letter-spacing:-.05px;}
.wrap{max-width:880px;margin:0 auto;padding:40px 24px 64px;}
.panel{background:var(--s1);border:1px solid var(--hair);border-radius:12px;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.04);}
.topbar{display:flex;align-items:center;justify-content:space-between;height:56px;
  border-bottom:1px solid var(--hair);margin-bottom:40px;}
.brand{display:flex;align-items:center;gap:9px;font-weight:600;font-size:15px;letter-spacing:-.3px;}
.brand .mark{width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;
  border-bottom:14px solid var(--accent);}
.topbar .meta{font-family:var(--mono);font-size:12px;color:var(--tertiary);}
h1{font-size:30px;font-weight:600;letter-spacing:-.8px;}
.sub{margin-top:9px;display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:13px;color:var(--subtle);}
.sub .url{font-family:var(--mono);color:var(--muted);background:var(--s1);
  border:1px solid var(--hair);border-radius:6px;padding:3px 9px;font-size:12px;}
.verdict{margin-top:26px;padding:24px 26px;display:flex;align-items:center;gap:20px;}
.dot{width:9px;height:9px;border-radius:50%;background:var(--amber);
  box-shadow:0 0 0 4px rgba(242,153,74,.14);flex:none;}
.dot.green{background:var(--green);box-shadow:0 0 0 4px rgba(63,191,95,.14);}
.dot.red{background:var(--red);box-shadow:0 0 0 4px rgba(235,87,87,.14);}
.verdict h2{font-size:21px;font-weight:600;letter-spacing:-.4px;}
.verdict p{margin-top:4px;color:var(--subtle);font-size:13.5px;}
.pill{margin-left:auto;flex:none;font-size:11px;font-weight:500;letter-spacing:.3px;
  color:var(--amber);background:var(--amber-bg);border:1px solid rgba(242,153,74,.25);
  border-radius:9999px;padding:4px 11px;}
.pill.green{color:var(--green);background:var(--green-bg);border-color:rgba(63,191,95,.3);}
.pill.red{color:var(--red);background:var(--red-bg);border-color:rgba(235,87,87,.3);}
.grid{margin-top:14px;display:grid;grid-template-columns:repeat(4,1fr);gap:12px;}
.stat{padding:16px 16px 18px;}
.stat .k{font-size:12px;color:var(--subtle);font-weight:500;}
.stat .v{margin-top:12px;font-family:var(--mono);font-size:23px;font-weight:500;
  letter-spacing:-.5px;}
.stat .u{font-size:12px;color:var(--subtle);margin-left:3px;font-family:var(--sans);}
.section{margin-top:36px;}
.section h3{font-size:12px;font-weight:500;color:var(--subtle);text-transform:uppercase;
  letter-spacing:.5px;margin-bottom:14px;}
.clip{overflow:hidden;}
.chart{padding:20px 22px 8px;}
.chart .legend{display:flex;gap:16px;font-size:12px;color:var(--subtle);margin-bottom:6px;}
.chart .legend b{color:var(--ink);font-family:var(--mono);font-weight:500;}
svg{display:block;width:100%;height:auto;}
table{width:100%;border-collapse:collapse;font-size:13px;}
thead th{text-align:right;font-weight:500;color:var(--subtle);font-size:11.5px;
  text-transform:uppercase;letter-spacing:.4px;padding:11px 18px;
  border-top:1px solid var(--hair);background:var(--s2);}
thead th:first-child{text-align:left;}
tbody td{text-align:right;padding:11px 18px;border-top:1px solid var(--hair);
  font-family:var(--mono);font-size:12.5px;color:var(--muted);}
tbody td:first-child{text-align:left;font-weight:500;color:var(--ink);}
tbody tr.onset td{background:var(--red-bg);color:var(--red);}
tbody tr.onset td:first-child{color:var(--red);}
tbody tr.onset td:first-child::after{content:"  ←  breaks here";color:var(--red);
  font-family:var(--sans);font-size:11px;font-weight:500;letter-spacing:0;}
.ok{color:var(--green);}
.cause{margin-top:14px;background:var(--s2);border:1px solid var(--hair);
  border-left:2px solid var(--amber);border-radius:10px;padding:16px 18px;}
.cause .lbl{font-size:11px;font-weight:500;text-transform:uppercase;letter-spacing:.5px;
  color:var(--amber);margin-bottom:6px;}
.cause p{font-size:13.5px;color:var(--muted);}
.cause p+p{margin-top:8px;}
.cause b{color:var(--ink);}
footer{margin-top:44px;padding-top:20px;border-top:1px solid var(--hair);display:flex;
  justify-content:space-between;font-family:var(--mono);font-size:11.5px;color:var(--tertiary);}
"""

MIDDOT = "·"
RARROW = "→"


def _esc(text: str) -> str:
    return html.escape(str(text), quote=True)


def _ms(ms: float) -> str:
    return "-" if ms <= 0 else f"{ms:.0f}ms"


def _err_td(rate: float) -> str:
    return '<td class="ok">0%</td>' if rate == 0 else f"<td>{rate:.0%}</td>"


def _svg_chart(result: dict) -> str:
    stages = result["stages"]
    verdict = result["verdict"]
    latency_wall = result["config"]["latency_wall_s"]
    onset_users = verdict["onset_users"]
    survives_users = verdict["survives_users"]
    pts = [(s["users"], s["p95_ms"] / 1000.0) for s in stages]
    if not pts:
        return ""
    w, h, pl, pr, pb = 600, 180, 40, 40, 24
    pt = 24
    ymax = max(max(v for _, v in pts), latency_wall * 1.2) or 1.0
    n = len(pts)
    plot_w, plot_h = w - pl - pr, h - pt - pb

    def x(i: int) -> float:
        return pl + (plot_w * (i / (n - 1) if n > 1 else 0))

    def y(v: float) -> float:
        return h - pb - (v / ymax) * plot_h

    poly = " ".join(f"{x(i):.0f},{y(v):.0f}" for i, (_, v) in enumerate(pts))
    wall_y = y(latency_wall)
    dots, labels = [], []
    for i, (users, v) in enumerate(pts):
        if users == onset_users:
            color, lc, r = "#eb5757", "#eb5757", 4
        elif users == survives_users and onset_users is not None:
            color, lc, r = "#27a644", "#3fbf5f", 3.5
        else:
            color, lc, r = "#5e6ad2", "#62666d", 3
        edge = ' stroke="#010102" stroke-width="1.5"' if color != "#5e6ad2" else ""
        dots.append(f'<circle cx="{x(i):.0f}" cy="{y(v):.0f}" r="{r}" fill="{color}"{edge}/>')
        labels.append(
            f'<text x="{x(i):.0f}" y="{h - 8}" font-family="monospace" font-size="10" '
            f'fill="{lc}" text-anchor="middle">{users}</text>'
        )
    return (
        f'<svg viewBox="0 0 {w} {h}" preserveAspectRatio="none">'
        f'<line x1="{pl}" y1="{wall_y:.0f}" x2="{w - pr}" y2="{wall_y:.0f}" stroke="#eb5757" '
        f'stroke-width="1" stroke-dasharray="4 4" opacity=".55"/>'
        f'<text x="{pl + 4}" y="{wall_y - 4:.0f}" font-family="monospace" font-size="9" '
        f'fill="#eb5757">latency wall {MIDDOT} {latency_wall:g}s</text>'
        f'<line x1="{pl}" y1="{h - pb}" x2="{w - pr}" y2="{h - pb}" '
        f'stroke="#23252a" stroke-width="1"/>'
        f'<polyline points="{poly}" fill="none" stroke="#5e6ad2" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'{"".join(dots)}{"".join(labels)}</svg>'
    )


def _verdict(result: dict) -> tuple[str, str, str, str]:
    v = result["verdict"]
    if v["onset_users"] is None:
        return ("green", "READY",
                f"Held up through {v['max_tested']} concurrent users",
                "No failures up to the most we tested.")
    if v["survives_users"] == 0:
        return ("red", "AT RISK",
                f"Struggles from ~{v['onset_users']} concurrent users",
                "It buckles almost immediately under load.")
    return ("amber", "NEEDS ATTENTION",
            f"Survives ~{v['survives_users']} concurrent users",
            f"First failure at ~{v['onset_users']} users.")


def _stats(result: dict) -> str:
    v = result["verdict"]
    stages = result["stages"]
    onset_users = v["onset_users"]
    onset = onset_users is not None
    survives = v["survives_users"] if onset else v["max_tested"]
    onset_stage = next((s for s in stages if s["users"] == onset_users), None)
    wall_ms = onset_stage["p95_ms"] if onset_stage else max(
        (s["p95_ms"] for s in stages), default=0)
    p95_val = f"{wall_ms / 1000:.1f}" if wall_ms >= 1000 else f"{wall_ms:.0f}"
    p95_unit = "s" if wall_ms >= 1000 else "ms"
    cards = [
        ("Survives", str(survives), "users"),
        ("Peak throughput", f"{v['peak_rps']:.0f}", "req/s"),
        ("Breaks at", str(onset_users) if onset else "none", "users" if onset else ""),
        ("p95 at the wall" if onset else "Peak p95", p95_val, p95_unit),
    ]
    return "".join(
        f'<div class="panel stat"><div class="k">{k}</div>'
        f'<div class="v">{val}<span class="u">{u}</span></div></div>'
        for k, val, u in cards
    )


def _ramp_table(result: dict) -> str:
    onset_users = result["verdict"]["onset_users"]
    rows = []
    for s in result["stages"]:
        cls = ' class="onset"' if s["users"] == onset_users else ""
        rows.append(
            f"<tr{cls}><td>{s['users']}</td><td>{s['rps']:.0f}</td>"
            f"<td>{_ms(s['p50_ms'])}</td><td>{_ms(s['p95_ms'])}</td>"
            f"<td>{_ms(s['p99_ms'])}</td>{_err_td(s['error_rate'])}</tr>"
        )
    return (
        "<table><thead><tr><th>Users</th><th>Req/s</th><th>p50</th><th>p95</th>"
        "<th>p99</th><th>Errors</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def _route_table(result: dict) -> str:
    v = result["verdict"]
    stages = result["stages"]
    if not stages:
        return ""
    decisive = next((s for s in stages if s["users"] == v["onset_users"]), stages[-1])
    routes = decisive["routes"]
    if len(routes) <= 1:
        return ""
    ranked = sorted(routes.items(),
                    key=lambda kv: (kv[1]["error_rate"], kv[1]["p95_ms"]), reverse=True)
    rows = []
    for label, stat in ranked:
        cls = ' class="onset"' if label == v["culprit_route"] else ""
        rows.append(
            f"<tr{cls}><td>{_esc(label)}</td><td>{stat['rps']:.0f}</td>"
            f"<td>{_ms(stat['p95_ms'])}</td>{_err_td(stat['error_rate'])}</tr>"
        )
    return (
        f'<div class="section"><h3>Per route {MIDDOT} at {decisive["users"]} users</h3>'
        '<div class="panel clip"><table><thead><tr><th>Route</th><th>Req/s</th>'
        "<th>p95</th><th>Errors</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div></div>"
    )


def _cause(result: dict) -> str:
    v = result["verdict"]
    paras = []
    if v["bottleneck"]:
        culprit = f"<b>{_esc(v['culprit_route'])}</b> — " if v["culprit_route"] else ""
        paras.append(f"<p>{culprit}{_esc(v['bottleneck'])}</p>")
    if v["saturated"] and v["saturation_users"]:
        paras.append(
            f"<p>Throughput plateaued ~{v['peak_rps']:.0f} req/s around "
            f"{v['saturation_users']} users (capacity ceiling).</p>"
        )
    if v["marginal"]:
        paras.append("<p>Only wobbled at the very top of the ramp — you likely have "
                     "some headroom.</p>")
    if not paras:
        return ""
    return f'<div class="cause"><div class="lbl">Likely cause</div>{"".join(paras)}</div>'


def render_html(result: dict) -> str:
    target = result["target"]
    config = result["config"]
    dot, pill, headline, sub = _verdict(result)
    ts = datetime.strptime(result["created_at"], "%Y-%m-%dT%H:%M:%SZ").strftime(
        "%Y-%m-%d %H:%M UTC")
    n_routes = len(target["routes"])
    routes = f"{n_routes} route{'s' if n_routes != 1 else ''}"
    warn_html = (f'<div class="cause"><p>{_esc(result["warning"])}</p></div>'
                 if result.get("warning") else "")
    max_users = config["max_users"]
    meta = (f"{_esc(config['method'])} {MIDDOT} {config['stage_seconds']:g}s per level "
            f"{MIDDOT} max {max_users} users")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>PreScale — Readiness report</title>
<style>{_CSS}</style></head>
<body><div class="wrap">
  <div class="topbar">
    <div class="brand"><span class="mark"></span> PreScale</div>
    <div class="meta">prescale run {MIDDOT} {ts}</div>
  </div>
  <h1>Readiness report</h1>
  <div class="sub"><span class="url">{_esc(target["url"])}</span>
    <span>{MIDDOT} {routes} {MIDDOT} ramped 1 {RARROW} {max_users} users</span></div>
  <div class="panel verdict">
    <span class="dot {dot}"></span>
    <div><h2>{headline}</h2><p>{sub}</p></div>
    <span class="pill {dot}">{pill}</span>
  </div>
  {warn_html}
  <div class="grid">{_stats(result)}</div>
  <div class="section"><h3>Load ramp</h3>
    <div class="panel clip">
      <div class="chart">{_svg_chart(result)}</div>
      {_ramp_table(result)}
    </div>
    {_cause(result)}
  </div>
  {_route_table(result)}
  <footer><span>Generated by prescale {result["tool_version"]}</span>
    <span>{meta}</span></footer>
</div></body></html>
"""
