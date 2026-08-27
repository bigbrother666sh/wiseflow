#!/usr/bin/env bash
# swcr-register.sh — swcr-register 工具 wrapper（子命令分发）
# 让 agent 用 `swcr-register <子命令> [参数...]` 走 PATH，零路径拼接。
# 每个子命令 exec 转发到 scripts/ 下对应 Python 脚本，不改语义。
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
  code-doc)    exec python3 "$SCRIPT_DIR/scripts/generate_code_doc.py" "$@" ;;
  manual)      exec python3 "$SCRIPT_DIR/scripts/generate_manual.py" "$@" ;;
  form-info)   exec python3 "$SCRIPT_DIR/scripts/generate_form_info.py" "$@" ;;
  *)
    cat >&2 <<'USAGE'
用法: swcr-register <子命令> [参数...]

子命令:
  code-doc     生成程序鉴别材料（源程序文档 .docx）
  manual       生成软件操作手册（README -> .docx）
  form-info    生成申请填报信息 Markdown

各子命令参数见 swcr-register 工具说明（SKILL.md）。
USAGE
    exit 1
    ;;
esac
