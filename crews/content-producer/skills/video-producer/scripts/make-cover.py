#!/usr/bin/env python3
"""Stage 14a — make-cover：封面（siliconflow-img-gen，必含标题文字）。

Usage:
  python3 scripts/make-cover.py <project_dir> --title "..."

入：project_dir/script/brief.md（标题）+ storyboard 关键帧
出：project_dir/cover.jpg（含标题文字的封面图）

封面硬约束：必含标题文字。siliconflow-img-gen 不一定能把中文标题烤进图，
agent 生成后用 image 工具看，确认标题可见——不可见就用 ImageMagick/Pillow 烧字上去。
"""

import argparse
import json
import sys
from pathlib import Path


def die(msg: str) -> None:
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 14a make-cover")
    parser.add_argument("project_dir", help="项目目录（output_videos/<topic>/ 或平台运营目录 <platform>/outputs/<video-name>/）")
    parser.add_argument("--title", default=None, help="封面标题文字，不传则从 brief.md 抽")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    cover = project / "cover.jpg"
    if cover.is_file():
        print(f"[checkpoint] cover.jpg 已存在：{cover}")
        return

    title = args.title
    if not title:
        brief = project / "brief.md"
        if brief.is_file():
            content = brief.read_text(encoding="utf-8")
            # 抽第一个 # 标题或前 50 字作 title
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            if not title:
                title = content[:50].strip()
        if not title:
            die("需 --title 或 brief.md 含 # 标题")

    stub = {
        "title": title,
        "instruction": (
            "agent 调公共 siliconflow-img-gen 生成封面图，prompt 必含标题文字指令。"
            "生成后用 image 工具看，确认标题可见——不可见就用 ImageMagick/Pillow 烧字上去。"
            "落 cover.jpg 到项目根。"
        ),
        "cover_path": str(cover),
    }
    print(f"[plan] cover.jpg 标题：{title}")
    print(f"[next] agent 调 siliconflow-img-gen 生成 → 确认标题可见 → 落 {cover}")


if __name__ == "__main__":
    main()
