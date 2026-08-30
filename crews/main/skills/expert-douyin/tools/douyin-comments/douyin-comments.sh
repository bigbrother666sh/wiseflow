#!/usr/bin/env bash
# douyin-comments — 抖音评论抓取 wrapper
# 让 agent 用 `douyin-comments <cmd>` 走 PATH，零路径拼接。
# 直调 scripts/fetch_comments.ts（纯 HTTP + login-manager cookie + relay 签名，不起浏览器）。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# Resolve symlink (wrapper is ln -sfn'd into ~/.openclaw/bin) so SCRIPT_DIR points at the real skill dir.
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
exec node --experimental-strip-types "$SCRIPT_DIR/scripts/fetch_comments.ts" "$@"
