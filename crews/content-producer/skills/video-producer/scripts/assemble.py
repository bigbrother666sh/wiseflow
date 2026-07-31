#!/usr/bin/env python3
"""assemble — 按序拼接已就绪的段 + 可选转场。

原子工具，不写死 Workflow。仅做一件事：把 render/ 下各 shot 的段按序拼成成片。
切素材/调速/混音/字幕/分辨率归一化由其他原子工具负责（clip-trim / audio-mix / timeline-compose），
agent 按 SKILL.md 场景化组合调用。

Usage:
  python3 scripts/assemble.py <project_dir> [--transition hard|fade|dissolve|xfade] [--width 1080] [--fps 30]

入：project_dir/render/ 各 shot-NN/gen*.mp4（段已就绪，assemble 不再切段）
出：project_dir/video.mp4（按序拼接的成片）

可选归一化：段尺寸/帧率不一时传 --width/--fps 统一（scale + pad 16:9 + sar + fps）。
段就绪约定：render/shot-NN/ 下应有 gen*.mp4 或 multi-best*.mp4，assemble 自动识别变体取最新。
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

VALID_TRANSITIONS = {"hard", "fade", "dissolve", "xfade"}
XFADE_TYPES = {"fade": "fade", "dissolve": "dissolve", "xfade": "fade"}


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


def pick_latest(shot_dir: Path, patterns: list[str]) -> Path | None:
    """自动识别 gen*.mp4 / multi-best*.mp4 变体，按版本号取最新。"""
    candidates: list[Path] = []
    for pat in patterns:
        candidates.extend(shot_dir.glob(pat))
    if not candidates:
        return None

    def version_key(p: Path) -> tuple[int, int]:
        m = re.search(r"[v-](\d+)", p.stem)
        return (1, int(m.group(1))) if m else (0, 0)

    return sorted(candidates, key=version_key)[-1]


def normalize_segment(src: Path, dst: Path, width: int, fps: int) -> float:
    """分辨率归一化：scale 到目标宽度 + pad 16:9 + sar 归一 + fps 统一。返回时长。"""
    height = round(width * 9 / 16)
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={fps},format=yuv420p"
    )
    run([
        "ffmpeg", "-y", "-i", str(src),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", "-r", str(fps),
        str(dst),
    ])
    return probe_duration(dst)


def concat_hard(segments: list[tuple[str, Path]], out: Path) -> None:
    """hard 转场：concat demuxer 直拼。concat_list.txt 里 file 行用绝对路径，避免 cwd 解析歧义。"""
    list_file = out.parent / "concat_list.txt"
    list_file.write_text(
        "\n".join(f"file '{seg.resolve()}'" for _, seg in segments),
        encoding="utf-8",
    )
    run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(out),
    ])
    list_file.unlink(missing_ok=True)


def concat_xfade(segments: list[tuple[str, Path, float]], out: Path, transition: str) -> None:
    """fade/dissolve/xfade 转场：链式 xfade。过渡时长 0.5s，不足 1s 的段硬切。"""
    if len(segments) == 1:
        shutil.copy2(segments[0][1], out)
        return

    xfade_type = XFADE_TYPES.get(transition, "fade")
    transition_dur = 0.5

    inputs: list[str] = []
    filter_parts: list[str] = []
    prev_label = "[0:v]"
    accum_dur = 0.0
    for i, (_, seg, dur) in enumerate(segments):
        inputs.extend(["-i", str(seg)])
        if i == 0:
            accum_dur = dur
            continue
        offset = max(0, accum_dur - transition_dur)
        cur_label = f"[v{i}]"
        filter_parts.append(
            f"{prev_label}[{i}:v]xfade=transition={xfade_type}:duration={transition_dur}:offset={offset:.3f}{cur_label}"
        )
        prev_label = cur_label
        accum_dur += dur - transition_dur

    amix_parts = [f"[{i}:a]" for i in range(len(segments))]
    amix_parts.append(f"amix=inputs={len(segments)}:duration=longest[aout]")
    filter_parts.append("".join(amix_parts))

    filter_complex = ";".join(filter_parts)
    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend([
        "-filter_complex", filter_complex,
        "-map", prev_label, "-map", "[aout]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k", str(out),
    ])
    run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 12 assemble 按序拼接")
    parser.add_argument("project_dir", help="output_videos/<topic>/")
    parser.add_argument("--source-dir", default=None, help="段目录（默认 render/；timeline-compose 调时传 artifacts/timeline/）")
    parser.add_argument("--output", default="video.mp4", help="输出名（相对 project_dir，默认 video.mp4）")
    parser.add_argument("--transition", default="hard", choices=sorted(VALID_TRANSITIONS))
    parser.add_argument("--width", type=int, default=None, help="归一化目标宽度（不传则不归一化，直 concat）")
    parser.add_argument("--fps", type=int, default=None, help="归一化帧率（不传则不归一化）")
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    source_dir = project / args.source_dir if args.source_dir else project / "render"

    # 收段：两种目录结构兼容
    # - render/：按 shot-NN/ 子目录收，每目录取最新 gen*.mp4 / multi-best*.mp4
    # - 其他目录（如 artifacts/timeline/）：直接收目录下的 clip-NN.mp4 或 *.mp4，按文件名序
    segments: list[tuple[str, Path]] = []
    if source_dir.name == "render":
        for shot_dir in sorted(source_dir.glob("shot-*")):
            pick = pick_latest(shot_dir, ["multi-best*.mp4", "gen*.mp4"])
            if pick and pick.is_file():
                segments.append((shot_dir.name, pick))
    else:
        for pick in sorted(source_dir.glob("*.mp4")):
            if pick.is_file():
                segments.append((pick.stem, pick))

    if not segments:
        die(f"{source_dir}/ 下无任何段（render/ 走 shot-NN/gen*.mp4；其他目录走 *.mp4），先跑 render-shot 或 timeline-compose")

    video_out = project / args.output
    if video_out.is_file():
        print(f"[checkpoint] {args.output} 已存在：{video_out}")
        return

    print(f"[plan] 共 {len(segments)} 段，转场={args.transition}")

    # 可选归一化（段尺寸/帧率不一时传 --width/--fps）
    if args.width is not None and args.fps is not None:
        work_dir = project / "artifacts" / "normalized"
        work_dir.mkdir(parents=True, exist_ok=True)
        normalized: list[tuple[str, Path, float]] = []
        for idx, (name, src) in enumerate(segments, 1):
            dst = work_dir / f"{idx:02d}_{name}.mp4"
            if not dst.is_file():
                print(f"[norm] {name} → {dst.name} (scale={args.width}, fps={args.fps})")
                dur = normalize_segment(src, dst, args.width, args.fps)
            else:
                dur = probe_duration(dst)
            normalized.append((name, dst, dur))

        print(f"[concat] 拼接 {len(normalized)} 段，转场={args.transition}")
        if args.transition == "hard":
            concat_hard([(n, d) for n, d, _ in normalized], video_out)
        else:
            concat_xfade(normalized, video_out, args.transition)
        print(f"  - 归一化：{args.width}x{round(args.width*9/16)}@{args.fps}fps")
    else:
        # 不归一化，直 concat（要求各段已同尺寸/帧率；否则 ffmpeg 会失败，agent 应先归一化）
        print(f"[concat] 直拼 {len(segments)} 段（未归一化，要求段已同尺寸/帧率）")
        if args.transition == "hard":
            concat_hard(segments, video_out)
        else:
            # xfade 需要时长信息
            with_dur = [(n, s, probe_duration(s)) for n, s in segments]
            concat_xfade(with_dur, video_out, args.transition)

    print(f"[done] 成片已落：{video_out}")
    print(f"  - 段数：{len(segments)}，转场：{args.transition}")


if __name__ == "__main__":
    main()
