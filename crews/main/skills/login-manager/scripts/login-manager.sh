#!/usr/bin/env bash
# login-manager.sh — Platform login state management wrapper
#
# Wraps the TypeScript implementation for simple one-line invocation.
# Usage: login-manager.sh <command> [args...]
#
# Commands:
#   check  <platform>   Probe: cookies still valid?
#   read   <platform>   Print stored session JSON
#   write  <platform>   Save session from stdin JSON
#   status-all          Check all stored sessions at once
#
# Cookie export (one-step):
#   ./scripts/export-cookies.sh <wsUrl> <domain> <platform>
#     Extract cookies from browser tab via CDP and save to login-manager storage.
#
# Platforms: douyin, bilibili, kuaishou, xhs, xhs-publish, xhs-browse,
#            weibo, zhihu, wechat-channels
#
# Exit codes:
#   0  Success
#   1  General error
#   2  Session expired / not found → trigger browser login

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TS_SCRIPT="${SCRIPT_DIR}/login_manager.ts"

exec node --experimental-strip-types "$TS_SCRIPT" "$@"
