# demo/ — hero recording

`make-demo.sh` regenerates the terminal hero clip for the landing page. It runs
the **real** `prescale investigate` against [`examples/fragile-shop.py`](../examples/fragile-shop.py),
records it with **asciinema** at a fixed 120×32, renders a brand-themed GIF with
**agg** (dark canvas `#0c0d0c`, cream text `#e7e3d8`, vermilion accent `#e35335`,
JetBrains Mono), and post-processes with **ffmpeg** into an autoplay-loop
`hero.mp4` + `hero.webm` (+ `poster.png`) that ends on a gentle zoom-hold of the
🔬 Diagnosis panel.

## Run

```bash
demo/make-demo.sh              # outputs to demo/out/ (git-ignored)
```

Needs the dev venv (`.venv`) plus `asciinema`, `agg`, and `ffmpeg` on PATH
(`curl`+`unzip` fetch JetBrains Mono the first time; agg falls back to DejaVu Sans
Mono otherwise).

## Embed (like OpenCode's hero)

```html
<video autoplay loop muted playsinline poster="poster.png">
  <source src="hero.webm" type="video/webm">
  <source src="hero.mp4" type="video/mp4">
</video>
```

## Tuning

Knobs at the top of `make-demo.sh`:

- `COLS` / `ROWS` — terminal geometry (aspect ratio / layout density).
- `FONTSIZE` — bigger = sharper/more legible on small hero areas.
- `SPEED` — agg playback speed; higher tightens the ramp/probe stretch.
- `ZOOM` / `ZY` / `HOLD` — the closing punch-in factor, vertical focus, and hold.
  Keep `ZOOM` gentle (~1.06) — the Diagnosis panel is full-width, so a large zoom
  clips its edges.
- `THEME` — the `bg,fg,<16 ANSI>` palette.
