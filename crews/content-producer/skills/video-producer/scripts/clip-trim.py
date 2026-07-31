#!/usr/bin/env python3
"""clip-trim — 精确切素材：指定入点/出点/倍速，支持视频和音频分别处理。

原子工具，不写死 Workflow。agent 按 SKILL.md 场景化组合调用。

Usage:
  # 切视频段（0.5s 入，2.3s 出，1.5x 倍速）
  python3 scripts/clip-trim.py --input shot.mp4 --output clip.mp4 --start 0.5 --end 2.3 --speed 1.5

  # 只切音频段（30s 入，35s 出，原速）
  python3 scripts/clip-trim.py --input narration.mp3 --output clip.mp3 --start 30 --end 35

  # 视频倍速时同步音频倍速（setpts + atempo）
  python3 scripts/clip-trim.py --input shot.mp4 --output clip.mp4 --start 1 --end 3 --speed 2 --sync-audio

参数说明：
  --input  输入素材路径（视频或音频文件）
  --output 输出路径
  --start  入点（秒，默认 0）
  --end    出点（秒，默认 = 输入全长）
  --speed  倍速（默认 1.0；2.0 = 2x，0.5 = 0.5x）
  --sync-audio  视频倍速时同步音频倍速（用 atempo filter；超出 0.5-2.0 范围链式串联）

视频倍速原理：setpts=PTS/speed 改时间戳；音频 atempo=speed 改播放速率。
倍速后时长 = (end - start) / speed。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


def die(msg: str) -> None:
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print(f"[cmd] {cmd[0]} ... ({len(cmd)} args)")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        die(f"命令失败 (rc={p.returncode}): {p.stderr[:500] or p.stdout[:500]}")
    return p


def probe_duration(path: Path) -> float:
    p = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
        capture_output=True, text=True,
    )
    if p.returncode != 0:
        return 0.0
    try:
        return float(json.loads(p.stdout).get("format", {}).get("duration", 0) or 0)
    except Exception:
        return 0.0


def is_video(path: Path) -> bool:
    """用 ffprobe 看是否有视频流。"""
    p = subprocess.run(
        ["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True,
    )
    return p.stdout.strip() == "video"


def atempo_chain(speed: float) -> str:
    """atempo filter 链。atempo 单级范围 [0.5, 2.0]，超出则链式串联。
    例：4x → atempo=2.0,atempo=2.0；0.25x → atempo=0.5,atempo=0.5。"""
    if 0.5 <= speed <= 2.0:
        return f"atempo={speed}"
    parts = []
    remaining = speed
    while remaining > 2.0:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        parts.append("atempo=0.5")
        remaining /= 0.5
    parts.append(f"atempo={remaining}")
    return ",".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description="clip-trim 精确切素材")
    parser.add_argument("--input", required=True, help="输入素材路径（视频或音频）")
    parser.add_argument("--output", required=True, help="输出路径")
    parser.add_argument("--start", type=float, default=0.0, help="入点（秒，默认 0）")
    parser.add_argument("--end", type=float, default=None, help="出点（秒，默认=输入全长）")
    parser.add_argument("--speed", type=float, default=1.0, help="倍速（默认 1.0）")
    parser.add_argument("--sync-audio", action="store_true", help="视频倍速时同步音频倍速")
    args = parser.parse_args()

    src = Path(args.input).resolve()
    dst = Path(args.output).resolve()
    if not src.is_file():
        die(f"输入不存在: {src}")

    src_dur = probe_duration(src)
    end = args.end if args.end is not None else src_dur
    if end <= args.start:
        die(f"出点({end})必须大于入点({args.start})")
    if args.speed <= 0:
        die(f"倍速必须 > 0，收到 {args.speed}")

    trim_dur = end - args.start
    out_dur = trim_dur / args.speed

    # -ss/-t 放 -i 后（output seek，精确切）；倍速时 -t 限的是输出时长（out_dur）
    cmd = ["ffmpeg", "-y", "-i", str(src), "-ss", str(args.start), "-t", str(out_dur)]

    has_video = is_video(src)
    vf_parts = []
    af_parts = []

    if has_video and args.speed != 1.0:
        vf_parts.append(f"setpts=PTS/{args.speed}")
        if args.sync_audio:
            af_parts.append(atempo_chain(args.speed))

    if vf_parts:
        cmd.extend(["-vf", ",".join(vf_parts)])
    if af_parts:
        cmd.extend(["-af", ",".join(af_parts)])

    # 视频流编码设置（音频文件无视频流时跳过）
    if has_video:
        cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "23"])
    cmd.extend(["-c:a", "aac", "-b:a", "192k"])

    cmd.append(str(dst))
    run(cmd)

    actual_dur = probe_duration(dst)
    print(f"[done] {src.name} → {dst.name}")
    print(f"  - 入点 {args.start}s 出点 {end}s，倍速 {args.speed}x")
    print(f"  - 期望时长 {out_dur:.3f}s，实际 {actual_dur:.3f}s")
    if has_video and args.sync_audio:
        print(f"  - 视音频同步倍速")


if __name__ == "__main__":
    main()
