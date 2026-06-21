#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-openagentio-promo-base.mp4}"
OUT="${2:-openagentio-promo-final.mp4}"

if [[ ! -f "$BASE" ]]; then
  hyperframes render -o "$BASE"
fi

ffmpeg -y \
  -i "$BASE" \
  -i assets/matrix_mcp_chat.mp4 \
  -i assets/observability.mp4 \
  -stream_loop 1 -i assets/code_with_rhythm_cut.mp3 \
  -filter_complex "\
[1:v]scale=-2:908,crop=990:908:(iw-990)/2:0,setsar=1,setpts=PTS+8.06/TB[matrix];\
[2:v]scale=-2:908,crop=975:908:(iw-975)/2:0,setsar=1,setpts=PTS+35.06/TB[trace];\
[0:v][matrix]overlay=104:86:enable='between(t,8.06,28.50)'[v1];\
[v1][trace]overlay=104:86:enable='between(t,35.06,56.33)'[vout];\
[3:a]atrim=0:60,volume=0.42[aout]" \
  -map "[vout]" \
  -map "[aout]" \
  -c:v libx264 \
  -pix_fmt yuv420p \
  -c:a aac \
  -movflags +faststart \
  -shortest \
  "$OUT"

echo "Wrote $OUT"
