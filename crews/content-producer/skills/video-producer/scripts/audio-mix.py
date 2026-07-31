#!/usr/bin/env python3
"""audio-mix — 多轨混音：指定多条音轨 + 各自起始延时和音量，输出混合音频。

原子工具，不写死 Workflow。agent 按 SKILL.md 场景化组合调用。

Usage:
  # 混三条音轨：旁白（0s 入，1.0 音量）+ BGM（5s 入，0.15 音量）+ 口播（10s 入，0.8 音量）
  python3 scripts/audio-mix.py \
    --track narration.mp3 --delay 0 --volume 1.0 \
    --track bgm.mp3 --delay 5 --volume 0.15 \
    --track voiceover.mp3 --delay 10 --volume 0.8 \
    --output mixed.mp3

  # 混两条音轨，指定总时长（短于总时长则 pad 静音到该时长）
  python3 scripts/audio-mix.py \
    --track narration.mp3 --delay 0 --volume 1.0 \
    --track bgm.mp3 --delay 2 --volume 0.2 \
    --output mixed.mp3 --duration 30

参数说明：
  --track   音轨（可重复多次，每次跟 --delay 和 --volume）
  --delay   该轨起始延时（秒，默认 0）
  --volume  该轨音量系数（0.0-1.0，默认 1.0；0.15 = �压到 15%）
  --output  输出混合音频路径
  --duration 输出总时长（秒，可选；不传则取最长轨延时+时长）

实现：ffmpeg adelay（毫秒延时）+ volume（音量）+ amix（叠加）。
延时用 adelay=<ms>，amix inputs=N duration=longest dropout_transition=0。
"""

import argparse
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


def main() -> None:
    parser = argparse.ArgumentParser(description="audio-mix 多轨混音")
    parser.add_argument(
        "--track", action="append", required=True,
        help="音轨文件路径（可重复多次）",
    )
    parser.add_argument(
        "--delay", action="append", type=float, default=None,
        help="该轨起始延时（秒，默认 0；按 --track 顺序对应）",
    )
    parser.add_argument(
        "--volume", action="append", type=float, default=None,
        help="该轨音量系数（0.0-1.0，默认 1.0；按 --track 顺序对应）",
    )
    parser.add_argument("--output", required=True, help="输出混合音频路径")
    parser.add_argument("--duration", type=float, default=None, help="输出总时长（秒，可选）")
    args = parser.parse_args()

    tracks = args.track
    n = len(tracks)

    # delay/volume 按 track 顺序对应，缺省补默认值
    delays = args.delay if args.delay else []
    delays += [0.0] * (n - len(delays))
    volumes = args.volume if args.volume else []
    volumes += [1.0] * (n - len(volumes))

    if len(delays) != n or len(volumes) != n:
        die(f"--delay / --volume 数量须等于 --track 数量（{n}）")

    # 校验各轨文件存在
    for t in tracks:
        if not Path(t).is_file():
            die(f"音轨不存在: {t}")

    dst = Path(args.output).resolve()
    dst.parent.mkdir(parents=True, exist_ok=True)

    # ffmpeg filter_complex 构造：
    # [i:a]adelay=<ms>,volume=<v>,apad=whole_dur=<dur>[a<i>]  各轨延时+音量+补虚到总时长
    # [a0][a1]...[aN]amix=inputs=N:duration=longest:dropout_transition=0:normalize=0[aout]
    # normalize=0 禁用 amix 自动除以轨道数，每轨 volume 即最终音量（设 2.0 就是 2 倍，不被稀释）
    # apad=whole_dur=<dur> 把每轨补虚到 --duration 总时长，避免短轨被截、输出时长不足
    inputs: list[str] = []
    filter_parts: list[str] = []
    dur_ms = int(args.duration * 1000) if args.duration is not None else None
    for i, (delay_s, vol) in enumerate(zip(delays, volumes)):
        inputs.extend(["-i", tracks[i]])
        delay_ms = int(delay_s * 1000)
        parts = []
        if delay_ms > 0:
            parts.append(f"adelay={delay_ms}")
        if vol != 1.0:
            parts.append(f"volume={vol}")
        if dur_ms is not None:
            # apad=whole_dur 是样本数（ms 级近似），确保该轨至少到 --duration 总时长
            parts.append(f"apad=whole_dur={args.duration}")
        if parts:
            filter_parts.append(f"[{i}:a]" + ",".join(parts) + f"[a{i}]")
        else:
            filter_parts.append(f"[{i}:a]anull[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(n))
    # duration=longest + normalize=0：取最长轨时长，每轨音量不被稀释
    filter_parts.append(
        f"{mix_inputs}amix=inputs={n}:duration=longest:dropout_transition=0:normalize=0[aout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = ["ffmpeg", "-y"]
    cmd.extend(inputs)
    cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]"])

    # 输出格式按扩展名推断（默认 mp3）
    ext = dst.suffix.lower().lstrip(".")
    if ext in ("wav",):
        cmd.extend(["-c:a", "pcm_s16le"])
    elif ext in ("ogg",):
        cmd.extend(["-c:a", "libvorbis"])
    else:
        cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])

    if args.duration is not None:
        cmd.extend(["-t", str(args.duration)])

    cmd.append(str(dst))
    run(cmd)

    print(f"[done] 混合音频已落：{dst}")
    print(f"  - {n} 轨混入")
    for i, (t, d, v) in enumerate(zip(tracks, delays, volumes)):
        print(f"  [{i}] {Path(t).name}  delay={d}s  volume={v}")
    if args.duration is not None:
        print(f"  - 总时长限制：{args.duration}s")


if __name__ == "__main__":
    main()
