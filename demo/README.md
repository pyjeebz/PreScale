# demo/ — hero recording

`make-demo.sh` records the terminal hero clip for the landing page from a **real**
`prescale investigate` run against [`examples/fragile-shop.py`](../examples/fragile-shop.py)
— nothing is scripted. Because `investigate` now draws a **live ramp table**, the
recording genuinely shows the load climbing, the error rate creeping in on
`/checkout` (rows turning red), and then the 🔬 Diagnosis — whatever the tool
actually measures that run.

Pipeline:

```
fragile-shop.py + real `prescale investigate` (live ramp table)
  →  asciinema (120×34 PTY, so the live table animates)
  →  agg       (brand theme, JetBrains Mono, --font-size 24, 60 fps → GIF)
  →  ffmpeg    (container transcode only → hero.mp4 + hero.webm + poster.png)
```

agg emits **GIF only**, so ffmpeg is used purely to package that GIF into
`.mp4`/`.webm` at its **native 1× resolution** — no crop, no scale, no zoom (only
an even-dimension pad for codec compatibility).

## Run

```bash
demo/make-demo.sh              # outputs to demo/out/ (git-ignored)
```

Needs the dev venv (`.venv`) plus `asciinema`, `agg`, and `ffmpeg` on PATH
(`curl`+`unzip` fetch JetBrains Mono the first time; agg falls back to DejaVu Sans
Mono).

## Embed (like OpenCode's hero)

```html
<video autoplay loop muted playsinline poster="poster.png">
  <source src="hero.webm" type="video/webm">
  <source src="hero.mp4" type="video/mp4">
</video>
```

## Tuning

Knobs at the top of `make-demo.sh`:

- `SPEED` — agg playback speed; higher tightens the ramp/probe stretch.
- `--last-frame-duration` (in the agg call) — the end hold on the Diagnosis. agg
  drops trailing terminal idle, so this is the real hold knob, not the driver's
  `sleep`.
- `COLS` / `ROWS` / `FONTSIZE` / `THEME` — geometry and palette.

The ramp length follows the tool's own ladder and `-s` (seconds per level); lower
`-s` for a shorter clip.
