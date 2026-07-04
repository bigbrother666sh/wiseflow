#!/usr/bin/env bash
# wx-mp-hunter — WeChat Official Account Hunter wrapper
#
# Simplifies invocation by wrapping the TypeScript implementation.
# Usage: ./wx-mp-hunter.sh <command> [args...]
#
# Commands:
#   check-session                         检查 session 是否有效
#   login-qr                              生成二维码（登录第一步）
#   login-confirm [--timeout 120]         确认登录（登录第二步）
#   search <keyword> [--begin N] [--size N]
#   account-posts <fakeid> [--begin N] [--size N] [--keyword K]
#   fetch <url> [--html]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS_SCRIPT="${SCRIPT_DIR}/wx_mp_hunter.ts"

exec node --experimental-strip-types "$TS_SCRIPT" "$@"
