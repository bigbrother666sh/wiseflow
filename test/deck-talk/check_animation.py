#!/usr/bin/env python3
"""Extract before/after frames from the smoke slides; exclude the presenter region."""
import argparse
import json
from pathlib import Path
import subprocess
from PIL import Image, ImageChops, ImageStat


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--slides', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    scenes = json.loads(Path(__file__).with_name('deck-spec.json').read_text())['scenes']
    elapsed, evidence = 0, []
    for index, scene in enumerate(scenes, 1):
        frames = []
        for phase, offset in [('before', .15), ('after', 2.0)]:
            path = out/f'scene-{index:02d}-{phase}.png'
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', str(elapsed+offset), '-i', str(args.slides), '-frames:v', '1', '-threads', '1', str(path)], check=True)
            with Image.open(path) as image:
                frames.append(image.convert('RGB').crop((80, 80, 1360, 810)))
        difference = sum(ImageStat.Stat(ImageChops.difference(*frames)).mean)/3
        evidence.append({'scene': index, 'times': [elapsed+.15, elapsed+2.0], 'mean_pixel_difference': difference})
        if difference < .5:
            raise RuntimeError(f'scene {index} has no visible change in content area')
        elapsed += scene['duration']
    (out/'animation.json').write_text(json.dumps({'scope': 'pixel-change smoke check, not semantic or lip-sync review', 'scenes': evidence}, indent=2)+'\n')


if __name__ == '__main__':
    main()
