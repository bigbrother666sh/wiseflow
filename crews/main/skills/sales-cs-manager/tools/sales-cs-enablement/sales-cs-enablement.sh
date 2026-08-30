#!/usr/bin/env bash
# sales-cs-enablement.sh - sales-cs-enablement 子命令分发器 wrapper
# 让 agent 用 `sales-cs-enablement <cmd>` 走 PATH，零路径拼接。
# 子命令：
#   check-channel  -> scripts/check_awada_channel.py（诊断：awada channel 是否已配置）
#   link / 无参     -> scripts/symlink_business_knowledge.py（主入口：业务知识软链）
# wrapper 自身只是 exec 转发，不改语义。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# Resolve symlink (wrapper is ln -sfn'd into ~/.openclaw/bin) so SCRIPT_DIR points at the real skill dir.
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"

CMD="${1:-link}"
[ "$#" -gt 0 ] && shift
case "$CMD" in
  check-channel)
    exec python3 "$SCRIPT_DIR/scripts/check_awada_channel.py" "$@"
    ;;
  link)
    exec python3 "$SCRIPT_DIR/scripts/symlink_business_knowledge.py" "$@"
    ;;
  *)
    echo "usage: sales-cs-enablement [link|check-channel]" >&2
    echo "  check-channel  检查 openclaw.json 是否已配置 awada channel" >&2
    echo "  link           软链 business_knowledge 到 sales-cs workspace（默认）" >&2
    exit 2
    ;;
esac
