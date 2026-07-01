#!/usr/bin/env bash
# PreScale landing-page hero recorder.
#
#   demo/sim.py  (staged reproduction of `prescale investigate`: type -> ramp ->
#                 telemetry table -> errors creep in on /checkout -> Diagnosis)
#     -> asciinema  (fixed 120x34 geometry, no screen clears)
#     -> agg        (brand theme, JetBrains Mono, --font-size 24, 60 fps -> GIF)
#     -> ffmpeg     (container transcode ONLY — native 1:1 scale, no crop/zoom)
#     -> hero.mp4 + hero.webm + poster.png
#
# agg emits GIF only, so ffmpeg is used purely to package that GIF into mp4/webm
# at its exact resolution (even-dimension pad for codec compatibility — no scale).
#
# Needs: python3 + asciinema, agg, ffmpeg on PATH (curl+unzip for the font).
# Usage: demo/make-demo.sh [OUT_DIR]        # defaults to demo/out/
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/demo/out}"
COLS=120; ROWS=34; FONTSIZE=24
# theme = bg,fg,<16 ANSI> — dark canvas, cream default; sim.py emits truecolor accents
THEME="0c0d0c,e7e3d8,0c0d0c,e35335,8f8c83,e7e3d8,8f8c83,e7e3d8,8f8c83,e7e3d8,5c5a54,e35335,a8a499,e7e3d8,8f8c83,e7e3d8,a8a499,ffffff"

mkdir -p "$OUT"; FONTDIR="$OUT/fonts"; mkdir -p "$FONTDIR"

# JetBrains Mono (once, best-effort; agg falls back to DejaVu Sans Mono otherwise)
if [ ! -f "$FONTDIR/JetBrainsMono-Regular.ttf" ]; then
  curl -fsSL -o "$OUT/jbm.zip" \
    https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip \
    && unzip -oq -j "$OUT/jbm.zip" 'fonts/ttf/JetBrainsMono-Regular.ttf' \
       'fonts/ttf/JetBrainsMono-Bold.ttf' -d "$FONTDIR" || true
fi
FONTARGS=(); [ -f "$FONTDIR/JetBrainsMono-Regular.ttf" ] \
  && FONTARGS=(--font-dir "$FONTDIR" --font-family "JetBrains Mono")

# capture the simulation at fixed geometry (sim.py owns all timing incl. the hold)
asciinema rec --overwrite --cols $COLS --rows $ROWS \
  -c "python3 -u $REPO/demo/sim.py" "$OUT/demo.cast" >/dev/null 2>&1

# render brand-themed GIF at native 1x, 60 fps; idle cap 5s keeps the 4s hold
agg --cols $COLS --rows $ROWS --font-size $FONTSIZE --line-height 1.4 --fps-cap 60 \
    --idle-time-limit 5 --no-loop --theme "$THEME" "${FONTARGS[@]}" \
    -q "$OUT/demo.cast" "$OUT/demo.gif"

# native-scale transcode — NO crop, NO scale, NO zoom (even-dimension pad only)
EVENPAD="pad=ceil(iw/2)*2:ceil(ih/2)*2:0:0:color=0x0c0d0c"
ffmpeg -y -v error -i "$OUT/demo.gif" -vf "${EVENPAD},format=yuv420p" \
  -c:v libx264 -crf 18 -profile:v high -an -movflags +faststart "$OUT/hero.mp4"
ffmpeg -y -v error -i "$OUT/demo.gif" -vf "$EVENPAD" \
  -c:v libvpx-vp9 -b:v 0 -crf 30 -row-mt 1 -an "$OUT/hero.webm"
ffmpeg -y -v error -i "$OUT/hero.mp4" -update 1 "$OUT/poster.png"   # last frame

W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$OUT/hero.mp4")
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$OUT/hero.mp4")
echo "done -> $OUT"
echo "  hero.mp4 ($(du -h "$OUT/hero.mp4" | cut -f1))  hero.webm ($(du -h "$OUT/hero.webm" | cut -f1))  poster.png"
echo "  ${W}x${H} (native 1x)  $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/hero.mp4")s"
