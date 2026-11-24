#!/usr/bin/env python3
"""burn_subtitles.py — 把 SRT/ASS 字幕烧录进视频。

用法：
  python3 burn_subtitles.py <input.mp4> <subs.srt> [--output out.mp4]
                            [--font-size 20] [--margin-v 40] [--position bottom|top]
                            [--preview-at 2.5 --output preview.png]

行为：
  - SRT 走统一样式（白字黑描边居中，--font-size/--margin-v/--position 可调）
  - ASS 自带样式，样式参数被忽略
  - 视频重编码（libx264 crf 20），音频不动（-c:a copy）

退出码：
  0 = 成功
  1 = 参数错误 / 文件不存在 / ffmpeg 失败
  3 = ffmpeg 不存在
"""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys


def die(msg: str, code: int = 1) -> None:
    print(json.dumps({"ok": False, "error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


def filter_escape(s: str) -> str:
    """分别转义滤镜选项值与 filtergraph；不经过 shell。"""
    out = "".join("\\" + c if c in "\\':" else c for c in s)
    out = "".join("\\" + c if c in "\\'[],;" else c for c in out)
    return out


def probe_video(path: str) -> dict:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_streams",
         "-show_format", "-of", "json", path], capture_output=True, text=True,
    )
    if result.returncode:
        raise ValueError("ffprobe 失败: " + result.stderr[-500:])
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise ValueError("输入没有视频流")
    stream = data["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    rotation = next((float(item["rotation"]) for item in stream.get("side_data_list", [])
                     if "rotation" in item), float(stream.get("tags", {}).get("rotate", 0)))
    if round(rotation) % 180 == 90:
        width, height = height, width
    duration = float(stream.get("duration") or data.get("format", {}).get("duration") or 0)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError("无法读取视频时长")
    return {"width": width, "height": height, "duration": duration}


def main() -> None:
    parser = argparse.ArgumentParser(description="把 SRT/ASS 字幕烧录进视频")
    parser.add_argument("input", help="输入视频")
    parser.add_argument("subs", help="字幕文件（.srt 或 .ass）")
    parser.add_argument("--output", default=None,
                        help="输出 MP4 路径（默认 <input>_sub.mp4）")
    parser.add_argument("--font-size", type=int, default=20,
                        help="ASS 脚本单位字号（默认 20，仅 SRT 生效；不是成片像素）")
    parser.add_argument("--margin-v", type=int, default=40,
                        help="ASS 脚本单位垂直边距（默认 40，仅 SRT 生效；不是成片像素）")
    parser.add_argument("--position", choices=["bottom", "top"], default="bottom",
                        help="字幕位置（默认 bottom，仅 SRT 生效）")
    parser.add_argument("--preview-at", type=float,
                        help="只试渲指定秒处的一帧，--output 指定 .png/.jpg；不生成视频")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        die(f"输入文件不存在: {args.input}")
    if not os.path.isfile(args.subs):
        die(f"字幕文件不存在: {args.subs}")
    if not shutil.which("ffmpeg"):
        die("ffmpeg 未安装", 3)
    if not args.subs.lower().endswith((".srt", ".ass")):
        die("字幕文件必须是 .srt 或 .ass")
    if args.font_size <= 0 or args.margin_v < 0:
        die("字号必须为正，边距不能为负")
    if args.preview_at is not None:
        if not shutil.which("ffprobe"):
            die("ffprobe 未安装", 3)
        try:
            duration = probe_video(args.input)["duration"]
            if not math.isfinite(args.preview_at) or not 0 <= args.preview_at < duration:
                die("--preview-at 必须落在视频时长内")
        except (ValueError, KeyError, TypeError) as error:
            die(str(error))

    if args.output is None:
        stem = os.path.splitext(args.input)[0]
        args.output = f"{stem}_sub.png" if args.preview_at is not None else f"{stem}_sub.mp4"
    if os.path.realpath(args.output) in {os.path.realpath(args.input), os.path.realpath(args.subs)}:
        die("输出不能覆盖输入视频或字幕")
    if args.preview_at is not None and not args.output.lower().endswith((".png", ".jpg", ".jpeg")):
        die("试渲输出必须是 .png/.jpg/.jpeg")
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

    subs_path = filter_escape(os.path.abspath(args.subs))
    if args.subs.lower().endswith(".ass"):
        vf = f"subtitles={subs_path}"
    else:
        alignment = 2 if args.position == "bottom" else 8  # ASS：2=底部居中，8=顶部居中
        style = (
            "FontName=Noto Sans CJK SC,"
            f"FontSize={args.font_size},"
            "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
            "Outline=2,Shadow=0,"
            f"Alignment={alignment},MarginV={args.margin_v}"
        )
        vf = f"subtitles={subs_path}:force_style={filter_escape(style)}"

    cmd = [
        "ffmpeg", "-y",
        "-i", args.input,
        "-vf", vf,
    ]
    if args.preview_at is not None:
        # 输出端 seek：滤镜先看到原视频时间轴，避免字幕被重置到片头。
        cmd += ["-ss", str(args.preview_at), "-frames:v", "1", "-an", args.output]
    else:
        cmd += [
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            "-movflags", "+faststart",
            args.output,
        ]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        die("ffmpeg 烧录失败: " + (r.stderr or b"").decode("utf-8", "replace")[-500:])
    if not os.path.isfile(args.output) or os.path.getsize(args.output) == 0:
        die("输出不存在或为空")

    print(json.dumps({
        "ok": True,
        "output": args.output,
        "subs": args.subs,
        "preview_at": args.preview_at,
    }, ensure_ascii=False, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
