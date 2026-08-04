#!/usr/bin/env python3
"""query-retro-pending.py — 一键扫描待复盘作品 + 带出互动数据

扫描所有 cal_enabled=1 的已发布内容，筛选出满足复盘条件的作品：
  - 有 prediction.md 且无 retro.md
  - 已过 T+N 天窗口（publish_date + N 天 < now，默认 N=3）

输出 JSON 数组，每项含 source_folder、title、prediction_path、cal 预测分、
各平台互动数据。Agent 拿到后直接对比预测 vs 实际 → 写 retro.md，无需再查 DB / ls 目录。

Usage:
    python3 query-retro-pending.py                # 默认 T+3d
    python3 query-retro-pending.py --days 5       # T+5d 窗口
    python3 query-retro-pending.py --min-count 5  # 仅当 ≥5 条待复盘时才输出（默认 1）
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta
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

# 各平台互动指标列名（动态检测，这里做白名单过滤）
METRIC_COLUMNS = {
    "reads", "likes", "comments", "shares", "favorites",
    "plays", "views", "danmaku", "coins", "upvotes",
    "impressions", "reach", "saves", "retweets", "replies",
    "bookmarks", "reposts",
}

# cal 预测分列
CAL_SCORE_COLUMNS = {
    "cal_composite", "cal_score_er", "cal_score_hp", "cal_score_sr",
    "cal_score_ql", "cal_score_na", "cal_score_ab", "cal_score_pv",
    "cal_rubric_version",
}


# ── DB 查询 ──────────────────────────────────────────────────────────────────

def get_platform_tables(conn: sqlite3.Connection) -> list[str]:
    """返回所有 pub_* 表名"""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'pub_%'"
    )
    return [row[0] for row in cur.fetchall()]


def get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """返回表的列名列表"""
    cur = conn.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]


def query_cal_enabled_rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    """查某平台表里所有 cal_enabled=1 的行"""
    columns = get_columns(conn, table)
    col_list = ", ".join(columns)
    cur = conn.execute(
        f"SELECT {col_list} FROM {table} WHERE cal_enabled = 1"
    )
    return [dict(zip(columns, row)) for row in cur.fetchall()]


# ── 复盘条件检查 ──────────────────────────────────────────────────────────────

def is_pending_retro(source_folder: str, publish_date: str, days: int) -> tuple[bool, str | None]:
    """检查是否待复盘：有 prediction.md、无 retro.md、过 T+Nd 窗口。

    返回 (is_pending, prediction_path_or_none)。
    """
    work_dir = ROOT / source_folder
    calibration_dir = work_dir / "calibration"
    prediction_path = calibration_dir / "prediction.md"
    retro_path = calibration_dir / "retro.md"

    # 必须有 prediction.md
    if not prediction_path.exists():
        return False, None
    # 不能已有 retro.md
    if retro_path.exists():
        return False, None
    # T+Nd 窗口
    try:
        pub_dt = datetime.strptime(publish_date, "%Y-%m-%d")
    except ValueError:
        return False, None
    if datetime.now() < pub_dt + timedelta(days=days):
        return False, None

    return True, str(prediction_path)


# ── 主逻辑 ───────────────────────────────────────────────────────────────────

def scan_pending(days: int) -> list[dict]:
    """扫描所有待复盘作品，返回 JSON 可序列化的列表。"""
    if not DB.exists():
        return []

    conn = sqlite3.connect(str(DB))
    conn.row_factory = sqlite3.Row
    try:
        tables = get_platform_tables(conn)
        if not tables:
            return []

        # 收集所有 cal_enabled=1 的行，按 source_folder 分组
        # source_folder → { platform → {metrics + cal_scores + id + title + publish_date} }
        works: dict[str, dict] = {}

        for table in tables:
            platform = table.removeprefix("pub_")
            columns = set(get_columns(conn, table))
            metric_cols = sorted(METRIC_COLUMNS & columns)
            cal_cols = sorted(CAL_SCORE_COLUMNS & columns)

            for row in query_cal_enabled_rows(conn, table):
                folder = row["source_folder"]
                if not folder:
                    continue

                # 互动指标
                metrics = {col: row[col] for col in metric_cols if row[col] is not None}
                # cal 预测分
                cal_scores = {col: row[col] for col in cal_cols if row[col] is not None}

                entry = {
                    "id": row["id"],
                    "title": row["title"],
                    "publish_date": row["publish_date"],
                    "publish_url": row.get("publish_url"),
                    "metrics": metrics,
                }

                if folder not in works:
                    works[folder] = {
                        "source_folder": folder,
                        "title": row["title"],  # 取第一个见到的 title
                        "publish_date": row["publish_date"],
                        "platforms": {},
                        "cal_scores": cal_scores,
                    }
                else:
                    # 同一 source_folder 多平台：取最新 publish_date
                    if row["publish_date"] > works[folder]["publish_date"]:
                        works[folder]["publish_date"] = row["publish_date"]
                        works[folder]["title"] = row["title"]
                    # cal_scores 取有 composite 的那个
                    if "cal_composite" in cal_scores and "cal_composite" not in works[folder]["cal_scores"]:
                        works[folder]["cal_scores"] = cal_scores

                works[folder]["platforms"][platform] = entry

        # 过滤：只保留待复盘的（有 prediction.md、无 retro.md、过 T+Nd）
        pending = []
        for folder, work in works.items():
            is_pending, pred_path = is_pending_retro(
                folder, work["publish_date"], days
            )
            if is_pending:
                work["prediction_path"] = pred_path
                pending.append(work)

        # 按 publish_date 降序
        pending.sort(key=lambda w: w["publish_date"], reverse=True)
        return pending
    finally:
        conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="query-retro-pending",
        description="扫描待复盘作品 + 带出互动数据",
    )
    parser.add_argument("--days", type=int, default=3, help="T+Nd 窗口（默认 3）")
    parser.add_argument("--min-count", type=int, default=1, help="最少待复盘数才输出（默认 1）")
    args = parser.parse_args()

    pending = scan_pending(args.days)

    if len(pending) < args.min_count:
        json.dump({"total": len(pending), "min_count": args.min_count, "pending": []}, sys.stdout, ensure_ascii=False, indent=2)
    else:
        json.dump({"total": len(pending), "pending": pending}, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
