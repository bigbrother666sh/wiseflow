#!/usr/bin/env python3
"""Local, version-pinned HyperFrames rendering; no upstream workflow installation."""
import argparse
import html
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from html.parser import HTMLParser

TOOL = Path(__file__).resolve().parents[1]
FONT = 'Noto Sans CJK SC'


def browser_binary():
    marker = TOOL / '.deck-render-browser'
    if not marker.is_file():
        return None
    version, separator, relative = marker.read_text().strip().partition('\t')
    if not separator or version != '1.61.1':
        return None
    path = (TOOL / relative).resolve()
    return path if path.is_file() and path.is_relative_to(TOOL) else None


def font_available():
    if shutil.which('fc-list') and FONT in run(['fc-list', ':lang=zh', 'family']):
        return True
    if sys.platform == 'darwin':
        return any((root / 'NotoSansCJKsc-Regular.otf').is_file() for root in
                   (Path.home() / 'Library/Fonts', Path('/Library/Fonts')))
    if os.name == 'nt':
        local = os.environ.get('LOCALAPPDATA')
        windir = os.environ.get('WINDIR', 'C:/Windows')
        return any((root / 'NotoSansCJKsc-Regular.otf').is_file() for root in
                   ([Path(local) / 'Microsoft/Windows/Fonts'] if local else []) + [Path(windir) / 'Fonts'])
    return False


def run(cmd, cwd=None):
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY='1')
    browser = browser_binary()
    if browser:
        env['PRODUCER_HEADLESS_SHELL_PATH'] = str(browser)
    # The explicit --no-browser-gpu flags own capture policy; don't inherit a conflicting override.
    env.pop('PRODUCER_BROWSER_GPU_MODE', None)
    result = subprocess.run([str(x) for x in cmd], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=1200)
    if result.returncode:
        raise RuntimeError((result.stderr + '\n' + result.stdout)[-8000:])
    return result.stdout


def dependencies():
    for name in ('node', 'ffmpeg', 'ffprobe'):
        if not shutil.which(name):
            raise EnvironmentError(f'缺少 {name}，交 IT engineer 安装')
    if int(run(['node', '--version']).strip().lstrip('v').split('.')[0]) < 22:
        raise EnvironmentError('需要 Node >=22')
    for name, version in json.loads((TOOL / 'package.json').read_text())['dependencies'].items():
        manifest = TOOL / 'node_modules' / name / 'package.json'
        if not manifest.is_file() or json.loads(manifest.read_text())['version'] != version:
            raise EnvironmentError(f'缺少锁定依赖 {name}@{version}，交 IT engineer 运行项目依赖安装')
    executable = 'hyperframes.cmd' if os.name == 'nt' else 'hyperframes'
    return TOOL / 'node_modules/.bin' / executable


def positive(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(f'{label} 必须是有限正数')
    return value


def validate_spec(spec):
    if not isinstance(spec, dict):
        raise ValueError('spec 必须是 JSON 对象')
    for key, default in [('width', 1920), ('height', 1080), ('fps', 30)]:
        value = positive(spec.get(key, default), key)
        if int(value) != value or (key != 'fps' and (value % 2 or value < 360)):
            raise ValueError(f'{key} 必须为整数，画布尺寸至少 360 且为偶数')
        if key == 'fps' and value > 60:
            raise ValueError('fps 最大 60')
        spec[key] = int(value)
    if spec.get('theme', 'light') not in ('light', 'dark'):
        raise ValueError('theme: light / dark')
    if spec.get('pip', 'bottom-right') not in ('none', 'bottom-left', 'bottom-right', 'top-left', 'top-right'):
        raise ValueError('pip 必须是四角之一或 none')
    scenes = spec.get('scenes')
    if not isinstance(scenes, list) or not scenes:
        raise ValueError('scenes 必须是非空数组')
    for scene in scenes:
        if not isinstance(scene, dict):
            raise ValueError('scene 必须是 JSON 对象')
        duration = positive(scene.get('duration'), 'scene.duration')
        if not 3 <= duration <= 30:
            raise ValueError('每页驻留 3–30 秒；过短合页，过长拆页')
        if not isinstance(scene.get('title'), str) or not scene['title'].strip() or len(scene['title']) > 32:
            raise ValueError('每页 title 必填，最多 32 字')
        kind = scene.get('type', 'points')
        if kind not in ('title', 'points', 'chart', 'image'):
            raise ValueError('scene.type: title / points / chart / image')
        points = scene.get('points', [])
        if not isinstance(points, list) or len(points) > 4 or any(not isinstance(x, str) or len(x) > 48 for x in points):
            raise ValueError('points 最多四条，每条最多 48 字')
        if kind == 'chart':
            data = scene.get('data', [])
            if not isinstance(data, list) or not 1 <= len(data) <= 6 or not scene.get('source'):
                raise ValueError('chart 需要 1–6 个 data 点和 source 来源')
            for item in data:
                if not isinstance(item, dict):
                    raise ValueError('data 点必须是 JSON 对象')
                positive(item.get('value'), 'chart.value')
                if not isinstance(item.get('label'), str) or len(item['label']) > 8:
                    raise ValueError('chart.label 最多 8 字')
        if kind == 'image':
            image = Path(scene.get('image', ''))
            if not image.is_absolute() or not image.is_file() or not scene.get('source'):
                raise ValueError('image 需要存在的绝对路径和 source 来源/授权')
    return spec


def font_css():
    return '\n'.join(f'@font-face {{ font-family: "{FONT}"; src: local("{name}"); font-weight: {weight}; }}'
                     for weight, name in [(300, FONT + ' Light'), (400, FONT), (500, FONT + ' Medium'), (700, FONT + ' Bold')])


def scaffold(spec_path, project):
    spec = validate_spec(json.loads(spec_path.read_text()))
    gsap = TOOL / 'node_modules/gsap/dist/gsap.min.js'
    if not gsap.is_file():
        raise EnvironmentError('缺少 gsap，先安装 deck-render 依赖')
    if project.exists() and any(project.iterdir()):
        raise ValueError('scaffold 只写空目录；修改已有 HTML，或另建目录，不覆盖设计')
    project.mkdir(parents=True, exist_ok=True)
    (project / 'assets').mkdir()
    (project / 'compositions').mkdir()
    shutil.copy2(gsap, project / 'assets/gsap.min.js')
    w, h, fps = spec['width'], spec['height'], spec['fps']
    # Use the same logical 1920x1080 grid at any requested canvas size.
    dark = spec.get('theme') == 'dark'
    bg, fg, muted, accent = ('#152536', '#ffffff', '#d2deeb', '#80bcff') if dark else ('#f7f5f0', '#1c2b3a', '#465568', '#274b73')
    pip = spec.get('pip', 'bottom-right')
    left = 560 if pip.endswith('left') else 100
    width = 1260 if pip != 'none' else 1720
    refs, elapsed = [], 0
    for i, scene in enumerate(spec['scenes'], 1):
        sid = f'scene-{i:02d}'
        duration = scene['duration']
        esc = lambda x: html.escape(str(x), quote=True)
        body = ''
        kind = scene.get('type', 'points')
        if kind == 'chart':
            data = scene['data']
            maximum = max(x['value'] for x in data)
            step = width / len(data)
            bars = []
            for j, item in enumerate(data):
                bh = item['value'] / maximum * 360
                x = j * step + step * .2
                bars.append(f'<rect class="bar" x="{x}" y="{420-bh}" width="{step*.6}" height="{bh}" fill="{accent}"/>'
                            f'<text x="{j*step+step/2}" y="{400-bh}" text-anchor="middle">{esc(item["value"])}</text>'
                            f'<text x="{j*step+step/2}" y="470" text-anchor="middle">{esc(item["label"])}</text>')
            body = f'<svg width="{width}" height="510" viewBox="0 0 {width} 510">' + ''.join(bars) + '</svg>'
        else:
            if kind == 'image':
                source = Path(scene['image'])
                name = f'{sid}{source.suffix.lower()}'
                shutil.copy2(source, project / 'assets' / name)
                body += f'<img src="assets/{name}" alt="{esc(scene["title"])}">'
            body += '<ul>' + ''.join(f'<li>{esc(x)}</li>' for x in scene.get('points', [])) + '</ul>'
        source = esc(scene.get('source', ''))
        css = f'''{font_css()}
        [data-composition-id="{sid}"] .page {{ position:absolute; width:1920px; height:1080px; transform:scale({w/1920},{h/1080}); transform-origin:top left; background:{bg}; color:{fg}; font-family:"{FONT}",sans-serif; }}
        [data-composition-id="{sid}"] .content {{ position:absolute; left:{left}px; top:100px; width:{width}px; }}
        [data-composition-id="{sid}"] h1 {{ font-size:60px; line-height:1.25; margin:0 0 24px; }}
        [data-composition-id="{sid}"] p {{ font-size:28px; color:{muted}; margin:0 0 32px; }}
        [data-composition-id="{sid}"] li {{ font-size:36px; line-height:1.6; margin:18px 0; }}
        [data-composition-id="{sid}"] ul {{ padding-left:40px; margin:0; }}
        [data-composition-id="{sid}"] img {{ float:left; width:48%; height:440px; object-fit:contain; margin-right:40px; }}
        [data-composition-id="{sid}"] svg text {{ font-family:"{FONT}",sans-serif; font-size:28px; fill:{fg}; }}
        [data-composition-id="{sid}"] .bar {{ transform-box:fill-box; transform-origin:bottom; }}
        [data-composition-id="{sid}"] .source {{ position:absolute; left:{left}px; top:820px; width:{width}px; font-size:22px; color:{muted}; }}'''
        animation = f'''const scope = '[data-composition-id="{sid}"]';
        const tl = gsap.timeline({{paused:true}});
        tl.fromTo(scope+' h1', {{opacity:0,y:24}}, {{opacity:1,y:0,duration:0.6}}, 0);
        tl.fromTo(scope+' .body', {{opacity:0,y:20}}, {{opacity:1,y:0,duration:0.6}}, 0.3);'''
        if kind == 'chart':
            animation += "\ntl.fromTo(scope+' .bar',{scaleY:0},{scaleY:1,duration:0.8,stagger:0.12},0.5);"
        animation += f'\nwindow.__timelines["{sid}"]=tl; tl.seek(0);'
        (project / f'compositions/{sid}.html').write_text(f'''<template id="{sid}-template">
        <div data-composition-id="{sid}" data-width="{w}" data-height="{h}">
        <div class="page"><div class="content"><h1>{esc(scene['title'])}</h1><p>{esc(scene.get('subtitle', ''))}</p>
        <div class="body">{body}</div></div><div class="source">{source} · {i:02d} / {len(spec['scenes']):02d}</div></div>
        <style>{css}</style><script>{animation}</script></div></template>''')
        refs.append(f'<div id="{sid}" data-composition-id="{sid}" data-composition-src="compositions/{sid}.html" data-start="{elapsed}" data-duration="{duration}" data-track-index="0"></div>')
        elapsed += duration
    (project / 'index.html').write_text(f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
    <script src="assets/gsap.min.js"></script><style>{font_css()}
    *{{box-sizing:border-box}} html,body{{margin:0;width:{w}px;height:{h}px;overflow:hidden;background:{bg};}}</style></head><body>
    <div data-composition-id="main" data-width="{w}" data-height="{h}" data-fps="{fps}" data-start="0" data-duration="{elapsed}">
    {''.join(refs)}</div><script>window.__timelines=window.__timelines||{{}}; window.__timelines.main=gsap.timeline({{paused:true}});</script></body></html>''')
    (project / 'deck-spec.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n')
    (project / 'hyperframes.json').write_text(json.dumps({'paths': {'assets': 'assets', 'blocks': 'compositions'}, 'media': {'autoProxy': False}}, indent=2))
    return {'project': str(project), 'duration': elapsed, 'scenes': len(refs), 'pip': pip}


class RootParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.root = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if self.root is None and 'data-composition-id' in attrs:
            self.root = attrs


def metadata(project):
    parser = RootParser()
    parser.feed((project / 'index.html').read_text())
    root = parser.root or {}
    return {key: positive(float(root.get('data-' + key, 30 if key == 'fps' else 0)), key)
            for key in ('width', 'height', 'duration', 'fps')}


def check(hf, project):
    metadata(project)
    print(run([hf, 'lint', project]), end='')
    print(run([hf, 'check', project, '--no-browser-gpu']), end='')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-setup')
    sc = sub.add_parser('scaffold')
    sc.add_argument('project', type=Path)
    sc.add_argument('--spec', required=True, type=Path)
    for name in ('check', 'preview', 'render'):
        p = sub.add_parser(name)
        p.add_argument('project', type=Path)
        if name in ('preview', 'render'):
            p.add_argument('--output', required=True, type=Path)
        if name == 'preview':
            p.add_argument('--at', help='逗号分隔秒数；默认每页中点')
        if name == 'render':
            p.add_argument('--workers', type=int, default=2, choices=range(1, 25))
            p.add_argument('--quality', choices=['draft', 'looks', 'delivery'], default='delivery')
            p.add_argument('--force', action='store_true')
    args = parser.parse_args()
    hf = dependencies()
    if args.command == 'check-setup':
        if not browser_binary():
            raise EnvironmentError('缺少锁定 Playwright Chromium；运行 scripts/install-deck-render.sh')
        if not font_available():
            raise EnvironmentError(f'缺少 {FONT} 中文字体')
        report = json.loads(run([hf, 'doctor', '--json']))
        required = {'Node.js', 'FFmpeg', 'FFprobe', 'Chrome'}
        checks = {item['name']: item for item in report['checks']}
        missing = [name for name in required if not checks.get(name, {}).get('ok')]
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if missing:
            raise EnvironmentError('HF 必需检查失败：' + ', '.join(sorted(missing)))
        print('wrapper_setup=pass; telemetry disabled; pinned versions retained; doctor optional/update notices are informational')
        return
    project = args.project.resolve()
    if args.command == 'scaffold':
        print(json.dumps(scaffold(args.spec.resolve(), project), ensure_ascii=False))
        return
    if args.command == 'check':
        check(hf, project)
        return
    output = args.output.resolve()
    if args.command == 'preview':
        if output.exists() and any(output.iterdir()):
            raise ValueError('preview 输出目录必须为空，避免混用旧静帧')
        check(hf, project)
        at = args.at
        if not at and (project / 'deck-spec.json').is_file():
            spec = json.loads((project / 'deck-spec.json').read_text())
            elapsed, times = 0, []
            for scene in spec['scenes']:
                times.append(str(elapsed + scene['duration'] / 2))
                elapsed += scene['duration']
            at = ','.join(times)
        cmd = [hf, 'snapshot', project, '--output', output, '--describe', 'false', '--no-browser-gpu']
        if at:
            duration = metadata(project)['duration']
            if any(not math.isfinite(float(t)) or not 0 <= float(t) < duration for t in at.split(',')):
                raise ValueError('preview 时间点必须在视频时长内')
            cmd += ['--at', at, '--no-end']
        print(run(cmd))
        from PIL import Image, ImageOps, ImageDraw
        frames = sorted(output.glob('*.png'))
        if not frames:
            raise RuntimeError('snapshot 未输出 PNG')
        sheet = Image.new('RGB', (640 * min(3, len(frames)), 390 * math.ceil(len(frames) / 3)), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, frame in enumerate(frames):
            with Image.open(frame) as im:
                sheet.paste(ImageOps.contain(im.convert('RGB'), (640, 360)), ((i % 3)*640, (i // 3)*390))
            draw.text(((i % 3)*640+8, (i // 3)*390+365), frame.name, fill='black')
        sheet.save(output / 'contact-sheet.jpg')
        return
    if output.suffix.lower() != '.mp4' or output == project / 'index.html':
        raise ValueError('render 输出必须为 .mp4')
    if output.exists() and not args.force:
        raise ValueError('输出已存在；检查后用 --force 显式重渲染')
    check(hf, project)
    output.parent.mkdir(parents=True, exist_ok=True)
    expected = metadata(project)
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='.deck-render-', dir=output.parent) as temp:
        dest = Path(temp) / 'render.mp4'
        from fractions import Fraction
        print(run([hf, 'render', project, '--output', dest, '--fps', str(Fraction(str(expected['fps']))),
                   '--workers', args.workers, '--quality', args.quality, '--no-browser-gpu']))
        probe = json.loads(run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', dest]))
        video = next(x for x in probe['streams'] if x['codec_type'] == 'video')
        if any(video[k] != expected[k] for k in ('width', 'height')) or abs(float(Fraction(video['r_frame_rate'])) - expected['fps']) > .01 or abs(float(probe['format']['duration']) - expected['duration']) > .12:
            raise RuntimeError('渲染尺寸/帧率/时长与 composition 不一致')
        dest.replace(output)
    report = {'output': str(output), **expected, 'render_wall_seconds': round(time.monotonic()-start, 3), 'hyperframes': '0.8.50'}
    output.with_suffix('.render.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    try:
        main()
    except (EnvironmentError, ImportError) as exc:
        print(f'[setup error] {exc}', file=sys.stderr)
        sys.exit(2)
    except (ValueError, KeyError, StopIteration, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f'[error] {exc}', file=sys.stderr)
        sys.exit(1)
