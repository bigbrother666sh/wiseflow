#!/usr/bin/env python3
"""Stage 11 — mix-audio：旁白 + BGM + 字幕。

Usage:
  python3 scripts/mix-audio.py <project_dir>

入：project_dir/script/script.md（delivery_cues）+ storyboard/duration
出：project_dir/audio/narration.mp3（awk-tts 旁白）
    + project_dir/audio/bgm.mp3（BGM，pexels/pixabay 或静音占位）
    + project_dir/audio/subtitles.srt（字幕，从对白+旁白抽）

旁白优先级：OpenClaw 内置 TTS 优先 → awk-tts fallback（delivery_cues 按 awk-tts 实际通道能力裁剪）。
本脚本落脚手架：实际调内置 TTS 或 awk-tts 由 agent 按 SKILL.md 优先级执行，本脚本只落 audio/ 目录与 srt 模板。
"""

import argparse
import json
import sys
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 11 mix-audio")
    parser.add_argument("project_dir", help="output_videos/<topic>/")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    script_path = project / "script" / "script.md"
    if not script_path.is_file():
        die(f"前置缺失: script.md 不存在")

    audio_dir = project / "audio"
    audio_dir.mkdir(parents=True, exist_ok=True)

    # checkpoint
    narration = audio_dir / "narration.mp3"
    srt = audio_dir / "subtitles.srt"
    if narration.is_file() and srt.is_file():
        print(f"[checkpoint] narration.mp3 + subtitles.srt 已存在，沿用")
        return

    # srt 占位模板
    if not srt.is_file():
        srt.write_text(
            "1\n00:00:00,000 --> 00:00:03,000\n（agent 据对白+旁白填字幕）\n", encoding="utf-8"
        )

    print(f"[done] audio/ 目录已建 + subtitles.srt 模板已落")
    print(f"[next] agent 按优先级调 TTS：")
    print(f"  1. OpenClaw 内置 TTS（首选）")
    print(f"  2. awk-tts fallback（delivery_cues 按 awk-tts 实际通道能力裁剪）")
    print(f"  BGM：pexels-footage / pixabay-footage 搜 background music，或静音占位")


if __name__ == "__main__":
    main()
