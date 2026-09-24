#!/usr/bin/env python3
"""Offline engineering smoke test: synthetic presenter/tone, never a real-avatar acceptance."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / 'crews/content-producer/skills/expert-video/tools'
DECK = TOOLS / 'deck-render/deck-render.sh'
VIDEO = TOOLS / 'video-producer/video-producer.sh'


def run(cmd, log):
    start = time.monotonic()
    result = subprocess.run([str(x) for x in cmd], capture_output=True, text=True, timeout=1200)
    log.write_text(result.stdout + '\n' + result.stderr)
    if result.returncode:
        raise RuntimeError(f'{cmd[0]} failed ({result.returncode}), see {log}')
    return round(time.monotonic()-start, 3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='empty directory')
    parser.add_argument('--slides', type=Path, help='reuse an explicitly supplied 60s 1080p30 wrapper output')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    if out.exists() and any(out.iterdir()):
        parser.error('output-dir must be empty')
    out.mkdir(parents=True, exist_ok=True)
    (out/'logs').mkdir()
    durations = {}
    def step(name, cmd):
        durations[name] = run(cmd, out/'logs'/f'{name}.log')
    step('scaffold', [DECK, 'scaffold', out/'composition', '--spec', Path(__file__).with_name('deck-spec.json')])
    step('preview', [DECK, 'preview', out/'composition', '--output', out/'review/slides'])
    if args.slides:
        shutil.copy2(args.slides.resolve(), out/'slides.mp4')
    else:
        step('render', [DECK, 'render', out/'composition', '--output', out/'slides.mp4', '--workers', '2'])
    step('animation', ['python3', Path(__file__).with_name('check_animation.py'), '--slides', out/'slides.mp4', '--output-dir', out/'review/animation'])
    step('presenter-fixture', ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc2=s=480x480:r=30:d=60', '-c:v', 'libx264', '-threads', '2', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', out/'presenter.mp4'])
    step('audio-fixture', ['ffmpeg', '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=60', out/'narration.wav'])
    step('pip', [VIDEO, 'pip-compose', '--base', out/'slides.mp4', '--presenter', out/'presenter.mp4', '--audio', out/'narration.wav', '--output', out/'composed.mp4'])
    step('no-presenter', [VIDEO, 'pip-compose', '--base', out/'slides.mp4', '--audio', out/'narration.wav', '--output', out/'no-presenter.mp4'])
    srt = out/'subtitles.srt'
    srt.write_text('1\n00:00:00,000 --> 00:01:00,000\n开发验收：测试小窗与测试音，不是真人口播\n', encoding='utf-8')
    step('subtitles', [VIDEO, 'burn-srt', out/'composed.mp4', srt, '--output', out/'subtitled.mp4', '--force-style', 'FontName=Noto Sans CJK SC,FontSize=22,Alignment=2,MarginV=20'])
    step('normalize', [VIDEO, 'normalize', out/'subtitled.mp4', '--output', out/'video.mp4'])
    step('review', [ROOT/'skills/video-review/video-review.sh', out/'video.mp4', '--target-duration', '60', '--target-resolution', '1920x1080', '--output', out/'review/verdict.json'])
    step('decode', ['ffmpeg', '-v', 'error', '-i', out/'video.mp4', '-f', 'null', '-'])
    (out/'smoke.json').write_text(json.dumps({'scope': 'synthetic media only; no TTS/ASR/avatar/lip-sync acceptance', 'seconds': durations, 'slides_reused': bool(args.slides), 'video': str(out/'video.mp4')}, indent=2)+'\n')
    print(out/'smoke.json')


if __name__ == '__main__':
    main()
