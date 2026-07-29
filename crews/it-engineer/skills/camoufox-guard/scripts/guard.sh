#!/bin/bash
# camoufox-guard - 巡检 camoufox-bin 进程数，超阈值告警 + 清理孤儿，防 OOM 死机
#
# 背景：camoufox-bin 泄漏堆积致 13GB 机器 OOM 硬死机（07-17/07-27/07-29 三次），
# 根因是 browser.ts close() 不退 daemon 致 camoufox-bin 孤儿化（[[27]]/[[39]]），7.1 未根治。
# 由 it-engineer 心跳调用。幂等、安全：只杀超龄（>MAX_AGE_MIN）的孤儿进程，不影响活跃任务。
#
# 阈值可通过环境变量覆盖：
#   CAMOUFOX_GUARD_THRESHOLD (默认 6)   告警阈值（并发上限，超了报）
#   CAMOUFOX_GUARD_HARD_LIMIT (默认 12) 硬上限（超了杀最老孤儿，防 OOM）
#   CAMOUFOX_GUARD_MAX_AGE_MIN (默认 30) 超此年龄(分钟)视为孤儿可杀
set -uo pipefail

THRESHOLD="${CAMOUFOX_GUARD_THRESHOLD:-6}"
HARD_LIMIT="${CAMOUFOX_GUARD_HARD_LIMIT:-12}"
MAX_AGE_MIN="${CAMOUFOX_GUARD_MAX_AGE_MIN:-30}"

# camoufox-bin 进程列表：pid etimes(秒) rss(KB)，comm 精确匹配 camoufox-bin
list_pids() { ps -eo pid,etimes,rss,comm --no-headers | awk '$4=="camoufox-bin"'; }

COUNT=$(list_pids | wc -l | tr -d ' ')

if [ "$COUNT" -le "$THRESHOLD" ]; then
  echo "camoufox-guard: OK ($COUNT 个 camoufox-bin，阈值 $THRESHOLD)"
  exit 0
fi

echo "camoufox-guard: ⚠️ camoufox-bin = $COUNT（阈值 $THRESHOLD，硬限 $HARD_LIMIT）"
list_pids | awk '{printf "  pid=%s age=%dmin rss=%dMB\n",$1,int($2/60),int($3/1024)}'

# 超硬限：杀最老的孤儿（age > MAX_AGE_MIN），降到 THRESHOLD
# 安全保证：只杀超龄进程，活跃浏览器任务（< 30min）不受影响
if [ "$COUNT" -gt "$HARD_LIMIT" ]; then
  KILL_N=$((COUNT - THRESHOLD))
  echo "camoufox-guard: 🔴 超硬限，清理 $KILL_N 个超 ${MAX_AGE_MIN}min 的孤儿进程"
  list_pids | awk -v age=$((MAX_AGE_MIN*60)) '$2>age {print $1" "$2}' | sort -k2 -rn | head -n "$KILL_N" | while read -r pid et; do
    echo "  kill -TERM pid=$pid (age=$((et/60))min)"
    kill -TERM "$pid" 2>/dev/null || true
  done
  sleep 3
  AFTER=$(list_pids | wc -l | tr -d ' ')
  echo "camoufox-guard: 清理后剩 $AFTER 个"
  if [ "$AFTER" -gt "$HARD_LIMIT" ]; then
    echo "camoufox-guard: ⚠️ 仍超硬限，孤儿可能非超龄。建议告知用户重启 gateway：systemctl --user restart openclaw-gateway"
  fi
fi
