#!/usr/bin/env bash
# published-track.sh — published-track 顶层 wrapper（子命令分发）
# 让 agent 用 `published-track <子命令> [参数...]` 走 PATH，零路径拼接。
# 每个子命令 exec 转发到 scripts/ 下对应脚本，不改语义。
set -euo pipefail
SELF="${BASH_SOURCE[0]}"
# Resolve symlink (wrapper is ln -sfn'd into ~/.openclaw/bin) so SCRIPT_DIR points at the real skill dir.
while [ -L "$SELF" ]; do SELF="$(readlink -f "$SELF")"; done
SCRIPT_DIR="$(cd "$(dirname "$SELF")" && pwd)"

cmd="${1:-}"
if [ $# -gt 0 ]; then shift; fi

case "$cmd" in
  record)                 exec bash "$SCRIPT_DIR/scripts/record.sh" "$@" ;;
  update-metrics)         exec bash "$SCRIPT_DIR/scripts/update-metrics.sh" "$@" ;;
  fetch-metrics)          exec bash "$SCRIPT_DIR/scripts/fetch-and-update-metrics.sh" "$@" ;;
  query)                  exec bash "$SCRIPT_DIR/scripts/query.sh" "$@" ;;
  query-pending)          exec bash "$SCRIPT_DIR/scripts/query-pending.sh" "$@" ;;
  check-published)        exec bash "$SCRIPT_DIR/scripts/check-published.sh" "$@" ;;
  set-distribute-status)  exec bash "$SCRIPT_DIR/scripts/set-distribute-status.sh" "$@" ;;
  get-xhs-user-id)        exec bash "$SCRIPT_DIR/scripts/get-xhs-user-id.sh" "$@" ;;
  init-db)                exec bash "$SCRIPT_DIR/scripts/init-db.sh" "$@" ;;
  migrate-v3)             exec bash "$SCRIPT_DIR/scripts/migrate-v3.sh" "$@" ;;
  *)
    cat >&2 <<'USAGE'
用法: published-track <子命令> [参数...]

子命令:
  record                 发布记录入库（upsert；自动读 dna-meta.json 落 dna_id）
  update-metrics         更新单条/同 folder 记录的互动指标
  fetch-metrics          探活→API 抓取→写库（xhs/bilibili/douyin/kuaishou；wx_mp/wx_channel 不走这里）
  query                  通用查询（--platform [--limit]）
  query-pending          查询待分发内容
  check-published        查某作品是否已发布
  set-distribute-status  设置分发状态
  get-xhs-user-id        获取/缓存 xhs user_id
  init-db                初始化数据库（幂等）
  migrate-v3             迁移到 v3 schema（dna_id/account/perf_evaluated，幂等）

每个子命令支持 --help 或无参调用查看参数（部分子命令）。
USAGE
    exit 1
    ;;
esac
