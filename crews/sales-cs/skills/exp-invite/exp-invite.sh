#!/usr/bin/env bash
# exp-invite — 体验群邀请 wrapper
# 让 agent 用 `exp-invite <cmd>` 走 PATH，零路径拼接。
# 转发到 scripts/invite.sh（真业务脚本）。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# 只解析 ~/.openclaw/bin 软链一层（bin/<skill> -> <workspace>/skills/<skill>/<skill>.sh），
# 不 readlink -f 继续展开 workspace 内 skills/<skill> 指向仓库模板的软链。
# invite.sh 用 dirname $0/../../.. 推导 workspace 根（./db/customer.db），
# readlink -f 会把 workspace 折叠成仓库模板路径，导致 db 解析到模板目录（无运行数据）。
# 保留字面 workspace 路径，db 才能命中真实运行数据目录。
if [ -L "$SELF" ]; then
  _target="$(readlink "$SELF")"
  case "$_target" in
    /*) SELF="$_target" ;;
    *)  SELF="$(cd "$(dirname "$SELF")" && pwd)/$_target" ;;
  esac
fi
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"
exec "$SCRIPT_DIR/scripts/invite.sh" "$@"
