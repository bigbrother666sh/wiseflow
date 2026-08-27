#!/usr/bin/env python3
"""xhs_engagement.py - 小红书 creator 后台互动数抓取（纯取数，不碰 DB）

通过 camoufox-cli + xhs-browse 持久化 session 打开 creator 创作服务平台
「笔记管理」页，eval 解析 `.note-card__body` 拿标题 + 5 列互动数
（阅读/评论/点赞/收藏/分享），按 title 匹配目标笔记。

CLI 形态：
    check                判 creator 后台登录态（exit 0 就位 / exit 2 失效）
    list                 列出 creator 后台所有笔记 + 5 列互动数
    fetch --row-id <id>  抓单条（从 pub_xhs 取该行 title 匹配 → update-metrics.sh 写库）
    fetch --title <t>    纯取数调试入口（按 title 匹配，只输出 JSON 不写库）
    fetch-all            批量刷新（打开首页一次，解析页内全部笔记，匹配 pub_xhs
                         全部行写库；不翻页，首页没有的行报 unmatched 跳过）
    probe                dump 截图/DOM/解析 JSON 到 ./xhs-engagement-probe/

登录态（本 skill 不自管，只消费 session profile）：
- www 消费者域：login-manager 管（导出 xhs-browse.json 给 raw HTTP 下游）
- creator 创作者域 SSO：xhs-publish login-verify 管（导出 xhs-publish.json）
- 本 skill 复用 xhs-browse 持久化 session 的 profile 登录态，
  不导出 cookie、不开独立 session、不 import cookie。

依赖：
- camoufox-cli（npm 全局）
- published-track skill（同 crew 私有，写库走它的 update-metrics.sh）
- python3 stdlib
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

# ── 常量 ─────────────────────────────────────────────────────────────────────

PLATFORM = "xhs"
SESSION_NAME = "xhs-browse"  # 复用 login-manager/xhs-publish 共享的持久化 session

NOTE_MANAGER_URL = "https://creator.xiaohongshu.com/new/note-manager?source=official"

CAMOUFOX_BIN = os.environ.get("CAMOUFOX_CLI", "camoufox-cli")
FETCH_TIMEOUT_S = 30
CARD_WAIT_MAX_S = 15      # open 后等笔记卡片出现的上限
CARD_POLL_INTERVAL_S = 1

# spike dump 输出目录
PROBE_OUT_DIR = Path(
    os.environ.get("PROBE_OUT_DIR", "./xhs-engagement-probe")
).expanduser()

# published-track DB / 写库脚本（与 wx-mp-engagement 同一约定：本 skill 查 title + 写库，
# 写库委托 published-track 的 update-metrics.sh，不直接 SQL 写）
PUBLISHED_TRACK_DB = Path(
    os.environ.get(
        "PUBLISHED_TRACK_DB",
        "~/.openclaw/workspace-main/db/published_track.db",
    )
).expanduser()
PUBLISHED_TRACK_SCRIPTS = Path(
    os.environ.get(
        "PUBLISHED_TRACK_SCRIPTS",
        "~/.openclaw/workspace-main/skills/published-track/scripts",
    )
).expanduser()
UPDATE_METRICS_SH = PUBLISHED_TRACK_SCRIPTS / "update-metrics.sh"


# ── camoufox-cli 集成 ────────────────────────────────────────────────────────

def camoufox_run(args: list[str], *, timeout: int = FETCH_TIMEOUT_S) -> subprocess.CompletedProcess:
    # --persistent 固定带：所有 camoufox-cli 命令复用同一 daemon + 同一 profile，
    # 避免每次命令重起 daemon 不带 profile（cookie/登录态不恢复）+ 多 daemon
    # 同 session 冲突互杀（SIGKILL）。--persistent 是 per-call flag，必须每次都带。
    cmd = [CAMOUFOX_BIN, "--persistent", "--json"] + args
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def camoufox_open(url: str) -> None:
    """打开 URL。camoufox-cli 默认 headless，不需要 --headless 参数。"""
    result = camoufox_run(["--session", SESSION_NAME, "open", url], timeout=90)
    if result.returncode != 0:
        raise RuntimeError(f"camoufox-cli open failed: {result.stderr.strip()}")


def camoufox_eval(expr: str) -> str:
    """在 session 内 eval JS，返回字符串结果"""
    result = camoufox_run(["--session", SESSION_NAME, "eval", expr])
    if result.returncode != 0:
        return ""
    try:
        env = json.loads(result.stdout)
        data = env.get("data", "")
        if isinstance(data, dict) and "result" in data:
            # camoufox-cli eval 返回 {data: {result: "..."}}
            return data["result"]
        return data if isinstance(data, str) else json.dumps(data)
    except json.JSONDecodeError:
        return result.stdout


def camoufox_get_url() -> str:
    """获取当前页面 URL"""
    result = camoufox_run(["--session", SESSION_NAME, "url"])
    if result.returncode != 0:
        return ""
    try:
        env = json.loads(result.stdout)
        return env.get("data", {}).get("url", "")
    except json.JSONDecodeError:
        return ""


def camoufox_screenshot(out_path: Path) -> bool:
    """截图。camoufox-cli 语法：screenshot <file>，不需要 --path。"""
    result = camoufox_run(
        ["--session", SESSION_NAME, "screenshot", str(out_path)],
        timeout=FETCH_TIMEOUT_S,
    )
    return result.returncode == 0


def camoufox_close() -> None:
    """关闭 camoufox session——登录态在磁盘 profile，不留进程占内存"""
    camoufox_run(["--session", SESSION_NAME, "close"], timeout=10)


# ── 平台行查询 / 写库（published-track 委托）─────────────────────────────────

def lookup_published_row(row_id: int) -> dict | None:
    if not PUBLISHED_TRACK_DB.exists():
        return None
    conn = sqlite3.connect(str(PUBLISHED_TRACK_DB))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, title, publish_url, publish_date, source_folder "
            "FROM pub_xhs WHERE id = ?",
            (row_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_all_xhs_rows() -> list[dict]:
    """取 pub_xhs 全部行（id/title/publish_url）。

    不按日期/指标过滤——后台列表首页本身就是天然窗口：页内有什么解析什么，
    匹配上的行写库，匹配不上的报 unmatched 跳过（老作品不在首页是常态，非错误）。
    """
    if not PUBLISHED_TRACK_DB.exists():
        return []
    conn = sqlite3.connect(str(PUBLISHED_TRACK_DB))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT id, title, publish_url FROM pub_xhs ORDER BY id DESC"
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


def update_metrics_row(row_id: int, metrics: dict) -> dict:
    """写库委托 published-track 的 update-metrics.sh。"""
    if not UPDATE_METRICS_SH.exists():
        return {"ok": False, "error": f"update-metrics.sh not found at {UPDATE_METRICS_SH}"}
    cmd = [
        str(UPDATE_METRICS_SH),
        "--platform", PLATFORM,
        "--id", str(row_id),
        "--views", str(metrics.get("views", 0)),
        "--comments", str(metrics.get("comments", 0)),
        "--likes", str(metrics.get("likes", 0)),
        "--favorites", str(metrics.get("collects", 0)),  # pub_xhs 收藏列叫 favorites
        "--shares", str(metrics.get("shares", 0)),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, check=False)
    if result.returncode != 0:
        return {"ok": False, "error": result.stderr.strip(), "stdout": result.stdout.strip()}
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"ok": True, "stdout": result.stdout.strip()}


# ── creator 后台笔记管理页解析 ───────────────────────────────────────────────

# 页面 DOM 结构：
#   .note-card
#     .note-card__body
#       .note-card__row.note-card__row--header
#         .note-card__title  → 笔记标题
#       .note-card__row.note-card__row--stats
#         .note-card__stat (×5)
#           span  → 互动数（顺序：阅读/评论/点赞/收藏/分享）
_PARSE_JS = r"""
(() => {
  const cards = document.querySelectorAll('.note-card__body');
  const entries = [];
  for (const card of cards) {
    const titleEl = card.querySelector('.note-card__title');
    const title = titleEl ? titleEl.textContent.trim() : '';
    if (!title) continue;
    const statsRow = card.querySelector('.note-card__row--stats');
    if (!statsRow) continue;
    const statEls = statsRow.querySelectorAll('.note-card__stat span');
    const stats = [];
    for (const s of statEls) {
      const num = parseInt((s.textContent || '0').trim().replace(/,/g, ''), 10) || 0;
      stats.push(num);
    }
    entries.push({ title, stats });
  }
  return JSON.stringify(entries);
})()
"""

_COUNT_CARDS_JS = (
    "(() => String(document.querySelectorAll('.note-card__body').length))()"
)


def open_note_manager_and_wait(require_cards: bool = True) -> tuple[list[dict], int]:
    """打开 creator 后台笔记管理页，等笔记卡片加载，返回 (笔记条目列表, 卡片数)。

    require_cards=False（check 用）：只要没跳登录页就算就位，0 卡片也返回空列表
    （新账号无笔记场景不算失效）。

    失败路径：
    - 跳登录页 → SessionExpired（exit 2）
    - require_cards 且超时仍无卡片（非登录页）→ CreatorBackendNoNotes（exit 1）
    """
    camoufox_open(NOTE_MANAGER_URL)

    deadline = time.time() + CARD_WAIT_MAX_S
    card_count = 0
    while time.time() < deadline:
        # 显式跳登录页 → 真失效，不等
        current_url = camoufox_get_url()
        if "login" in current_url:
            raise SessionExpired(f"creator 后台跳登录页（{current_url[:100]}）")
        raw = camoufox_eval(_COUNT_CARDS_JS)
        try:
            card_count = int(raw or "0")
        except ValueError:
            card_count = 0
        if card_count > 0:
            break
        time.sleep(CARD_POLL_INTERVAL_S)

    if card_count == 0:
        # 最后再看一次 URL 区分登录失效 vs 页面异常
        current_url = camoufox_get_url()
        if "login" in current_url:
            raise SessionExpired(f"creator 后台跳登录页（{current_url[:100]}）")
        if require_cards:
            raise CreatorBackendNoNotes(
                "creator 后台未加载到笔记卡片"
                "（可能页面结构变化、账号无笔记、或登录态半失效）"
            )
        return [], 0

    raw = camoufox_eval(_PARSE_JS)
    entries: list[dict] = []
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, str):  # 双重编码兜底
                data = json.loads(data)
            if isinstance(data, list):
                entries = [e for e in data if isinstance(e, dict) and e.get("title")]
        except json.JSONDecodeError:
            raise CreatorBackendParseFailed(
                f"解析 creator 后台 eval 返回 JSON 失败: {raw[:200]}"
            )
    if require_cards and not entries:
        raise CreatorBackendParseFailed(
            f"页面有 {card_count} 个卡片但解析到 0 条笔记（DOM 结构可能改版，跑 probe 排查）"
        )
    return entries, card_count


# ── 错误类型（main 里映射到 exit code）───────────────────────────────────────

class SessionExpired(Exception):
    """creator 后台跳登录页——xhs-browse session 登录态失效，exit 2"""


class CreatorBackendNoNotes(Exception):
    """页面打开正常但没加载到笔记卡片，exit 1"""


class CreatorBackendParseFailed(Exception):
    """卡片在但解析失败（DOM 改版），exit 1"""


# ── title 匹配 ───────────────────────────────────────────────────────────────

def normalize_title(s: str) -> str:
    """标题归一化：折叠空白（含全角空格）、去尾部省略号（后台 displayTitle 可能截断）"""
    return re.sub(r"[\s　]+", " ", s).strip().rstrip(".…").rstrip()


def match_note_by_title(entries: list[dict], target_title: str) -> dict | None:
    """按标题找唯一匹配：精确相等优先，其次前缀互含（防截断，最短 6 字符起）。
    多条歧义时返回 None（宁可失败也不错配）。"""
    target = normalize_title(target_title)
    if not target:
        return None
    exact = [e for e in entries if normalize_title(e.get("title", "")) == target]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        return None
    prefix = [
        e for e in entries
        if len(normalize_title(e.get("title", ""))) >= 6
        and len(target) >= 6
        and (
            normalize_title(e["title"]).startswith(target)
            or target.startswith(normalize_title(e["title"]))
        )
    ]
    return prefix[0] if len(prefix) == 1 else None


def stats_to_metrics(stats: list[int]) -> dict:
    """creator 后台 stats 区 5 列数字顺序：阅读/评论/点赞/收藏/分享。"""
    padded = (stats + [0] * 5)[:5]
    return {
        "views": padded[0],
        "comments": padded[1],
        "likes": padded[2],
        "collects": padded[3],
        "shares": padded[4],
    }


# ── 输出 / 退出 ──────────────────────────────────────────────────────────────

def print_json(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


def err_exit(error: str, msg: str, code: int = 1) -> None:
    sys.stderr.write(f"error: {msg}\n")
    print_json({"ok": False, "platform": PLATFORM, "error": error, "msg": msg})
    sys.exit(code)


# ── CLI 子命令 ───────────────────────────────────────────────────────────────

def cmd_check(args) -> None:
    """判 creator 后台登录态：打开笔记管理页不跳登录页 = 就位（0 笔记的新账号也算就位）"""
    try:
        entries, _ = open_note_manager_and_wait(require_cards=False)
    except SessionExpired as e:
        err_exit("SESSION_EXPIRED", str(e), 2)
    except (CreatorBackendNoNotes, CreatorBackendParseFailed, RuntimeError) as e:
        err_exit(type(e).__name__.upper(), str(e), 1)
    finally:
        camoufox_close()
    print_json({
        "ok": True,
        "platform": PLATFORM,
        "notes_found": len(entries),
        "message": "creator 后台登录态就位",
    })


def cmd_list(args) -> None:
    """列出 creator 后台所有笔记 + 5 列互动数"""
    try:
        entries, _ = open_note_manager_and_wait()
    except SessionExpired as e:
        err_exit("SESSION_EXPIRED", str(e), 2)
    except (CreatorBackendNoNotes, CreatorBackendParseFailed, RuntimeError) as e:
        err_exit(type(e).__name__.upper(), str(e), 1)
    finally:
        camoufox_close()
    print_json({
        "ok": True,
        "platform": PLATFORM,
        "total": len(entries),
        "notes": [
            {"title": e["title"], "metrics": stats_to_metrics(e.get("stats", []))}
            for e in entries
        ],
    })


def cmd_fetch(args) -> None:
    """抓单条：--row-id 走完整链路（查 title → 取数 → 写库）；--title 纯取数调试（不写库）"""
    row: dict | None = None
    if args.row_id:
        row = lookup_published_row(args.row_id)
        if row is None:
            err_exit("ROW_NOT_FOUND", f"pub_xhs id={args.row_id} not found（或 DB 未初始化：{PUBLISHED_TRACK_DB}）", 1)
        target_title = row.get("title") or ""
        if not target_title:
            err_exit("ROW_TITLE_EMPTY", f"pub_xhs id={args.row_id} 的 title 为空，无法按标题匹配", 1)
    else:
        target_title = args.title

    try:
        entries, _ = open_note_manager_and_wait()
    except SessionExpired as e:
        err_exit("SESSION_EXPIRED", str(e), 2)
    except (CreatorBackendNoNotes, CreatorBackendParseFailed, RuntimeError) as e:
        err_exit(type(e).__name__.upper(), str(e), 1)
    finally:
        camoufox_close()

    matched = match_note_by_title(entries, target_title)
    if matched is None:
        err_exit(
            "NOTE_NOT_IN_CREATOR_BACKEND",
            f"creator 后台未匹配到该笔记（共 {len(entries)} 条，"
            f"title={target_title[:40]!r}；笔记可能已删除/审核未通过/私密）",
            1,
        )
    metrics = stats_to_metrics(matched.get("stats", []))

    result = {
        "ok": True,
        "platform": PLATFORM,
        "title": target_title,
        "matched_title": matched["title"],
        "metrics": metrics,
    }
    if row is not None:
        result["row_id"] = row["id"]
        result["publish_url"] = row.get("publish_url")
        result["update"] = update_metrics_row(row["id"], metrics)
    print_json(result)


def cmd_fetch_all(args) -> None:
    """批量刷新：打开首页一次，解析页内全部笔记，匹配 pub_xhs 全部行写库。

    不翻页——首页本身就是天然窗口：页内有什么解析什么，匹配上的行写库，
    匹配不上的报 unmatched 跳过（老作品不在首页是常态，非错误）。
    少操作一次页面就少一次风控暴露。
    """
    rows = list_all_xhs_rows()
    if not rows:
        print_json({"ok": True, "platform": PLATFORM, "total": 0, "matched": 0, "unmatched": 0, "results": []})
        return

    try:
        entries, _ = open_note_manager_and_wait()
    except SessionExpired as e:
        err_exit("SESSION_EXPIRED", str(e), 2)
    except (CreatorBackendNoNotes, CreatorBackendParseFailed, RuntimeError) as e:
        err_exit(type(e).__name__.upper(), str(e), 1)
    finally:
        camoufox_close()

    results = []
    n_matched = 0
    for row in rows:
        title = row.get("title") or ""
        if not title:
            results.append({"row_id": row["id"], "ok": False, "error": "ROW_TITLE_EMPTY"})
            continue
        matched = match_note_by_title(entries, title)
        if matched is None:
            # 不在首页（老作品/已删除/私密/标题歧义）——跳过，非错误
            results.append({"row_id": row["id"], "ok": False, "error": "NOT_ON_FIRST_PAGE", "title": title})
            continue
        metrics = stats_to_metrics(matched.get("stats", []))
        upd = update_metrics_row(row["id"], metrics)
        n_matched += 1
        results.append({
            "row_id": row["id"], "ok": upd.get("ok", True),
            "matched_title": matched["title"], "metrics": metrics,
            **({"update_error": upd.get("error")} if not upd.get("ok", True) else {}),
        })
    print_json({
        "ok": True,
        "platform": PLATFORM,
        "total": len(rows),
        "matched": n_matched,
        "unmatched": len(rows) - n_matched,
        "results": results,
    })


def cmd_probe(args) -> None:
    """打开 creator 后台笔记管理页，dump 截图/DOM/解析 JSON"""
    PROBE_OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        entries, _ = open_note_manager_and_wait()
        camoufox_screenshot(PROBE_OUT_DIR / "01_note_manager.png")
        html = camoufox_eval("document.documentElement.outerHTML")
        (PROBE_OUT_DIR / "01_note_manager.html").write_text(html, encoding="utf-8")
        (PROBE_OUT_DIR / "02_notes.json").write_text(
            json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        result = {
            "ok": True,
            "platform": PLATFORM,
            "out_dir": str(PROBE_OUT_DIR),
            "notes_found": len(entries),
            "first_3": entries[:3],
        }
    except (SessionExpired, CreatorBackendNoNotes, CreatorBackendParseFailed, RuntimeError) as e:
        err_exit(type(e).__name__.upper(), str(e), 2 if isinstance(e, SessionExpired) else 1)
    finally:
        camoufox_close()
    print_json(result)


# ── main ─────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="xhs_engagement",
        description="小红书 creator 后台互动数抓取（纯取数，不碰 DB）",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("check", help="判 creator 后台登录态").set_defaults(func=cmd_check)
    sub.add_parser("list", help="列出 creator 后台所有笔记 + 互动数").set_defaults(func=cmd_list)

    p_fetch = sub.add_parser("fetch", help="抓单条互动数（--row-id 查库+写库；--title 纯取数调试）")
    g = p_fetch.add_mutually_exclusive_group(required=True)
    g.add_argument("--row-id", type=int, help="pub_xhs 行 id（从 DB 取 title 匹配，抓完写库）")
    g.add_argument("--title", type=str, help="直接按 title 匹配（纯取数，不写库）")
    p_fetch.set_defaults(func=cmd_fetch)

    sub.add_parser(
        "fetch-all",
        help="批量刷新（打开首页一次，匹配 pub_xhs 全部行写库；不翻页）",
    ).set_defaults(func=cmd_fetch_all)

    sub.add_parser("probe", help="dump 截图/DOM/解析 JSON 调试用").set_defaults(func=cmd_probe)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
        return 0
    except SystemExit as e:
        return int(e.code) if e.code is not None else 0
    except Exception as e:  # noqa: BLE001
        sys.stderr.write(f"error: {e}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
