#!/usr/bin/env python3
"""validate-rubric.py — 新 rubric 公式合格性验证

对比新旧公式在同一批作品上的偏差信号数。新公式偏差信号降幅 ≥ 阈值 → pass。

工作方式：
1. 从 DB 查最新发布且有数据的 N 篇作品的旧分数 + 实际指标 → 算旧偏差信号数
2. 读 Agent 批量重打的新分数（JSON 文件，由 blind sub-agent 产出）
3. 用同一归一化逻辑算新偏差信号数
4. 降幅 = (old - new) / old ≥ 阈值（默认 30%）→ pass=true

Usage:
    python3 validate-rubric.py --new-scores /tmp/new-scores.json
    python3 validate-rubric.py --new-scores /tmp/new-scores.json --reduction-threshold 0.3

new-scores.json 格式：
[
  {"source_folder": "output_articles/xxx", "scores": {"er":3,"hp":4,"sr":2,"ql":4,"na":3,"ab":4,"pv":3}},
  ...
]
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

# ── 路径 ─────────────────────────────────────────────────────────────────────

ROOT = Path(
    os.environ.get(
        "PUBLISHED_TRACK_ROOT",
        Path(__file__).resolve().parent.parent.parent.parent,
    )
).expanduser()
DB = ROOT / "db" / "published_track.db"

# ── 常量（与 detect-bump-signals.py 一致）─────────────────────────────────────

DIMENSIONS = ["er", "hp", "sr", "ql", "na", "ab", "pv"]

METRIC_COLUMNS = {
    "reads", "likes", "comments", "shares", "favorites",
    "plays", "views", "danmaku", "coins", "upvotes",
    "impressions", "reach", "saves", "retweets", "replies",
    "bookmarks", "reposts",
}

SCORE_HIGH = 3
SCORE_LOW = 2
ACTUAL_HIGH = 3
ACTUAL_LOW = 2


# ── 归一化（与 detect-bump-signals.py 一致）──────────────────────────────────

def engagement_to_score(total: int) -> int:
    if total <= 0:
        return 0
    elif total <= 10:
        return 1
    elif total <= 50:
        return 2
    elif total <= 200:
        return 3
    elif total <= 1000:
        return 4
    else:
        return 5


def count_bias_signals(dim_scores: dict[str, int], actual_score: int) -> int:
    """返回偏差信号数（高估 + 低估）。"""
    count = 0
    for dim, score in dim_scores.items():
        if score >= SCORE_HIGH and actual_score <= ACTUAL_LOW:
            count += 1
        elif score <= SCORE_LOW and actual_score >= ACTUAL_HIGH:
            count += 1
    return count


# ── DB 查询 ──────────────────────────────────────────────────────────────────

def get_all_platform_tables(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pub_%'"
    )]


def get_metric_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    return sorted(METRIC_COLUMNS & set(cols))


def query_work_metrics(conn: sqlite3.Connection, source_folders: set[str]) -> dict[str, list[dict]]:
    """查各 work 在各平台的互动指标。返回 {source_folder: [{platform, total_engagement, actual_score}]}"""
    tables = get_all_platform_tables(conn)
    result: dict[str, list[dict]] = {sf: [] for sf in source_folders}

    for table in tables:
        platform = table.removeprefix("pub_")
        metric_cols = get_metric_columns(conn, table)
        if not metric_cols:
            continue
        col_list = ", ".join(f"COALESCE({c}, 0) AS {c}" for c in metric_cols)
        placeholders = ",".join("?" * len(source_folders))
        rows = conn.execute(
            f"SELECT source_folder, {col_list} FROM {table} WHERE source_folder IN ({placeholders})",
            list(source_folders),
        ).fetchall()
        for row in rows:
            sf = row[0]
            total = sum(row[i] or 0 for i in range(1, len(metric_cols) + 1))
            actual_score = engagement_to_score(total)
            result[sf].append({
                "platform": platform,
                "total_engagement": total,
                "actual_score": actual_score,
            })

    return result


def get_old_scores(conn: sqlite3.Connection, source_folders: set[str]) -> dict[str, dict[str, int]]:
    """从 DB 查各 work 的旧 cal_score_* 分数。返回 {source_folder: {er:3, hp:4, ...}}"""
    tables = get_all_platform_tables(conn)
    result: dict[str, dict[str, int]] = {}

    for table in tables:
        placeholders = ",".join("?" * len(source_folders))
        rows = conn.execute(
            f"""SELECT source_folder, cal_score_er, cal_score_hp, cal_score_sr,
                       cal_score_ql, cal_score_na, cal_score_ab, cal_score_pv
                FROM {table}
                WHERE source_folder IN ({placeholders}) AND cal_score_er IS NOT NULL
                GROUP BY source_folder""",
            list(source_folders),
        ).fetchall()
        for row in rows:
            sf = row[0]
            if sf not in result:  # 取第一个有分数的记录
                result[sf] = {}
                for i, dim in enumerate(DIMENSIONS):
                    val = row[i + 1]
                    if val is not None:
                        result[sf][dim] = int(val)

    return result


# ── 主逻辑 ───────────────────────────────────────────────────────────────────

def validate(new_scores_path: str, sample_size: int, reduction_threshold: float) -> dict:
    # 读新分数
    new_scores_data = json.loads(Path(new_scores_path).read_text(encoding="utf-8"))
    source_folders = {item["source_folder"] for item in new_scores_data}

    if len(source_folders) < 3:
        return {"pass": False, "reason": f"样本不足：仅 {len(source_folders)} 篇，最少需要 3 篇"}

    if not DB.exists():
        return {"pass": False, "reason": f"DB not found: {DB}"}

    conn = sqlite3.connect(str(DB))
    try:
        # 查各 work 的实际指标
        work_metrics = query_work_metrics(conn, source_folders)

        # 查旧分数
        old_scores = get_old_scores(conn, source_folders)

        # 算旧公式偏差信号数
        old_signal_count = 0
        old_data_points = 0
        for sf, metrics_list in work_metrics.items():
            if sf not in old_scores:
                continue
            for m in metrics_list:
                old_data_points += 1
                old_signal_count += count_bias_signals(old_scores[sf], m["actual_score"])

        # 算新公式偏差信号数
        new_scores_map = {item["source_folder"]: item["scores"] for item in new_scores_data}
        new_signal_count = 0
        new_data_points = 0
        for sf, metrics_list in work_metrics.items():
            if sf not in new_scores_map:
                continue
            for m in metrics_list:
                new_data_points += 1
                new_signal_count += count_bias_signals(new_scores_map[sf], m["actual_score"])

        # 判定：降幅 ≥ 阈值 → pass
        reduction = old_signal_count - new_signal_count
        if old_signal_count == 0:
            passed = False
            reason = "旧公式偏差信号数已为 0，无升级必要"
            reduction_ratio = 0.0
        else:
            reduction_ratio = reduction / old_signal_count
            passed = reduction_ratio >= reduction_threshold
            if passed:
                reason = f"偏差信号降幅 {reduction_ratio:.0%} ≥ 阈值 {reduction_threshold:.0%}"
            else:
                reason = f"偏差信号降幅 {reduction_ratio:.0%} < 阈值 {reduction_threshold:.0%}"

        return {
            "pass": passed,
            "sample_size": len(source_folders),
            "old_signals": old_signal_count,
            "new_signals": new_signal_count,
            "old_data_points": old_data_points,
            "new_data_points": new_data_points,
            "reduction": reduction,
            "reduction_ratio": round(reduction_ratio, 4),
            "reduction_threshold": reduction_threshold,
            "reason": reason,
        }
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="validate-rubric",
        description="新 rubric 公式合格性验证",
    )
    parser.add_argument("--new-scores", required=True, help="新分数 JSON 文件路径")
    parser.add_argument("--sample-size", type=int, default=10, help="验证样本数（默认 10）")
    parser.add_argument(
        "--reduction-threshold",
        type=float,
        default=0.3,
        help="偏差信号降幅阈值（默认 0.3=30%%，新公式信号数需 ≤ 旧 × (1-阈值)）",
    )
    args = parser.parse_args()

    result = validate(args.new_scores, args.sample_size, args.reduction_threshold)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    sys.exit(main())
