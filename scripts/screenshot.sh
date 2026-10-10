#!/usr/bin/env bash
# pipeline-animation skill · 截图验证脚本
# 用法:
#   ./scripts/screenshot.sh <html文件> [t秒] [输出png]
#   ./scripts/screenshot.sh examples/r1_pipeline.html 27        → /tmp/pa_r1_pipeline_t27.png
#   ./scripts/screenshot.sh my_diagram.html 12.8 out.png
# 依赖: macOS 自带的 Google Chrome（无其他依赖）
set -euo pipefail

F="${1:?用法: screenshot.sh <html文件> [t秒] [输出png]}"
T="${2:-27}"
BASE=$(basename "$F" .html)
OUT="${3:-/tmp/pa_${BASE}_t${T}.png}"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "未找到 Google Chrome: $CHROME" >&2; exit 1; }
[ -f "$F" ] || { echo "文件不存在: $F" >&2; exit 1; }

F_ABS=$(cd "$(dirname "$F")" && pwd)/$(basename "$F")

"$CHROME" --headless --disable-gpu --screenshot="$OUT" \
  --window-size=1600,900 --hide-scrollbars --virtual-time-budget=6000 \
  "file://$F_ABS?t=$T" 2>/dev/null

echo "$OUT"
