#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPARE = os.path.join(ROOT, 'plugins', 'flutter-knowledge', 'skills', 'visual-verification', 'scripts', 'compare.py')
SIZE = (750, 1624)
SUPER = 4
LINES = [
    ('Good morning', 64, (255, 255, 255)),
    ('Plans for today', 64, (255, 255, 255)),
    ('Three meetings, two deadlines, one long walk.', 28, (160, 158, 168)),
    ('Your focus block starts at nine and ends at noon.', 28, (160, 158, 168)),
    ('Lunch with the design team moved to Thursday.', 28, (160, 158, 168)),
    ('Review the quarterly numbers before tonight.', 28, (160, 158, 168)),
    ('Inbox zero, then the roadmap draft', 32, (255, 255, 255)),
    ('Call the bank about the transfer', 32, (255, 255, 255)),
]


def scene(dx=0, dy=0, button=(26, 203, 100), brighten=0):
    w, h = SIZE[0] * SUPER, SIZE[1] * SUPER
    img = Image.new('RGB', (w, h), (24, 23, 28))
    draw = ImageDraw.Draw(img)
    y = 120 * SUPER
    for text, size, color in LINES:
        font = ImageFont.load_default(size=size * SUPER)
        draw.text((48 * SUPER + dx, y + dy), text, font=font, fill=color)
        y += int(size * 1.6) * SUPER
    draw.rounded_rectangle((56 * SUPER + dx, 1100 * SUPER + dy, 694 * SUPER + dx, 1200 * SUPER + dy), radius=50 * SUPER, fill=button)
    draw.rounded_rectangle((56 * SUPER + dx, 1240 * SUPER + dy, 694 * SUPER + dx, 1340 * SUPER + dy), radius=50 * SUPER, outline=(60, 58, 66), width=2 * SUPER)
    out = img.resize(SIZE, Image.BOX)
    if brighten:
        out = Image.fromarray(np.clip(np.asarray(out, np.int16) + brighten, 0, 255).astype(np.uint8))
    return out


def run(actual, expected, *extra):
    with tempfile.TemporaryDirectory() as tmp:
        a, e = os.path.join(tmp, 'a.png'), os.path.join(tmp, 'e.png')
        actual.save(a)
        expected.save(e)
        proc = subprocess.run([sys.executable, COMPARE, '--actual', a, '--expected', e, *extra], capture_output=True, text=True)
        return proc.returncode, proc.stdout + proc.stderr


def offset(dx):
    with tempfile.TemporaryDirectory() as tmp:
        diff = os.path.join(tmp, 'diff.png')
        _, out = run(scene(dx=dx), scene(), '--output', diff)
        share = re.search(r'Differing pixels: ([0-9.]+)%', out)
        red = int((np.asarray(Image.open(diff).convert('RGB')) == (255, 32, 32)).all(axis=2).sum()) if os.path.exists(diff) else -1
        return (float(share.group(1)) if share else -1.0), red, out


CASES = [
    ('identical images match', lambda ref: (ref, ()), 0),
    ('text a quarter pixel apart matches', lambda ref: (scene(dx=1), ()), 0),
    ('everything one logical pixel apart matches', lambda ref: (scene(dx=2 * SUPER), ()), 0),
    ('everything half a logical pixel apart diagonally matches', lambda ref: (scene(dx=SUPER, dy=SUPER), ()), 0),
    ('everything four logical pixels apart fails', lambda ref: (scene(dx=8 * SUPER), ()), 1),
    ('a recolored button fails', lambda ref: (scene(button=(40, 120, 220)), ()), 1),
    ('a slightly brighter screen fails', lambda ref: (scene(brighten=18), ()), 1),
    ('--shift 0 is the strict pixel-for-pixel comparison', lambda ref: (scene(dx=2 * SUPER), ('--shift', '0')), 1),
]


def main():
    ref = scene()
    failures = 0
    for name, make, want in CASES:
        actual, extra = make(ref)
        code, out = run(actual, ref, *extra)
        ok = code == want
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name} (exit {code}, want {want})")
        if not ok:
            print('     ' + out.strip().replace('\n', '\n     '))
    share, red, out = offset(2 * SUPER)
    ok = share == 0 and red == 0
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} one logical pixel of whole-scene offset is absorbed (differing {share}%, red {red})")
    share, red, out = offset(4 * SUPER)
    ok = share > 0 and red > 0
    failures += not ok
    print(f"{'ok  ' if ok else 'FAIL'} two logical pixels of whole-scene offset show red (differing {share}%, red {red})")
    if not ok:
        print('     ' + out.strip().replace('\n', '\n     '))
    expected_colors = np.zeros((24, 24, 3), dtype=np.uint8)
    expected_colors[:, ::2] = (255, 0, 0)
    expected_colors[:, 1::2] = (0, 0, 255)
    actual_colors = np.zeros_like(expected_colors)
    actual_colors[:, 1::2] = (255, 0, 255)
    code, out = run(Image.fromarray(actual_colors), Image.fromarray(expected_colors))
    failures += code != 1
    print(f"{'ok  ' if code == 1 else 'FAIL'} new colors cannot match independent channel ranges (exit {code}, want 1)")
    with tempfile.TemporaryDirectory() as tmp:
        actual_path, expected_path = os.path.join(tmp, 'actual.png'), os.path.join(tmp, 'expected.png')
        ref.save(expected_path)
        for actual in (ref, scene(button=(40, 120, 220))):
            actual.save(actual_path)
            overlays = [os.path.join(tmp, 'text.png'), os.path.join(tmp, 'json.png')]
            commands = [[sys.executable, COMPARE, '--actual', actual_path, '--expected', expected_path, '--output', output]
                        for output in overlays]
            plain = subprocess.run(commands[0], capture_output=True, text=True)
            structured = subprocess.run(commands[1] + ['--json'], capture_output=True, text=True)
            try:
                result = json.loads(structured.stdout)
                plain_share = float(re.search(r'Differing pixels: ([0-9.]+)%', plain.stdout)[1])
                plain_cluster = float(re.search(r'Worst region:     ([0-9.]+)%', plain.stdout)[1])
                ok = (plain.returncode == structured.returncode and result['overall_percent'] == plain_share
                      and result['worst_region_percent'] == plain_cluster
                      and result['settings']['threshold'] == 0.02 and result['settings']['max_cluster'] == 0.25
                      and result['settings']['tolerance'] == 12 and result['settings']['shift'] == 2
                      and np.array_equal(np.asarray(Image.open(overlays[0])), np.asarray(Image.open(overlays[1]))))
            except (ValueError, KeyError, OSError):
                ok = False
            failures += not ok
            print(f"{'ok  ' if ok else 'FAIL'} JSON output preserves exit, percentages, thresholds and overlay pixels")
        mismatch = Image.new('RGB', (100, 100))
        mismatch.save(actual_path)
        error = subprocess.run(commands[1] + ['--json'], capture_output=True, text=True)
        try:
            result = json.loads(error.stdout)
            ok = error.returncode == 2 and result['status'] == 'ERROR' and 'overall_percent' not in result
        except ValueError:
            ok = False
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} JSON capture errors never contain invented percentages")
    bad_size = Image.new('RGB', (100, 100))
    code, _ = run(bad_size, ref)
    print(f"{'ok  ' if code == 2 else 'FAIL'} a size mismatch cannot run (exit {code}, want 2)")
    failures += code != 2
    print('all passed' if not failures else f'{failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
