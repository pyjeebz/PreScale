#!/usr/bin/env bash
# PreScale landing-page hero recorder — captures the REAL `prescale investigate`.
#
#   examples/fragile-shop.py (a target that breaks under load)
#   + real `prescale investigate` with its live ramp table
#     -> asciinema  (PTY, so the live table animates: rows fill, errors climb red)
#     -> agg        (brand theme, JetBrains Mono, --font-size 24, 60 fps -> GIF)
#     -> ffmpeg     (container transcode ONLY — native 1:1 scale, no crop/zoom)
#     -> hero.mp4 + hero.webm + poster.png
#
# Nothing is scripted: the numbers, the red rows, and the Diagnosis are whatever
# the tool actually measures this run. agg emits GIF only, so ffmpeg is used
# purely to package it into mp4/webm at native resolution (even-dimension pad
# for codec compatibility — no crop, scale, or zoom).
#
# Needs: the dev venv (.venv) + asciinema, agg, ffmpeg on PATH (curl+unzip for font).
# Usage: demo/make-demo.sh [OUT_DIR]        # defaults to demo/out/
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/demo/out}"
PORT=8400
COLS=120; ROWS=34; FONTSIZE=24
SPEED=1.5            # agg playback speed — tightens the ramp/probe stretch
TYPE_DELAY=0.05     # per keystroke (~33ms effective after SPEED)
PYBIN="$REPO/.venv/bin"
THEME="0c0d0c,e7e3d8,0c0d0c,e35335,8f8c83,e7e3d8,8f8c83,e7e3d8,8f8c83,e7e3d8,5c5a54,e35335,a8a499,e7e3d8,8f8c83,e7e3d8,a8a499,ffffff"

mkdir -p "$OUT"; FONTDIR="$OUT/fonts"; mkdir -p "$FONTDIR"
export PATH="$PYBIN:$PATH"
export PRESCALE_HOME="$OUT/store"

# JetBrains Mono (once, best-effort; agg falls back to DejaVu Sans Mono otherwise)
if [ ! -f "$FONTDIR/JetBrainsMono-Regular.ttf" ]; then
  curl -fsSL -o "$OUT/jbm.zip" \
    https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip \
    && unzip -oq -j "$OUT/jbm.zip" 'fonts/ttf/JetBrainsMono-Regular.ttf' \
       'fonts/ttf/JetBrainsMono-Bold.ttf' -d "$FONTDIR" || true
fi
FONTARGS=(); [ -f "$FONTDIR/JetBrainsMono-Regular.ttf" ] \
  && FONTARGS=(--font-dir "$FONTDIR" --font-family "JetBrains Mono")

# fresh fragile target (patterns below live in this file, not the invocation)
pkill -f fragile-shop.py 2>/dev/null || true
fuser -k ${PORT}/tcp 2>/dev/null || true
sleep 0.4
"$PYBIN/python" "$REPO/examples/fragile-shop.py" $PORT & SHOP=$!
trap 'kill $SHOP 2>/dev/null || true' EXIT
sleep 1.2

# driver: clean vermilion prompt, simulated typing, the real command, then a hold
CMD="prescale investigate http://localhost:$PORT --path /search --path /product --path /checkout -s 1"
cat > "$OUT/driver.sh" <<DRV
clear
printf '\033[38;2;227;83;53m\xe2\x9d\xaf\033[0m '
sleep 0.6
c='$CMD'
for ((i=0;i<\${#c};i++)); do printf '%s' "\${c:i:1}"; sleep $TYPE_DELAY; done
sleep 0.4; printf '\n'
$CMD
sleep 0.5
DRV

# capture at fixed geometry (asciinema PTY -> the live ramp table animates)
asciinema rec --overwrite --cols $COLS --rows $ROWS \
  -c "bash $OUT/driver.sh" "$OUT/demo.cast" >/dev/null 2>&1

# render brand-themed GIF at native 1x, 60 fps; idle cap 5s keeps the final hold
# --last-frame-duration is the real end hold (agg drops trailing terminal idle)
agg --cols $COLS --rows $ROWS --font-size $FONTSIZE --line-height 1.4 --fps-cap 60 \
    --speed $SPEED --idle-time-limit 2 --last-frame-duration 3.5 --no-loop \
    --theme "$THEME" "${FONTARGS[@]}" -q "$OUT/demo.cast" "$OUT/demo.gif"

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
