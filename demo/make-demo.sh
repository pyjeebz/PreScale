#!/usr/bin/env bash
# Deterministic PreScale hero-demo recorder.
#
#   real `prescale investigate` (examples/fragile-shop.py)
#     -> asciinema (fixed 120x32 geometry, simulated typing)
#     -> agg        (brand theme: dark canvas, cream text, vermilion accent, JetBrains Mono)
#     -> ffmpeg     (subtle Ken-Burns hold on the 🔬 Diagnosis panel)
#     -> hero.mp4 + hero.webm + poster.png   (autoplay-loop hero video)
#
# Needs: the dev venv (.venv) + asciinema, agg, ffmpeg on PATH (curl+unzip for the font).
# Usage: demo/make-demo.sh [OUT_DIR]        # defaults to demo/out/
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${1:-$REPO/demo/out}"
PORT=8400
COLS=120; ROWS=32; FONTSIZE=22
SPEED=1.5            # agg playback speed — tightens the ramp/probe stretch
TYPE_DELAY=0.075     # per-keystroke (~50ms effective after SPEED)
ZOOM=1.06; ZY=0.60; HOLD=4.5   # gentle punch-in, held on the Diagnosis, in seconds
PYBIN="$REPO/.venv/bin"
# theme = bg,fg,<16 ANSI>  — magenta->cream so table headers stay on-brand; red = vermilion
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

# fresh fragile target
pkill -f "fragile-shop.py" 2>/dev/null || true; sleep 0.4
"$PYBIN/python" "$REPO/examples/fragile-shop.py" $PORT & SHOP=$!
trap 'kill $SHOP 2>/dev/null || true' EXIT
sleep 1

# driver: clean vermilion prompt, simulated typing, real prescale, end on the diagnosis
CMD="prescale investigate http://localhost:$PORT --path /search --path /product --path /checkout -s 1"
cat > "$OUT/driver.sh" <<DRV
clear
printf '\033[38;2;227;83;53m\xe2\x9d\xaf\033[0m '
sleep 0.6
c='$CMD'
for ((i=0;i<\${#c};i++)); do printf '%s' "\${c:i:1}"; sleep $TYPE_DELAY; done
sleep 0.4; printf '\n'
$CMD
sleep 0.4
DRV

# capture at fixed geometry
asciinema rec --overwrite --cols $COLS --rows $ROWS -i 0.4 \
  -c "bash $OUT/driver.sh" "$OUT/demo.cast" >/dev/null 2>&1

# render brand-themed gif
agg --cols $COLS --rows $ROWS --font-size $FONTSIZE --line-height 1.35 --fps-cap 60 \
    --idle-time-limit 0.4 --speed $SPEED --last-frame-duration 0.25 --no-loop \
    --theme "$THEME" "${FONTARGS[@]}" -q "$OUT/demo.cast" "$OUT/demo.gif"

W=$(ffprobe -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$OUT/demo.gif")
H=$(ffprobe -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$OUT/demo.gif")

# final Diagnosis frame
ffmpeg -y -v error -i "$OUT/demo.gif" -update 1 "$OUT/last.png"

# base clip (the run) + gentle zoom-hold on the Diagnosis
X264=(-c:v libx264 -pix_fmt yuv420p -crf 18 -profile:v high -an)
ZF=$(python3 -c "print(int($HOLD*60))")
ZSTEP=$(python3 -c "print(round(($ZOOM-1)/30,5))")
ffmpeg -y -v error -i "$OUT/demo.gif" -vf "fps=60,scale=${W}:${H}:flags=lanczos" \
  "${X264[@]}" "$OUT/base.mp4"
ffmpeg -y -v error -loop 1 -i "$OUT/last.png" -t $HOLD -r 60 \
  -vf "scale=${W}*2:${H}*2:flags=lanczos,zoompan=z='min(zoom+${ZSTEP},${ZOOM})':x='iw/2-(iw/zoom/2)':y='ih*${ZY}-(ih/zoom/2)':d=${ZF}:s=${W}x${H}:fps=60,format=yuv420p" \
  "${X264[@]}" "$OUT/zoomhold.mp4"

# concat -> hero.mp4 (+ webm + poster)
printf "file '%s'\nfile '%s'\n" "$OUT/base.mp4" "$OUT/zoomhold.mp4" > "$OUT/list.txt"
ffmpeg -y -v error -f concat -safe 0 -i "$OUT/list.txt" -c copy -movflags +faststart "$OUT/hero.mp4"
ffmpeg -y -v error -i "$OUT/hero.mp4" -an -c:v libvpx-vp9 -b:v 0 -crf 30 -row-mt 1 "$OUT/hero.webm"
ffmpeg -y -v error -i "$OUT/hero.mp4" -update 1 "$OUT/poster.png"

echo "done -> $OUT"
echo "  hero.mp4  ($(du -h "$OUT/hero.mp4" | cut -f1))   hero.webm ($(du -h "$OUT/hero.webm" | cut -f1))   poster.png"
echo "  ${W}x${H}  $(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$OUT/hero.mp4")s"
