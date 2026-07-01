# demo/ — hero recording

`make-demo.sh` renders the terminal hero clip for the landing page from
[`sim.py`](sim.py), a **staged reproduction** of a `prescale investigate` run.
The wording, telemetry table, and Diagnosis mirror `prescale_cli.render` /
`prescale_cli.investigate` exactly — `sim.py` just *stages* the reveal so the
video can show the table, then errors creeping in on `/checkout`, then the
Diagnosis (the real command renders the finished report in one burst, which
doesn't read on video).

Pipeline:

```
sim.py  →  asciinema (120×34, no screen clears)
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

Needs `python3` plus `asciinema`, `agg`, and `ffmpeg` on PATH (`curl`+`unzip`
fetch JetBrains Mono the first time; agg falls back to DejaVu Sans Mono).

## Embed (like OpenCode's hero)

```html
<video autoplay loop muted playsinline poster="poster.png">
  <source src="hero.webm" type="video/webm">
  <source src="hero.mp4" type="video/mp4">
</video>
```

## Tuning

- **Pacing** — constants at the top of `sim.py`: `CPS` (typing speed), `RAMP_STEP`,
  `WAIT` (the two deliberate beats), `CREEP_STEP` (error-climb frames), `HOLD`.
- **Look** — `COLS` / `ROWS` / `FONTSIZE` / `THEME` at the top of `make-demo.sh`.
  Keep `ROWS` tall enough that the command + table + Diagnosis all fit without
  scrolling (the history is meant to stay on screen).
