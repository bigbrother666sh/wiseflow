#!/usr/bin/env bash
# leak-guard.sh — 盲测通道泄漏自检
#
# 扫描 rubric_notes.md 是否混入"实绩/作品名/派生证据"——这些东西会经 blind sub-agent
# 的白名单读到,把盲打分污染成"看过实绩的事后合理化"。本脚本在 Bump 落地后强制跑,
# 命中即非零退出,触发 abort + 回滚。原型来自上游 cheat-on-content v1.4 bump Phase 5
# leak guard,我们没用他们的 7 步迁移(因为我们 fork 时就把 rubric / rubric-memo 拆开了),
# 只把"写时防回归"的 guard 抄来。
#
# 用法:
#   leak-guard.sh                              # 扫默认 calibration/rubric_notes.md
#   leak-guard.sh --file path/to/rubric_notes.md
#   leak-guard.sh --json                       # 输出 JSON(默认输出人读报告)
#
# 退出码:
#   0  干净,无实绩泄漏
#   2  命中疑似实绩 pattern(bump 流程应 abort + 回滚)
#   1  脚本用法错误 / 文件不存在
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
CAL_ROOT="$ROOT/calibration"
TARGET="$CAL_ROOT/rubric_notes.md"
JSON_MODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) TARGET="$2"; shift 2 ;;
    --json) JSON_MODE=1; shift ;;
    -h|--help)
      sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) echo "leak-guard: unknown arg: $1" >&2; exit 1 ;;
  esac
done

if [[ ! -f "$TARGET" ]]; then
  if [[ "$JSON_MODE" -eq 1 ]]; then
    echo "{\"ok\":false,\"error\":\"file not found: $TARGET\"}"
  else
    echo "❌ leak-guard: file not found: $TARGET" >&2
  fi
  exit 1
fi

# ── pattern 定义 ──
# 强信号:数字 + 量级单位(万/w/阅读/播放等),几乎只可能出现在实绩引用里。
STRONG_RE='[0-9]+\s*[wW万]|[0-9]+\s*(播放|阅读|阅读量|点赞|转发|评论|完播|转粉|浏览)'
# 弱信号:中文实绩词本身。命中需人工 review——可能是"复盘后观察会写入此处"这类说明性散文。
# 单独弱信号不当 hard block,但会标到 warnings[] 让 bump 流程提示人工 review。
WEAK_RE='实绩|播放量|阅读量|点赞数|转发量|评论数|完播率|转粉率'

# 白名单排除行(命中强信号但属于合法上下文):
#   - bucket 边界:"baseline × N" / "baseline × 0.3 ~ 1" / "< baseline × 10" 等(档位定义)
#   - 公式行:含 × / ÷ 数学符号 + composite 等公式 token(归一化常数/缩放因子)
#   - 版本速查表的公式签名行:如 "ER1.5+HP1.5+..."
#   - "×N" 形式的纯权重/倍数(×1.5 / ×2.0 / ×0.3)
WHITELIST_RE='baseline\s*[×x*]|×\s*[0-9]|composite|归一化|缩放|/[0-9]+\.?[0-9]*\s*[×x]|权重|×\s*[0-9]+\.[0-9]+'

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

strong_hits="$TMP_DIR/strong.txt"
weak_hits="$TMP_DIR/weak.txt"
: > "$strong_hits"
: > "$weak_hits"

lineno=0
while IFS= read -r line; do
  lineno=$((lineno + 1))
  # 先过白名单:整行若命中白名单,跳过(它是公式/bucket/权重上下文)
  if [[ "$line" =~ $WHITELIST_RE ]]; then
    continue
  fi
  if [[ "$line" =~ $STRONG_RE ]]; then
    printf '%d\t%s\n' "$lineno" "$line" >> "$strong_hits"
  elif [[ "$line" =~ $WEAK_RE ]]; then
    printf '%d\t%s\n' "$lineno" "$line" >> "$weak_hits"
  fi
done < "$TARGET"

strong_count=$(wc -l < "$strong_hits")
weak_count=$(wc -l < "$weak_hits")

emit_json() {
  local hits=()
  while IFS=$'\t' read -r ln text; do
    [[ -z "$ln" ]] && continue
    hits+=("{\"line\":$ln,\"text\":\"$(printf '%s' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g')\"}")
  done < "$strong_hits"
  local warr=()
  while IFS=$'\t' read -r ln text; do
    [[ -z "$ln" ]] && continue
    warr+=("{\"line\":$ln,\"text\":\"$(printf '%s' "$text" | sed 's/\\/\\\\/g; s/"/\\"/g')\"}")
  done < "$weak_hits"
  local joined; joined=$(IFS=,; printf '%s' "${hits[*]:-}")
  local wjoined; wjoined=$(IFS=,; printf '%s' "${warr[*]:-}")
  printf '{"ok":true,"file":"%s","strong_hits":[%s],"weak_hits":[%s],"strong_count":%d,"weak_count":%d,"clean":%s}\n' \
    "$TARGET" "$joined" "$wjoined" "$strong_count" "$weak_count" \
    "$([[ $strong_count -eq 0 ]] && echo true || echo false)"
}

if [[ "$JSON_MODE" -eq 1 ]]; then
  emit_json
else
  if [[ $strong_count -eq 0 && $weak_count -eq 0 ]]; then
    echo "✅ leak-guard: $TARGET 干净,无实绩泄漏"
  else
    echo "⚠️ leak-guard: $TARGET 发现疑似实绩泄漏"
    echo ""
    if [[ $strong_count -gt 0 ]]; then
      echo "【强信号 — 必须抽离到 rubric-memo.md】($strong_count 行):"
      while IFS=$'\t' read -r ln text; do
        [[ -z "$ln" ]] && continue
        printf '  L%d: %s\n' "$ln" "$text"
      done < "$strong_hits"
      echo ""
    fi
    if [[ $weak_count -gt 0 ]]; then
      echo "【弱信号 — 请人工 review】($weak_count 行):"
      while IFS=$'\t' read -r ln text; do
        [[ -z "$ln" ]] && continue
        printf '  L%d: %s\n' "$ln" "$text"
      done < "$weak_hits"
      echo ""
    fi
    echo "修复:把强信号行抽离到 calibration/rubric-memo.md,rubric_notes.md 只留通用公式/维度定义/bucket 边界。"
  fi
fi

# 强信号命中 = hard block(bump 应 abort 回滚);纯弱信号不 block(人读 review 即可)
if [[ $strong_count -gt 0 ]]; then
  exit 2
fi
exit 0
