#!/usr/bin/env python3
"""detect-bump-signals.py — 结构化 bump 信号检测

扫描所有已复盘作品（有 retro.md），比较 rubric 预测分 vs 实际互动表现，
按维度统计同向偏差。≥3 次同向 → bump 信号。

归一化方案：各平台互动总量（reads+likes+comments+shares+favorites+plays+views）
经 log 桶映射到 0-5 actual_score，与 dimension score（0-5）同量纲比较。

Usage:
    python3 detect-bump-signals.py                # 默认阈值 3
    python3 detect-bump-signals.py --threshold 5  # 改阈值
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sqlite3
import sys
from pathlib import Path

# ── 路径 ─────────────────────────────────────────────────────────────────────

ROOT = Path(
    os.environ.get(
        "CALIBRATOR_ROOT",
        Path(__file__).resolve().parent.parent.parent.parent,  # scripts/ → skill/ → skills/ → crew root
    )
).expanduser()
DB = ROOT / "db" / "published_track.db"
CALIBRATION_DIR = ROOT / "calibration"

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


# ── 数据采集 ──────────────────────────────────────────────────────────────────

def find_retroed_works() -> list[dict]:
    """扫描所有有 retro.md 的作品，返回 [{work_dir, source_folder, score_json}]。"""
    works = []
    for kind in ("output_articles", "output_videos"):
        base = ROOT / kind
        if not base.exists():
            continue
        for score_json in base.rglob("calibration/score.json"):
            cal_dir = score_json.parent
            retro_path = cal_dir / "retro.md"
            if not retro_path.exists():
                continue
            work_dir = cal_dir.parent
            source_folder = str(work_dir.relative_to(ROOT))
            try:
                scores = json.loads(score_json.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            works.append({
                "source_folder": source_folder,
                "score_json": scores,
                "retro_path": str(retro_path),
            })
    return works


def get_platform_metrics(source_folder: str) -> dict[str, dict]:
    """从 DB 查该 work 在各平台的互动指标。返回 {platform: {metric: value}}。"""
    if not DB.exists():
        return {}
    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            row[0] for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pub_%'"
            )
        ]
        result = {}
        for table in tables:
            platform = table.removeprefix("pub_")
            # 动态获取列名
            cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
            metric_cols = sorted(METRIC_COLUMNS & set(cols))
            if not metric_cols:
                continue
            col_list = ", ".join(f"COALESCE({c}, 0) AS {c}" for c in metric_cols)
            cur = conn.execute(
                f"SELECT id, {col_list} FROM {table} WHERE source_folder = ?",
                (source_folder,),
            )
            rows = cur.fetchall()
            if not rows:
                continue
            # 取所有行的指标求和（同 work 在同平台可能有多条记录）
            metrics = {c: 0 for c in metric_cols}
            for row in rows:
                for c in metric_cols:
                    metrics[c] += row[c] or 0
            result[platform] = metrics
        return result
    finally:
        conn.close()


def get_dimension_scores(score_json: dict) -> dict[str, int]:
    """从 score.json 提取 7 维分。

    score.json 格式：{"scores": {"ER": 3, "HP": 4, ...}, "composite": 6.71, ...}
    """
    raw = score_json.get("scores", score_json)  # 兼容扁平结构
    scores = {}
    for dim in DIMENSIONS:
        upper = dim.upper()
        val = raw.get(upper) or raw.get(dim) or raw.get(f"cal_score_{dim}")
        if val is not None:
            scores[dim] = int(val)
    return scores


# ── 偏差检测 ──────────────────────────────────────────────────────────────────

def detect_bias(dim_scores: dict[str, int], actual_score: int) -> list[dict]:
    """比较单组维度分 vs 实际表现，返回偏差信号列表。

    高估：维度分 ≥3 但实际 ≤2
    低估：维度分 ≤2 但实际 ≥3
    """
    signals = []
    for dim, score in dim_scores.items():
        if score >= SCORE_HIGH and actual_score <= ACTUAL_LOW:
            signals.append({"dimension": dim, "direction": "overestimate", "dim_score": score, "actual_score": actual_score})
        elif score <= SCORE_LOW and actual_score >= ACTUAL_HIGH:
            signals.append({"dimension": dim, "direction": "underestimate", "dim_score": score, "actual_score": actual_score})
    return signals


def analyze(threshold: int) -> dict:
    """主分析：扫描所有已复盘作品，检测 bump 信号。"""
    works = find_retroed_works()
    if not works:
        return {"analyzed": 0, "data_points": 0, "signals": [], "recommend_bump": False}

    # 收集所有偏差信号（per work × platform）
    all_biases = []  # [{dimension, direction, work, platform, dim_score, actual_score, total_engagement}]
    data_points = 0

    for work in works:
        dim_scores = get_dimension_scores(work["score_json"])
        if not dim_scores:
            continue
        composite = work["score_json"].get("composite")

        platform_metrics = get_platform_metrics(work["source_folder"])
        for platform, metrics in platform_metrics.items():
            total_engagement = sum(v for v in metrics.values() if v and v > 0)
            actual_score = engagement_to_score(total_engagement)
            data_points += 1

            biases = detect_bias(dim_scores, actual_score)
            for b in biases:
                all_biases.append({
                    **b,
                    "work": work["source_folder"],
                    "platform": platform,
                    "total_engagement": total_engagement,
                    "composite": composite,
                })

    # 聚合：按 dimension + direction 统计
    signal_map: dict[str, dict] = {}
    for b in all_biases:
        key = f"{b['dimension']}:{b['direction']}"
        if key not in signal_map:
            signal_map[key] = {
                "dimension": b["dimension"],
                "dimension_label": DIMENSION_LABELS.get(b["dimension"], b["dimension"]),
                "direction": b["direction"],
                "count": 0,
                "examples": [],
            }
        sig = signal_map[key]
        sig["count"] += 1
        if len(sig["examples"]) < 10:  # 最多保留 10 个例子
            sig["examples"].append({
                "work": b["work"],
                "platform": b["platform"],
                "dim_score": b["dim_score"],
                "actual_score": b["actual_score"],
                "total_engagement": b["total_engagement"],
                "composite": b["composite"],
            })

    # 标记触发的信号
    signals = sorted(signal_map.values(), key=lambda s: s["count"], reverse=True)
    triggered = []
    for sig in signals:
        sig["threshold"] = threshold
        sig["triggered"] = sig["count"] >= threshold
        if sig["triggered"]:
            triggered.append(sig)

    return {
        "analyzed": len(works),
        "data_points": data_points,
        "signals": signals,
        "triggered_signals": triggered,
        "recommend_bump": len(triggered) > 0,
    }


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="detect-bump-signals",
        description="结构化 bump 信号检测",
    )
    parser.add_argument("--threshold", type=int, default=3, help="同向偏差触发阈值（默认 3）")
    args = parser.parse_args()

    result = analyze(args.threshold)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
