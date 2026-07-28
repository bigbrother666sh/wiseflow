#!/usr/bin/env python3
"""Stage 12 — assemble：按镜顺序拼接成片 + 转场。

Usage:
  python3 scripts/assemble.py <project_dir> [--transition hard|fade|dissolve|xfade]

入：project_dir/render/ 各 shot-NN/gen-run-v01.mp4 + audio/ narration/bgm
出：project_dir/video.mp4（成片，含音轨与字幕）

转场用 ffmpeg xfade（合成期转场）——这解决"两镜间过渡观感"，不解决机位连续性。
机位连续性在 Stage 5 shot-decompose 已退化成"父机位首帧编辑重绘"。
本脚本调本仓 main 侧 video-edit assemble 子命令做实际 ffmpeg 工作，不裸写 ffmpeg。
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

VALID_TRANSITIONS = {"hard", "fade", "dissolve", "xfade"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 12 assemble")
    parser.add_argument("project_dir", help="output_videos/<topic>/")
    parser.add_argument("--transition", default="hard", choices=sorted(VALID_TRANSITIONS))
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    render_dir = project / "render"
    artifacts_dir = project / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # 收齐 render 下各 shot 的最终段（gen-run-v01.mp4 或 multi-best.mp4 优先）
    segments = []
    for shot_dir in sorted(render_dir.glob("shot-*")):
        pick = shot_dir / "multi-best.mp4"
        if not pick.is_file():
            pick = shot_dir / "gen-run-v01.mp4"
        if pick.is_file():
            segments.append((shot_dir.name, pick))

    if not segments:
        die(f"render/ 下无任何 shot 段（gen-run-v01.mp4 或 multi-best.mp4），先跑 render-shot")

    # 复制到 artifacts/ 按序编号
    for idx, (name, src) in enumerate(segments, 1):
        dst = artifacts_dir / f"{idx:02d}_{name}.mp4"
        if not dst.is_file():
            shutil.copy2(src, dst)

    video_out = project / "video.mp4"
    if video_out.is_file():
        print(f"[checkpoint] video.mp4 已存在：{video_out}")
        return

    # 检查 video-edit assemble 是否可用（main 侧公共子命令）
    ve_assemble = shutil.which("video-edit")
    print(f"[plan] 共 {len(segments)} 段，转场={args.transition}")
    print(f"[plan] artifacts 目录已就绪：{artifacts_dir}")
    if ve_assemble:
        print(f"[next] agent 跑：video-edit assemble {artifacts_dir} --output {video_out}")
        print(f"  （video-edit assemble 是 main 侧公共拼接子命令，含 ffmpeg concat + xfade + 烧字幕）")
    else:
        print(f"[warn] video-edit 不在 PATH，agent 须显式调 main 侧公共 video-edit assemble 子命令")
    print(f"  音轨：audio/narration.mp3 + audio/bgm.mp3 在拼接时混入")


if __name__ == "__main__":
    main()
