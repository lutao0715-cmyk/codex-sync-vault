#!/bin/sh
# 自动剪辑台 · 统一入口
#
#   ./run.sh doctor --fix          装依赖
#   ./run.sh panel                 开面板
#   ./run.sh auto in.mp4 -o out.mp4 --mode silence
#   ./run.sh analyze in.mp4
#
# 优先用 skill 自带的 venv（numpy 在那儿），退回系统 python3。

set -e
DIR=$(cd "$(dirname "$0")" && pwd)

if [ -x "$DIR/.venv/bin/python" ]; then
  PY="$DIR/.venv/bin/python"
elif [ -x "$DIR/.venv/Scripts/python.exe" ]; then
  PY="$DIR/.venv/Scripts/python.exe"
else
  PY=$(command -v python3 || command -v python)
fi

if [ -z "$PY" ]; then
  echo "找不到 python3。装一个 Python 3.9+ 再来。" >&2
  exit 1
fi

if [ ! -x "$DIR/bin/ffmpeg" ] && ! command -v ffmpeg >/dev/null 2>&1; then
  case "$1" in
    doctor|--help|-h|"") ;;
    *) echo "提示：还没找到 ffmpeg，先跑  $0 doctor --fix" >&2 ;;
  esac
fi

exec "$PY" "$DIR/scripts/avx.py" "$@"
