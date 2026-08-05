#!/usr/bin/env python3
"""detect-bump-signals.py — 结构化 bump 信号检测（纯 DB）

从 published_track.db 读取所有 cal_enabled=1 的记录，对未评估的记录
（cal_bump_evaluated=0）计算偏差信号并写回 cal_bias_signals，
然后聚合全量信号按维度统计同向偏差。≥3 次同向 → bump 信号。
触发 bump 时自动清空 cal_bias_signals（信号已达阈值被消费）；
未触发时保留信号，跨轮累积直到达标。

数据全部来自 DB：cal_score_*（盲打分）+ 互动指标（实测）。
偏差信号 = 纯数学：log 桶归一化 actual → 与 dim score 比较。

Usage:
    python3 detect-bump-signals.py                # 默认阈值 3
    python3 detect-bump-signals.py --threshold 5  # 改阈值
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
        Path(__file__).resolve().parent.parent.parent.parent,  # scripts/ → skill/ → skills/ → crew root
    )
).expanduser()
DB = ROOT / "db" / "published_track.db"

# ── 常量 ─────────────────────────────────────────────────────────────────────

DIMENSIONS = ["er", "hp", "sr", "ql", "na", "ab", "pv"]
DIMENSION_LABELS = {
    "er": "情感共鸣", "hp": "钩子强度", "sr": "社会议题共振",
    "ql": "金句密度", "na": "叙事性", "ab": "受众广度", "pv": "实用价值",
}

# 互动指标列名白名单
METRIC_COLUMNS = {
    "reads", "likes", "comments", "shares", "favorites",
    "plays", "views", "danmaku", "coins", "upvotes",
    "impressions", "reach", "saves", "retweets", "replies",
    "bookmarks", "reposts",
}

# 高/低分阈值
SCORE_HIGH = 3   # dimension score ≥3 = 高分
SCORE_LOW = 2    # dimension score ≤2 = 低分
ACTUAL_HIGH = 3  # actual_score ≥3 = 高表现
ACTUAL_LOW = 2   # actual_score ≤2 = 低表现


# ── 归一化 ───────────────────────────────────────────────────────────────────

def engagement_to_score(total: int) -> int:
    """互动总量 → 0-5 log 桶。

    0 → 0, 1-10 → 1, 11-50 → 2, 51-200 → 3, 201-1000 → 4, 1000+ → 5
    """
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


def detect_bias(dim_scores: dict[str, int], actual_score: int) -> list[dict]:
    """比较维度分 vs 实际表现，返回偏差信号列表。

    高估：维度分 ≥3 但实际 ≤2
    低估：维度分 ≤2 但实际 ≥3
    """
    signals = []
    for dim, score in dim_scores.items():
        if score >= SCORE_HIGH and actual_score <= ACTUAL_LOW:
            signals.append({"dim": dim, "dir": "overestimate", "dim_score": score, "actual_score": actual_score})
        elif score <= SCORE_LOW and actual_score >= ACTUAL_HIGH:
            signals.append({"dim": dim, "dir": "underestimate", "dim_score": score, "actual_score": actual_score})
    return signals


# ── DB 操作 ──────────────────────────────────────────────────────────────────

def get_all_platform_tables(conn: sqlite3.Connection) -> list[str]:
    """返回所有 pub_* 表名。"""
    return [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pub_%'"
    )]


def get_metric_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """获取该表的互动指标列名。"""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
    return sorted(METRIC_COLUMNS & set(cols))


def process_new_records(conn: sqlite3.Connection) -> int:
    """处理所有 cal_bump_evaluated=0 的记录：算偏差信号 → 写回 DB。

    返回处理的记录数。
    """
    tables = get_all_platform_tables(conn)
    processed = 0

    for table in tables:
        platform = table.removeprefix("pub_")
        metric_cols = get_metric_columns(conn, table)
        if not metric_cols:
            continue

        # 无分数的记录直接标记已评估（避免重复查询）
        conn.execute(
            f"UPDATE {table} SET cal_bump_evaluated = 1 "
            f"WHERE cal_enabled = 1 AND cal_bump_evaluated = 0 AND cal_score_er IS NULL"
        )

        # 查未评估且有分数的记录
        col_select = ", ".join(f"COALESCE({c}, 0) AS {c}" for c in metric_cols)
        rows = conn.execute(
            f"""SELECT id, source_folder, cal_score_er, cal_score_hp, cal_score_sr,
                       cal_score_ql, cal_score_na, cal_score_ab, cal_score_pv,
                       cal_composite, {col_select}
                FROM {table}
                WHERE cal_enabled = 1
                  AND cal_bump_evaluated = 0
                  AND cal_score_er IS NOT NULL"""
        ).fetchall()

        for row in row_to_dict(conn, table, metric_cols, rows):
            dim_scores = {}
            for dim in DIMENSIONS:
                val = row.get(f"cal_score_{dim}")
                if val is not None:
                    dim_scores[dim] = int(val)
            if not dim_scores:
                continue

            total_engagement = sum(row.get(c, 0) or 0 for c in metric_cols)
            actual_score = engagement_to_score(total_engagement)
            biases = detect_bias(dim_scores, actual_score)

            signals_json = json.dumps(biases, ensure_ascii=False) if biases else None
            conn.execute(
                f"UPDATE {table} SET cal_bias_signals = ?, cal_bump_evaluated = 1 WHERE id = ?",
                (signals_json, row["id"]),
            )
            processed += 1

    conn.commit()
    return processed


def row_to_dict(conn, table, metric_cols, rows):
    """将 sqlite3.Row 列表转为 dict 列表。"""
    result = []
    for row in rows:
        d = dict(row)
        result.append(d)
    return result


def aggregate_signals(conn: sqlite3.Connection, threshold: int) -> dict:
    """聚合所有 cal_bias_signals IS NOT NULL 的记录，按维度+方向统计。"""
    tables = get_all_platform_tables(conn)
    all_signals = []  # [{dim, dir, dim_score, actual_score, platform, source_folder, composite}]

    for table in tables:
        platform = table.removeprefix("pub_")
        rows = conn.execute(
            f"""SELECT source_folder, cal_composite, cal_bias_signals
                FROM {table}
                WHERE cal_bias_signals IS NOT NULL"""
        ).fetchall()
        for row in rows:
            try:
                signals = json.loads(row[2])  # row[2] = cal_bias_signals
            except (json.JSONDecodeError, TypeError):
                continue
            for s in signals:
                all_signals.append({
                    "dim": s["dim"],
                    "dir": s["dir"],
                    "dim_score": s["dim_score"],
                    "actual_score": s["actual_score"],
                    "platform": platform,
                    "source_folder": row[0],  # row[0] = source_folder
                    "composite": row[1],      # row[1] = cal_composite
                })

    if not all_signals:
        return {"data_points": 0, "signals": [], "triggered_signals": [], "recommend_bump": False}

    # 聚合：按 dim + dir 统计
    signal_map: dict[str, dict] = {}
    for s in all_signals:
        key = f"{s['dim']}:{s['dir']}"
        if key not in signal_map:
            signal_map[key] = {
                "dimension": s["dim"],
                "dimension_label": DIMENSION_LABELS.get(s["dim"], s["dim"]),
                "direction": s["dir"],
                "count": 0,
                "platforms": {},
                "examples": [],
            }
        sig = signal_map[key]
        sig["count"] += 1

        # 平台分布
        p = s["platform"]
        sig["platforms"][p] = sig["platforms"].get(p, 0) + 1

        # 例子（最多 10 个）
        if len(sig["examples"]) < 10:
            sig["examples"].append({
                "work": s["source_folder"],
                "platform": p,
                "dim_score": s["dim_score"],
                "actual_score": s["actual_score"],
                "composite": s["composite"],
            })

    # 标记触发
    signals = sorted(signal_map.values(), key=lambda x: x["count"], reverse=True)
    triggered = []
    for sig in signals:
        sig["threshold"] = threshold
        sig["triggered"] = sig["count"] >= threshold
        if sig["triggered"]:
            triggered.append(sig)

    return {
        "data_points": len(all_signals),
        "signals": signals,
        "triggered_signals": triggered,
        "recommend_bump": len(triggered) > 0,
    }


def clear_signals(conn: sqlite3.Connection) -> None:
    """聚合后清空所有 cal_bias_signals（信号已被消费，不再重复触发）。"""
    for table in get_all_platform_tables(conn):
        conn.execute(f"UPDATE {table} SET cal_bias_signals = NULL WHERE cal_bias_signals IS NOT NULL")
    conn.commit()


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="detect-bump-signals",
        description="结构化 bump 信号检测（纯 DB）",
    )
    parser.add_argument("--threshold", type=int, default=3, help="同向偏差触发阈值（默认 3）")
    args = parser.parse_args()

    if not DB.exists():
        json.dump({"error": f"DB not found: {DB}"}, sys.stdout, ensure_ascii=False)
        sys.stdout.write("\n")
        return 1

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        processed = process_new_records(conn)
        result = aggregate_signals(conn, args.threshold)
        result["newly_processed"] = processed
        # 只有触发 bump（信号已达阈值被消费）才清空；
        # 未触发时信号保留在 DB 里，跨轮累积直到达标
        if result["recommend_bump"]:
            clear_signals(conn)
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
