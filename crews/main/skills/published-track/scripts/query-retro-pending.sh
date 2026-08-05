#!/usr/bin/env bash
# query-retro-pending.sh — 一键扫描待复盘作品 + 带出互动数据
# 让 agent 走 PATH 调用，零路径拼接。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
exec python3 "$SCRIPT_DIR/query-retro-pending.py" "$@"
