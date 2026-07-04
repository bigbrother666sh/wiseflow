#!/usr/bin/env bash
# login-manager.sh — 平台登录态管理 wrapper
#
# 委托给 login_manager.py（Python 3 stdlib + camoufox-cli）。
# Phase 4.5.2 替换：原 CDP WebSocket 抽 cookie 路径 → camoufox-cli cookies export。
# 用法：login-manager.sh <command> [args...]
#
# 命令：
#   check <platform>                     探活 (exit 0/2)
#   read  <platform>                     读中央 JSON
#   write <platform>                     从 stdin 写中央 JSON
#   status-all                           批量探活
#   qr-headless <platform> [url]         启 headless + 截图 QR
#   qr-confirm <platform> --session <s>  轮询扫码 + cookies export
#   cookie-export <platform> <session>   从 camoufox session 落中央 JSON
#   cookie-import <platform> <session>   从中央 JSON 注 camoufox session
#   session-cleanup <platform> <session> 关 camoufox session
#
# 平台：douyin, bilibili, kuaishou, xhs-publish, xhs-browse,
#       weibo, zhihu, wechat-channels
#
# 退出码：
#   0  成功
#   1  通用错误
#   2  session 失效 / 扫码超时 → 触发重新登录流程

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_SCRIPT="${SCRIPT_DIR}/login_manager.py"

exec python3 "$PY_SCRIPT" "$@"
