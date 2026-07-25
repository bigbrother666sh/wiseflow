#!/usr/bin/env bash
# aigc-video-gen.sh — aigc-video-gen 顶层 wrapper（薄转发）
# 让 agent 用 `aigc-video-gen <args>` 走 PATH，零路径拼接。
# 内部转发到 scripts/gen.py；wrapper 自身只是 exec 转发，不改语义。
# 平台自动判断写在 gen.py 里：有 MODELSTUDIO_API_KEY 走百炼，否则有 AWK_GEN_KEY 谰火山，
# 两者皆无则输出提示让 Agent 改用 pexels-footage / pixabay-footage（退出码 2）。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# Resolve symlink (wrapper is ln -sfn'd into ~/.openclaw/bin) so SCRIPT_DIR points at the real skill dir.
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
exec python3 "$SCRIPT_DIR/scripts/gen.py" "$@"
