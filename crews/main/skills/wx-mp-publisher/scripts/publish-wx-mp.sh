#!/usr/bin/env bash
# publish-wx-mp.sh — 推送 Markdown 稿件到微信公众号草稿箱
#
# Usage: publish-wx-mp.sh <markdown_file> [theme]
#   theme 可以是：
#     - 内置主题 id：default|orangeheart|rainbow|lapis|pie|maize|purple|phycat（默认 pie）
#     - 本地 .css 文件路径：直接作为自定义主题加载（传给 wenyan-cli --custom-theme）
#     - 已注册自定义主题 id：在 wx-mp-publisher/SKILL.md 主题表中登记的 id
#       （描述含“用户自定义”），脚本自动解析出对应 CSS 文件路径
#
# 环境变量（优先本地直连）：
#   本地直连：WECHAT_APP_ID + WECHAT_APP_SECRET
#   relay  ：WENYAN_SERVER_URL + WENYAN_API_KEY
#   可选   ：WECHAT_TARGET_APP_ID（多公众号时指定目标 AppID）
#            WENYAN_PROXY（代理，如 http://127.0.0.1:7890）

set -euo pipefail

MD_FILE="${1:?Usage: publish-wx-mp.sh <markdown_file> [theme]}"
THEME="${2:-pie}"
CUSTOM_THEME=""

[[ -f "$MD_FILE" ]] || { echo "ERROR: 文件不存在: $MD_FILE"; exit 1; }

# ── 主题参数解析 ─────────────────────────────────────────────────────────────
# 1. 指向本地 .css 文件      → 直接作为自定义主题
# 2. SKILL.md 主题表中登记的自定义 id → 解析出 CSS 路径
# 3. 其它                     → 视为内置主题 id 原样传给 -t/--theme
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_MD="$SCRIPT_DIR/../SKILL.md"
CREW_WORKSPACE="$(cd "$SCRIPT_DIR/../../.." && pwd)"

resolve_registered_theme() {
  # $1 = theme id；stdout 输出解析到的 CSS 路径，找不到则返回非零
  local id="$1" row path
  row=$(grep -E "^\| \`$id\` \|.*用户自定义" "$SKILL_MD" 2>/dev/null | head -n1 || true)
  [[ -z "$row" ]] && return 1
  path=$(printf '%s' "$row" | sed -nE 's/.*文件：`([^`]+)`.*/\1/p')
  [[ -z "$path" ]] && return 1
  if [[ -f "$path" ]]; then
    printf '%s' "$path"
  elif [[ -f "$CREW_WORKSPACE/$path" ]]; then
    printf '%s' "$CREW_WORKSPACE/$path"
  else
    return 1
  fi
}

if [[ -f "$THEME" && "$THEME" == *.css ]]; then
  CUSTOM_THEME="$THEME"
  THEME="default"
elif resolved=$(resolve_registered_theme "$THEME"); then
  CUSTOM_THEME="$resolved"
  THEME="default"
fi

# ── 模式判断（优先本地直连）─────────────────────────────────────────────────
if [[ -n "${WECHAT_APP_ID:-}" && -n "${WECHAT_APP_SECRET:-}" ]]; then
  MODE=local
elif [[ -n "${WENYAN_SERVER_URL:-}" && -n "${WENYAN_API_KEY:-}" ]]; then
  MODE=relay
else
  echo "ERROR: 请配置环境变量："
  echo "  本地直连：WECHAT_APP_ID + WECHAT_APP_SECRET"
  echo "  relay  ：WENYAN_SERVER_URL + WENYAN_API_KEY"
  exit 1
fi

echo ">>> 模式: $MODE  主题: $THEME"
[[ -n "$CUSTOM_THEME" ]] && echo ">>> 自定义主题: $CUSTOM_THEME"
echo ">>> 文件: $MD_FILE"
[[ -n "${WECHAT_TARGET_APP_ID:-}" ]] && echo ">>> 目标公众号: $WECHAT_TARGET_APP_ID"
echo ">>> 注意：首次运行会自动下载 @wenyan-md/cli，约需 10–30 秒..."

# ── 构建可选参数 ─────────────────────────────────────────────────────────────
EXTRA_ARGS=()
[[ -n "${WECHAT_TARGET_APP_ID:-}" ]] && EXTRA_ARGS+=(--app-id "${WECHAT_TARGET_APP_ID}")
[[ -n "${WENYAN_PROXY:-}" ]]         && EXTRA_ARGS+=(--proxy "${WENYAN_PROXY}")
[[ -n "$CUSTOM_THEME" ]]             && EXTRA_ARGS+=(--custom-theme "$CUSTOM_THEME")

if [[ "$MODE" == "relay" ]]; then
  npx --yes @wenyan-md/cli publish \
    -f "$MD_FILE" \
    -t "$THEME" \
    --server "${WENYAN_SERVER_URL}" \
    --api-key "${WENYAN_API_KEY}" \
    "${EXTRA_ARGS[@]}"
else
  npx --yes @wenyan-md/cli publish \
    -f "$MD_FILE" \
    -t "$THEME" \
    "${EXTRA_ARGS[@]}"
fi
