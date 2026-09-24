"""Regression checks for the shared visual renderer and optional collage i2v path."""

import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / 'crews/content-producer/skills/expert-video/tools/video-producer/video-producer.sh'


def command(*args, env=None, timeout=180):
    return subprocess.run([str(WRAPPER), *map(str, args)], capture_output=True,
                          text=True, env=env, timeout=timeout)


class VisualPipelineTests(unittest.TestCase):
    def test_scaffold_metadata_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / 'collage'
            result = command('visual-render', 'scaffold', project, '--width', 360,
                             '--height', 640, '--fps', 12, '--duration', 2,
                             '--background', '#D95B36')
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((project / 'assets/gsap.min.js').is_file())
            self.assertIn('data-duration="2.0"', (project / 'index.html').read_text())
            second = command('visual-render', 'scaffold', project)
            self.assertNotEqual(second.returncode, 0)
            self.assertIn('非空', second.stderr)

    @unittest.skipUnless(os.environ.get('VIDEO_PRODUCER_BROWSER_TEST') == '1',
                         'opt-in HyperFrames render test')
    def test_three_paper_layers_assemble_and_render_silent(self):
        from PIL import Image, ImageChops
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            project = tmp / 'collage'
            result = command('visual-render', 'scaffold', project, '--width', 360,
                             '--height', 640, '--fps', 12, '--duration', 2,
                             '--background', '#D95B36')
            self.assertEqual(result.returncode, 0, result.stderr)
            page = project / 'index.html'
            markup = page.read_text()
            layers = (
                '<div id="paper-1" style="position:absolute;left:40px;top:110px;width:280px;height:140px;background:#eee8d5"></div>'
                '<div id="paper-2" style="position:absolute;left:80px;top:280px;width:200px;height:100px;background:#192d2a"></div>'
                '<div id="paper-3" style="position:absolute;left:125px;top:430px;width:110px;height:90px;background:#eebf5a"></div>'
            )
            markup = markup.replace('</div><script>', layers + '</div><script>')
            timeline = (
                "tl.fromTo('#paper-1',{x:-360},{x:0,duration:0.3},0.2);"
                "tl.fromTo('#paper-2',{x:360},{x:0,duration:0.3},0.7);"
                "tl.fromTo('#paper-3',{y:640},{y:0,duration:0.3},1.2);"
            )
            markup = markup.replace('window.__timelines.main = tl;',
                                    timeline + 'window.__timelines.main = tl;')
            page.write_text(markup)
            preview = tmp / 'preview'
            result = command('visual-render', 'preview', project, '--output', preview,
                             '--at', '0,0.5,1,1.8')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            frames = sorted(preview.glob('*.png'))
            self.assertEqual(len(frames), 4)
            self.assertTrue((preview / 'contact-sheet.jpg').is_file())
            with Image.open(frames[0]) as first, Image.open(frames[-1]) as last:
                self.assertIsNotNone(ImageChops.difference(first.convert('RGB'), last.convert('RGB')).getbbox())
            output = tmp / 'collage.mp4'
            result = command('visual-render', 'render', project, '--output', output,
                             '--workers', 1, timeout=300)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)]))
            self.assertEqual([(s['width'], s['height']) for s in probe['streams'] if s['codec_type'] == 'video'],
                             [(360, 640)])
            self.assertFalse(any(s['codec_type'] == 'audio' for s in probe['streams']))
            self.assertAlmostEqual(float(probe['format']['duration']), 2, delta=.12)

    @unittest.skipUnless(os.environ.get('VIDEO_PRODUCER_BROWSER_TEST') == '1',
                         'opt-in HyperFrames render test')
    def test_outro_uses_same_renderer_and_has_silent_audio_track(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            Image.new('RGB', (360, 202), '#246b82').save(project / 'portrait.png')
            result = command('make-outro', project, '--image', 'portrait.png',
                             '--slogan', '中文 & <品牌>', '--duration', 1,
                             '--width', 360, '--fps', 12, timeout=300)
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            output = project / 'render/outro/outro.mp4'
            self.assertTrue(output.is_file())
            page = project / 'render/outro/outro.composition/index.html'
            self.assertIn('中文 &amp; &lt;品牌&gt;', page.read_text())
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(output)]))
            self.assertEqual(sum(s['codec_type'] == 'video' for s in probe['streams']), 1)
            self.assertEqual(sum(s['codec_type'] == 'audio' for s in probe['streams']), 1)
            self.assertAlmostEqual(float(probe['format']['duration']), 1, delta=.12)

    def test_batch_i2v_mutes_generated_audio_and_reuses_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source = tmp / 'source.mp4'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i',
                            'color=c=blue:s=320x240:r=12:d=1', '-f', 'lavfi', '-i',
                            'sine=frequency=440:duration=1', '-c:v', 'libx264',
                            '-threads', '1', '-c:a', 'aac', str(source)], check=True)
            stub = tmp / 'aigc-video-gen'
            stub.write_text('''#!/usr/bin/env python3
import os, pathlib, shutil, sys
args = sys.argv[1:]
shutil.copy2(os.environ['BATCH_SOURCE'], args[args.index('--output')+1])
with open(os.environ['BATCH_LOG'], 'a') as log: log.write('called\\n')
''')
            stub.chmod(0o755)
            output = tmp / 'final.mp4'
            batch = tmp / 'jobs.json'
            batch.write_text(json.dumps([{'prompt': '纸片组装', 'first_frame': 'first.png',
                                          'last_frame': 'last.png', 'output': str(output),
                                          'mute': True}]))
            env = dict(os.environ, PATH=f'{tmp}:{os.environ["PATH"]}',
                       BATCH_SOURCE=str(source), BATCH_LOG=str(tmp / 'calls.log'))
            for _ in range(2):
                result = command('batch-i2v', '--batch', batch, env=env)
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual((tmp / 'calls.log').read_text(), 'called\n')
            probe = json.loads(subprocess.check_output([
                'ffprobe', '-v', 'error', '-show_streams', '-of', 'json', str(output)]))
            self.assertFalse(any(s['codec_type'] == 'audio' for s in probe['streams']))


if __name__ == '__main__':
    unittest.main()
