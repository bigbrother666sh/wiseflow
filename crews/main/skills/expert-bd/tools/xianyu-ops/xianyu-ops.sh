#!/usr/bin/env bash
# xianyu-ops.sh — xianyu-ops 工具 wrapper（子命令分发）
# 让 agent 用 `xianyu-ops <子命令> [参数...]` 走 PATH，零路径拼接。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# 解析 ~/.openclaw/bin 软链一层，定位工具目录（见 bd-record.sh 同款说明）。
if [ -L "$SELF" ]; then
  _target="$(readlink "$SELF")"
  case "$_target" in
    /*) SELF="$_target" ;;
    *)  SELF="$(cd "$(dirname "$SELF")" && pwd)/$_target" ;;
  esac
fi
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"

cmd="${1:-}"
if [ $# -gt 0 ]; then shift; fi

case "$cmd" in
  search)   exec python3 "$SCRIPT_DIR/scripts/xianyu_search.py" "$@" ;;
  *)
    cat >&2 <<'USAGE'
用法: xianyu-ops <子命令> [参数...]

子命令:
  search       闲鱼商品搜索（--query [--min-price] [--max-price] [--province] [--city] [--limit]）

商品详情 / 私信操作走 camoufox-cli + xianyu-ops 工具说明（SKILL.md），无独立脚本。
USAGE
    exit 1
    ;;
esac
