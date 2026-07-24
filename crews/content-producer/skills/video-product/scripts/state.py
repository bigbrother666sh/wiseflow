#!/usr/bin/env python3
"""Pipeline state manager for video-product — subagent resume-from-failure.

Borrowed from OpenMontage lib/checkpoint.py, scoped to our needs:
- One JSON state per project: output_videos/<name>/state.json
- Stage list is fixed (script → gate0 → calibrate → assets → assemble → review → cover)
- Each stage: status (pending/in_progress/completed/awaiting_human/failed) + ts + notes
- Append-only on disk — superseded states archived to state.history/ (never destroy)
- decisions.log is separate append-only audit; this file is point-in-time recovery

Usage:
  python3 ./skills/video-product/scripts/state.py <project-dir> --init
  python3 ./skills/video-product/scripts/state.py <project-dir> --enter <stage>
  python3 ./skills/video-product/scripts/state.py <project-dir> --complete <stage> [--notes "..."]
  python3 ./skills/video-product/scripts/state.py <project-dir> --await <stage> [--notes "..."]
  python3 ./skills/video-product/scripts/state.py <project-dir> --fail <stage> [--notes "..."]
  python3 ./skills/video-product/scripts/state.py <project-dir> --next          # prints next pending stage
  python3 ./skills/video-product/scripts/state.py <project-dir> --show          # pretty-print current state

Stages (in order):
  script      — Step 2 脚本创作与定稿
  gate0       — Step 2.3.5 Gate 0 关键帧 contact sheet 确认
  calibrate   — Step 2.4 脚本定稿打分+盲预测（content-calibrator）
  assets      — Step 3 + Step 4 用户素材预处理 + 视频素材生产
  assemble    — Step 5 合成视频
  review      — Step 5.5 成片自检（review.py）
  cover       — Step 6 制作封面
  deliver     — Step 7 用户确认交付

Exit codes:
  0  ok
  1  bad args / state corrupt / stage unknown
  2  --next but all stages completed (nothing to resume)
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

STAGES = ["script", "gate0", "calibrate", "assets", "assemble", "review", "cover", "deliver"]
STATE_FILE_NAME = "state.json"
HISTORY_DIR_NAME = "state.history"

VALID_STATUSES = {"pending", "in_progress", "completed", "awaiting_human", "failed"}
# Stages that require human approval before advancing (borrowed from OpenMontage human_approval_default)
GATED_STAGES = {"script", "gate0", "calibrate", "assets", "deliver"}


def die(msg: str, code: int = 1) -> None:
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(code)


def state_path(project: Path) -> Path:
    return project / STATE_FILE_NAME


def history_dir(project: Path) -> Path:
    return project / HISTORY_DIR_NAME


def now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def init_state(project: Path) -> dict:
    """Create initial state with all stages pending."""
    state = {
        "project": str(project.resolve()),
        "created": now_ts(),
        "updated": now_ts(),
        "stages": {s: {"status": "pending", "ts": None, "notes": ""} for s in STAGES},
    }
    state_path(project).write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")
    return state


def load_state(project: Path) -> dict:
    p = state_path(project)
    if not p.is_file():
        die(f"state.json 不存在：{p}（先跑 --init）")
    try:
        state = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"state.json 损坏：{e}")
    if "stages" not in state or set(state["stages"].keys()) != set(STAGES):
        die(f"state.json stages 不匹配，期望 {list(STAGES)}")
    return state


def archive_and_write(project: Path, state: dict) -> None:
    """Archive current state to state.history/ (timestamped) then write new."""
    p = state_path(project)
    if p.is_file():
        hist = history_dir(project)
        hist.mkdir(exist_ok=True)
        ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(p, hist / f"state_{ts_slug}.json")
    state["updated"] = now_ts()
    p.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def set_stage(project: Path, stage: str, status: str, notes: str | None) -> None:
    if stage not in STAGES:
        die(f"unknown stage: {stage}; valid: {STAGES}")
    if status not in VALID_STATUSES:
        die(f"unknown status: {status}; valid: {VALID_STATUSES}")
    state = load_state(project)
    cur = state["stages"][stage]
    cur["status"] = status
    cur["ts"] = now_ts()
    if notes is not None:
        cur["notes"] = notes
    archive_and_write(project, state)
    print(f"[ok] {stage} → {status}" + (f" ({notes})" if notes else ""))


def next_pending(project: Path) -> str | None:
    """Return the first stage that's pending or failed or awaiting_human, in order."""
    state = load_state(project)
    for s in STAGES:
        st = state["stages"][s]["status"]
        if st in ("pending", "failed", "awaiting_human"):
            return s
    return None


def show(project: Path) -> None:
    state = load_state(project)
    print(json.dumps(state, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pipeline state manager for video-product.")
    parser.add_argument("project_dir", help="项目目录 (output_videos/<name>/)")
    parser.add_argument("--init", action="store_true", help="初始化 state.json，所有阶段 pending")
    parser.add_argument("--enter", metavar="STAGE", default=None, help="进入某阶段：标 in_progress")
    parser.add_argument("--complete", metavar="STAGE", default=None, help="完成某阶段：标 completed")
    parser.add_argument("--await", dest="await_", metavar="STAGE", default=None, help="等用户决策：标 awaiting_human")
    parser.add_argument("--fail", metavar="STAGE", default=None, help="某阶段失败：标 failed")
    parser.add_argument("--next", action="store_true", help="打印下一个待跑阶段")
    parser.add_argument("--show", action="store_true", help="pretty-print 当前 state")
    parser.add_argument("--notes", default=None, help="给 --enter/--complete/--await/--fail 附备注")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    if not project.is_dir():
        die(f"项目目录不存在：{project}")

    if args.init:
        init_state(project)
        print(f"[ok] state initialized at {state_path(project)}")
        return

    # All other commands need existing state
    if args.next:
        nxt = next_pending(project)
        if nxt is None:
            print("[done] all stages completed — nothing to resume", file=sys.stderr)
            sys.exit(2)
        print(nxt)
        return

    if args.show:
        show(project)
        return

    for flag, status in [("enter", "in_progress"), ("complete", "completed"),
                          ("await_", "awaiting_human"), ("fail", "failed")]:
        val = getattr(args, flag)
        if val is not None:
            set_stage(project, val, status, args.notes)
            return

    die("没指定动作：传 --init / --enter / --complete / --await / --fail / --next / --show 之一")


if __name__ == "__main__":
    main()
