"""Self-contained HTML readiness report for `prescale run --html`.

Linear-styled (dark canvas, lavender accent, hairline borders), built from the
RunReport with no external dependencies — inline CSS, system font stack, an
inline-SVG chart. One file you can open offline, email, or attach to a PR.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone

from prescale_cli.loadtest import RunReport

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


def _ms(seconds: float) -> str:
    return "-" if seconds <= 0 else f"{seconds * 1000:.0f}ms"


def _err_td(rate: float) -> str:
    return '<td class="ok">0%</td>' if rate == 0 else f"<td>{rate:.0%}</td>"


def _svg_chart(report: RunReport) -> str:
    stages = report.stages
    pts = [(s.users, s.pct(0.95)) for s in stages]
    if not pts:
        return ""
    w, h, pl, pr, pb = 600, 180, 40, 40, 24
    pt = 24
    ymax = max(max(v for _, v in pts), report.latency_wall * 1.2) or 1.0
    n = len(pts)
    plot_w, plot_h = w - pl - pr, h - pt - pb

    def x(i: int) -> float:
        return pl + (plot_w * (i / (n - 1) if n > 1 else 0))

    def y(v: float) -> float:
        return h - pb - (v / ymax) * plot_h

    poly = " ".join(f"{x(i):.0f},{y(v):.0f}" for i, (_, v) in enumerate(pts))
    wall_y = y(report.latency_wall)
    dots, labels = [], []
    for i, (users, v) in enumerate(pts):
        if users == report.onset_users:
            color, lc, r = "#eb5757", "#eb5757", 4
        elif users == report.survives_users and report.onset_users is not None:
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
        f'fill="#eb5757">latency wall {MIDDOT} {report.latency_wall:g}s</text>'
        f'<line x1="{pl}" y1="{h - pb}" x2="{w - pr}" y2="{h - pb}" '
        f'stroke="#23252a" stroke-width="1"/>'
        f'<polyline points="{poly}" fill="none" stroke="#5e6ad2" stroke-width="2" '
        f'stroke-linejoin="round" stroke-linecap="round"/>'
        f'{"".join(dots)}{"".join(labels)}</svg>'
    )


def _verdict(report: RunReport) -> tuple[str, str, str, str]:
    if report.onset_users is None:
        return ("green", "READY",
                f"Held up through {report.max_tested} concurrent users",
                "No failures up to the most we tested.")
    if report.survives_users == 0:
        return ("red", "AT RISK",
                f"Struggles from ~{report.onset_users} concurrent users",
                "It buckles almost immediately under load.")
    return ("amber", "NEEDS ATTENTION",
            f"Survives ~{report.survives_users} concurrent users",
            f"First failure at ~{report.onset_users} users.")


def _stats(report: RunReport) -> str:
    onset = report.onset_users is not None
    survives = report.survives_users if onset else report.max_tested
    onset_stage = next((s for s in report.stages if s.users == report.onset_users), None)
    wall_p95 = onset_stage.pct(0.95) if onset_stage else max(
        (s.pct(0.95) for s in report.stages), default=0.0)
    p95_val = f"{wall_p95:.1f}" if wall_p95 >= 1 else f"{wall_p95 * 1000:.0f}"
    p95_unit = "s" if wall_p95 >= 1 else "ms"
    cards = [
        ("Survives", str(survives), "users"),
        ("Peak throughput", f"{report.peak_rps:.0f}", "req/s"),
        ("Breaks at", str(report.onset_users) if onset else "none", "users" if onset else ""),
        ("p95 at the wall" if onset else "Peak p95", p95_val, p95_unit),
    ]
    return "".join(
        f'<div class="panel stat"><div class="k">{k}</div>'
        f'<div class="v">{v}<span class="u">{u}</span></div></div>'
        for k, v, u in cards
    )


def _ramp_table(report: RunReport) -> str:
    rows = []
    for s in report.stages:
        cls = ' class="onset"' if s.users == report.onset_users else ""
        rows.append(
            f"<tr{cls}><td>{s.users}</td><td>{s.rps:.0f}</td>"
            f"<td>{_ms(s.pct(0.50))}</td><td>{_ms(s.pct(0.95))}</td>"
            f"<td>{_ms(s.pct(0.99))}</td>{_err_td(s.error_rate)}</tr>"
        )
    return (
        "<table><thead><tr><th>Users</th><th>Req/s</th><th>p50</th><th>p95</th>"
        "<th>p99</th><th>Errors</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>"
    )


def _route_table(report: RunReport) -> str:
    decisive = next((s for s in report.stages if s.users == report.onset_users),
                    report.stages[-1] if report.stages else None)
    if decisive is None or len(decisive.routes) <= 1:
        return ""
    ranked = sorted(decisive.routes.items(),
                    key=lambda kv: (kv[1].error_rate, kv[1].pct(0.95)), reverse=True)
    rows = []
    for label, stat in ranked:
        cls = ' class="onset"' if label == report.culprit_route else ""
        rows.append(
            f"<tr{cls}><td>{_esc(label)}</td><td>{stat.total / decisive.duration:.0f}</td>"
            f"<td>{_ms(stat.pct(0.95))}</td>{_err_td(stat.error_rate)}</tr>"
        )
    return (
        f'<div class="section"><h3>Per route {MIDDOT} at {decisive.users} users</h3>'
        '<div class="panel clip"><table><thead><tr><th>Route</th><th>Req/s</th>'
        "<th>p95</th><th>Errors</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table></div></div>"
    )


def _cause(report: RunReport) -> str:
    paras = []
    if report.bottleneck:
        culprit = f"<b>{_esc(report.culprit_route)}</b> — " if report.culprit_route else ""
        paras.append(f"<p>{culprit}{_esc(report.bottleneck)}</p>")
    if report.saturated and report.saturation_users:
        paras.append(
            f"<p>Throughput plateaued ~{report.peak_rps:.0f} req/s around "
            f"{report.saturation_users} users (capacity ceiling).</p>"
        )
    if report.marginal:
        paras.append("<p>Only wobbled at the very top of the ramp — you likely have "
                     "some headroom.</p>")
    if not paras:
        return ""
    return f'<div class="cause"><div class="lbl">Likely cause</div>{"".join(paras)}</div>'


def render_html(report: RunReport, *, url: str, targets: list[str], method: str,
                stage_seconds: float, max_users: int, warning: str | None = None) -> str:
    dot, pill, headline, sub = _verdict(report)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    routes = f"{len(targets)} route{'s' if len(targets) != 1 else ''}"
    warn_html = (f'<div class="cause"><p>{_esc(warning)}</p></div>') if warning else ""
    meta = f"{_esc(method)} {MIDDOT} {stage_seconds:g}s per level {MIDDOT} max {max_users} users"
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
  <div class="sub"><span class="url">{_esc(url)}</span>
    <span>{MIDDOT} {routes} {MIDDOT} ramped 1 {RARROW} {max_users} users</span></div>
  <div class="panel verdict">
    <span class="dot {dot}"></span>
    <div><h2>{headline}</h2><p>{sub}</p></div>
    <span class="pill {dot}">{pill}</span>
  </div>
  {warn_html}
  <div class="grid">{_stats(report)}</div>
  <div class="section"><h3>Load ramp</h3>
    <div class="panel clip">
      <div class="chart">{_svg_chart(report)}</div>
      {_ramp_table(report)}
    </div>
    {_cause(report)}
  </div>
  {_route_table(report)}
  <footer><span>Generated by prescale 0.1.0</span>
    <span>{meta}</span></footer>
</div></body></html>
"""
