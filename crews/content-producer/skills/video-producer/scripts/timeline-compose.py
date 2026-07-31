#!/usr/bin/env python3
"""timeline-compose — 时间轴合成：按 JSON 指令调 clip-trim + audio-mix 合成片段。

原子工具，不写死 Workflow。agent 按 SKILL.md 场景化组合调用。

Usage:
  python3 scripts/timeline-compose.py <project_dir> --timeline timeline.json [--output video.mp4]

时间轴 JSON 结构：
{
  "segments": [
    {
      "source": "render/shot-01/gen.mp4",     # 素材路径（相对 project_dir）
      "start": 0.5,                            # 入点（秒，默认 0）
      "end": 2.3,                              # 出点（秒，默认=素材全长）
      "speed": 1.5,                            # 倍速（默认 1.0）
      "sync_audio": true,                      # 视频倍速时同步音频倍速（默认 false）
      "audio_tracks": [                        # 该段额外音轨（可选，叠加到段音轨）
        {"source": "audio/narration.mp3", "start": 0.0, "end": 1.8, "delay": 0, "volume": 1.0}
      ]
    },
    ...
  ],
  "audio_globals": [                           # 全段音轨（可选，按 delay 跨段叠加）
    {"source": "audio/bgm.mp3", "delay": 0, "volume": 0.15}
  ],
  "width": 1080,                              # 归一化宽度（可选，默认不归一化）
  "fps": 30                                   # 归一化帧率（可选，默认不归一化）
}

输出：
  project_dir/artifacts/timeline/ 下各段切好的片段（clip-NN.mp4）
  project_dir/<output>（默认 video.mp4）：最终合成片段（按段序 concat + 各段音轨 + 全段音轨混入）

本脚本内部调 clip-trim.py 切段 + audio-mix.py 混音，不裸写 ffmpeg filter。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent


def die(msg: str) -> None:
    print(f"[error] {msg}", file=sys.stderr)
    sys.exit(1)


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    print(f"[cmd] {cmd[0]} ... ({len(cmd)} args)")
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        die(f"命令失败 (rc={p.returncode}): {p.stderr[:500] or p.stdout[:500]}")
    return p


def main() -> None:
    parser = argparse.ArgumentParser(description="timeline-compose 时间轴合成")
    parser.add_argument("project_dir", help="output_videos/<topic>/")
    parser.add_argument("--timeline", required=True, help="时间轴 JSON 路径（相对 project_dir 或绝对）")
    parser.add_argument("--output", default="video.mp4", help="输出合成片段名（相对 project_dir，默认 video.mp4）")
    parser.add_argument("--transition", default="hard", choices=["hard", "fade", "dissolve", "xfade"])
    args = parser.parse_args()

    project = Path(args.project_dir).resolve()
    tl_path = Path(args.timeline)
    if not tl_path.is_absolute():
        tl_path = project / args.timeline
    if not tl_path.is_file():
        die(f"时间轴不存在: {tl_path}")

    tl = json.loads(tl_path.read_text(encoding="utf-8"))
    segments = tl.get("segments") or []
    if not segments:
        die("时间轴无 segments")

    work_dir = project / "artifacts" / "timeline"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. 每段调 clip-trim 切素材
    print(f"[plan] 共 {len(segments)} 段，切段中...")
    clip_paths: list[Path] = []
    for i, seg in enumerate(segments, 1):
        src = Path(seg["source"])
        if not src.is_absolute():
            src = project / seg["source"]
        if not src.is_file():
            die(f"段 {i} 素材不存在: {src}")

        clip_dst = work_dir / f"clip-{i:02d}.mp4"
        cmd = [
            "python3", str(SCRIPT_DIR / "clip-trim.py"),
            "--input", str(src),
            "--output", str(clip_dst),
        ]
        if seg.get("start") is not None:
            cmd.extend(["--start", str(seg["start"])])
        if seg.get("end") is not None:
            cmd.extend(["--end", str(seg["end"])])
        if seg.get("speed") is not None and seg["speed"] != 1.0:
            cmd.extend(["--speed", str(seg["speed"])])
            if seg.get("sync_audio"):
                cmd.append("--sync-audio")
        print(f"[clip] 段 {i}: {src.name}")
        run(cmd)
        clip_paths.append(clip_dst)

    # 2. 各段音轨混入：每段如有 audio_tracks，跑 audio-mix 叠到段音轨
    for i, seg in enumerate(segments, 1):
        audio_tracks = seg.get("audio_tracks") or []
        if not audio_tracks:
            continue
        clip = work_dir / f"clip-{i:02d}.mp4"
        mixed = work_dir / f"clip-{i:02d}-mixed.mp4"
        cmd = ["python3", str(SCRIPT_DIR / "audio-mix.py")]
        cmd.extend(["--track", str(clip), "--delay", "0", "--volume", "1.0"])
        for tr in audio_tracks:
            tsrc = Path(tr["source"])
            if not tsrc.is_absolute():
                tsrc = project / tr["source"]
            cmd.extend(["--track", str(tsrc)])
            cmd.extend(["--delay", str(tr.get("delay", 0))])
            cmd.extend(["--volume", str(tr.get("volume", 1.0))])
        cmd.extend(["--output", str(mixed)])
        print(f"[mix] 段 {i} 音轨混入")
        run(cmd)
        clip_paths[i - 1] = mixed  # 替换为混音后的版本

    # 3. 拼接各段（走 assemble.py 做按序 concat + �可选转场）
    out_path = project / args.output
    width = tl.get("width")
    fps = tl.get("fps")
    norm_msg = f"，归一化={width}x{round(width*9/16)}@{fps}fps" if width and fps else "，未归一化"
    print(f"[compose] 拼接 {len(clip_paths)} 段，转场={args.transition}{norm_msg}")
    cmd = [
        "python3", str(SCRIPT_DIR / "assemble.py"),
        str(project),
        "--source-dir", "artifacts/timeline",
        "--output", args.output,
        "--transition", args.transition,
    ]
    if width is not None and fps is not None:
        cmd.extend(["--width", str(width), "--fps", str(fps)])
    run(cmd)

    # 4. 全段音轨（audio_globals）混入最终片段
    globals_audio = tl.get("audio_globals") or []
    if globals_audio:
        tmp_with_globals = work_dir / "with-globals.mp4"
        cmd = ["python3", str(SCRIPT_DIR / "audio-mix.py")]
        cmd.extend(["--track", str(out_path), "--delay", "0", "--volume", "1.0"])
        for tr in globals_audio:
            tsrc = Path(tr["source"])
            if not tsrc.is_absolute():
                tsrc = project / tr["source"]
            cmd.extend(["--track", str(tsrc)])
            cmd.extend(["--delay", str(tr.get("delay", 0))])
            cmd.extend(["--volume", str(tr.get("volume", 1.0))])
        cmd.extend(["--output", str(tmp_with_globals)])
        print(f"[mix] 全段音轨混入")
        run(cmd)
        tmp_with_globals.replace(out_path)

    print(f"[done] 时间轴合成已落：{out_path}")
    print(f"  - {len(segments)} 段，转场 {args.transition}")
    if globals_audio:
        print(f"  - 全段音轨 {len(globals_audio)} 条已混入")


if __name__ == "__main__":
    main()
