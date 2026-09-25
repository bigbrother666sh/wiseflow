#!/usr/bin/env python3
"""Probe Ark without creating video tasks; optionally generate one image.

Uses AWK_GEN_KEY from the calling environment. Never prints credentials.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = 'https://ark.cn-beijing.volces.com/api/v3'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--generate-image', action='store_true', help='Make one real image generation request (billable)')
    parser.add_argument('--out-dir', default='tmp/ark-smoke-image')
    args = parser.parse_args()
    key = os.environ.get('AWK_GEN_KEY', '').strip()
    headers = {'Content-Type': 'application/json'}
    if key:
        headers['Authorization'] = f'Bearer {key}'
    # Empty content is intentionally invalid: this POST cannot create a video task.
    for model in ('doubao-seedance-2-5-260628', 'doubao-seedance-2-0-fast-260128'):
        req = urllib.request.Request(BASE + '/contents/generations/tasks',
                                     data=json.dumps({'model': model, 'content': []}).encode(),
                                     headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                print(f'{model}: unexpected HTTP {response.status}; stopping')
                return 1
        except urllib.error.HTTPError as exc:
            try:
                error = json.loads(exc.read()).get('error', {})
                code = error.get('code', 'unknown')
            except (ValueError, AttributeError):
                code = 'non-JSON error'
            print(f'{model}: HTTP {exc.code}, code={code}; no generation requested')
            if key and exc.code in (401, 403):
                print('Authentication / permission rejected; model access unverified.')
                return 1
        except urllib.error.URLError as exc:
            print(f'Network failure: {type(exc.reason).__name__}')
            return 1
    if not key:
        print('AWK_GEN_KEY missing: only unauthenticated endpoint connectivity checked; authenticated API and image generation unverified.')
        return 2
    if args.generate_image:
        return subprocess.run([
            sys.executable, str(ROOT / 'skills/awk-img-gen/scripts/gen.py'),
            '--platform', 'volc', '--prompt', '极简水彩插画，一只橘猫坐在窗边看绿色盆栽，柔和晨光，无文字，正方形构图。',
            '--out-dir', args.out_dir,
        ], check=False).returncode
    print('Only invalid-request connectivity tested; no video submitted, model entitlement unverified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
