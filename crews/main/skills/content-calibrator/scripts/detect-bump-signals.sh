#!/usr/bin/env bash
# detect-bump-signals.sh — 结构化 bump 信号检测 wrapper
# 让 agent 走 PATH 调用，零路径拼接。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
# 默认从 PWD 推导 ROOT（agent 从 workspace 根调用）
export PUBLISHED_TRACK_ROOT="${PUBLISHED_TRACK_ROOT:-$PWD}"
exec python3 "$SCRIPT_DIR/detect-bump-signals.py" "$@"
