#!/usr/bin/env python3
"""Compare a captured screenshot against a reference design export.

Writes a legible diff image, locates where the differences cluster, and exits non-zero
when the implementation is off, so it works both in the agent loop and in CI.

Requires: pillow, numpy

Exit codes:
  0  match within thresholds
  1  difference above threshold
  2  could not run (missing file, unreadable image, bad arguments)
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn

try:
    import numpy as np
    from PIL import Image
except ImportError:
    print("error: install dependencies first: python3 -m pip install --user pillow numpy", file=sys.stderr)
    sys.exit(2)

EXIT_OK = 0
EXIT_DIFF = 1
EXIT_ERROR = 2


class ComparisonError(Exception):
    pass


def die(message: str) -> NoReturn:
    raise ComparisonError(message)


def load(path: str, label: str) -> Image.Image:
    try:
        return Image.open(path).convert("RGB")
    except FileNotFoundError:
        die(f"{label} image not found: {path}")
    except OSError as exc:
        die(f"{label} image could not be read ({path}): {exc}")


def parse_region(text: str) -> tuple[int, int, int, int]:
    parts = text.split(",")
    if len(parts) != 4:
        die(f"--ignore-region wants x,y,w,h — got {text!r}")
    try:
        x, y, w, h = (int(p) for p in parts)
    except ValueError:
        die(f"--ignore-region values must be integers — got {text!r}")
    if w <= 0 or h <= 0:
        die(f"--ignore-region width and height must be positive — got {text!r}")
    return x, y, w, h


def matches_neighbour(image: np.ndarray, other: np.ndarray, tolerance: int, shift: int) -> np.ndarray:
    h, w, _ = other.shape
    padded = np.pad(other, ((shift, shift), (shift, shift), (0, 0)), mode="edge")
    matches = np.zeros((h, w), dtype=bool)
    for dy in range(2 * shift + 1):
        for dx in range(2 * shift + 1):
            window = padded[dy : dy + h, dx : dx + w]
            matches |= (np.abs(image - window) <= tolerance).all(axis=2)
    return matches


def diff_mask(actual: Image.Image, expected: Image.Image, tolerance: int, shift: int) -> np.ndarray:
    a = np.asarray(actual, dtype=np.int16)
    e = np.asarray(expected, dtype=np.int16)
    if shift == 0:
        return np.abs(a - e).max(axis=2) > tolerance
    return ~matches_neighbour(a, e, tolerance, shift) | ~matches_neighbour(e, a, tolerance, shift)


def worst_cluster(mask: np.ndarray, grid: int = 12) -> tuple[float, tuple[int, int, int, int]]:
    """Density of the most-affected grid cell, and its pixel box.

    A global percentage hides a defect that is small but obvious — a control shifted four
    pixels covers a fraction of a percent of the screen and is the first thing a designer
    notices. Grading the worst cell as well as the whole image catches that.
    """
    h, w = mask.shape
    best = 0.0
    box = (0, 0, 0, 0)
    for ri in range(grid):
        y0, y1 = ri * h // grid, (ri + 1) * h // grid
        for ci in range(grid):
            x0, x1 = ci * w // grid, (ci + 1) * w // grid
            cell = mask[y0:y1, x0:x1]
            if cell.size == 0:
                continue
            share = float(cell.mean())
            if share > best:
                best = share
                box = (x0, y0, x1 - x0, y1 - y0)
    return best, box


def bounding_box(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)
    if not rows.any():
        return None
    y0, y1 = int(np.argmax(rows)), int(len(rows) - np.argmax(rows[::-1]))
    x0, x1 = int(np.argmax(cols)), int(len(cols) - np.argmax(cols[::-1]))
    return x0, y0, x1 - x0, y1 - y0


def write_overlay(actual: Image.Image, mask: np.ndarray, path: str) -> None:
    """Faded capture with differing pixels burned in as red."""
    base = (np.asarray(actual, dtype=np.float32) * 0.35 + 255.0 * 0.65).astype(np.uint8)
    base[mask] = (255, 32, 32)
    try:
        Image.fromarray(base, mode="RGB").save(path)
    except OSError as exc:
        die(f"could not write diff image to {path}: {exc}")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--actual", required=True, help="Captured screenshot")
    p.add_argument("--expected", required=True, help="Reference design export")
    p.add_argument("--output", help="Where to write the diff image")
    p.add_argument(
        "--threshold",
        type=float,
        default=0.02,
        help="Maximum acceptable share of differing pixels across the whole image (default 0.02)",
    )
    p.add_argument(
        "--max-cluster",
        type=float,
        default=0.25,
        help=(
            "Maximum acceptable share of differing pixels within any single grid cell "
            "(default 0.25). Catches a localized defect that the global threshold misses."
        ),
    )
    p.add_argument(
        "--tolerance",
        type=int,
        default=12,
        help="Per-channel value difference tolerated before a pixel counts as differing",
    )
    p.add_argument(
        "--shift",
        type=int,
        default=2,
        help=(
            "Misalignment absorbed, in image pixels (default 2: one logical pixel at "
            "ratio 2): a pixel matches when its complete RGB color matches a pixel in the other "
            "image within that distance and tolerance. A larger offset shows red, and how much of "
            "the screen it covers decides whether it fails: a small element can stay under "
            "the thresholds, so read the diff image. 0 compares pixel for pixel."
        ),
    )
    p.add_argument(
        "--ignore-region",
        action="append",
        default=[],
        metavar="X,Y,W,H",
        help="Exclude a rectangle from the comparison. Repeatable. Use for inherently "
        "dynamic content such as a status bar clock.",
    )
    p.add_argument(
        "--allow-resize",
        action="store_true",
        help="Rescale the reference when the sizes differ instead of failing. Off by "
        "default: a size mismatch is nearly always a wrong export scale, and resizing "
        "manufactures edge noise that hides the real defect.",
    )
    p.add_argument("--json", action="store_true", help="Emit compact comparison evidence without changing scoring")
    args = p.parse_args()

    if not 0.0 <= args.threshold <= 1.0:
        die("--threshold is a share between 0 and 1")
    if not 0.0 <= args.max_cluster <= 1.0:
        die("--max-cluster is a share between 0 and 1")
    if args.shift < 0:
        die("--shift is a number of pixels, 0 or more")

    actual = load(args.actual, "captured")
    expected = load(args.expected, "reference")

    if actual.size != expected.size:
        message = (
            f"size mismatch: captured {actual.size[0]}x{actual.size[1]}, "
            f"reference {expected.size[0]}x{expected.size[1]}"
        )
        if not args.allow_resize:
            die(
                f"{message}. The export scale does not match the capture device pixel "
                "ratio — fix the export or the harness rather than the widget. Pass "
                "--allow-resize to compare anyway."
            )
        if not args.json:
            print(f"warning: {message} — rescaling the reference; edge noise below is expected")
        expected = expected.resize(actual.size, Image.LANCZOS)

    mask = diff_mask(actual, expected, args.tolerance, args.shift)

    height, width = mask.shape
    for region in args.ignore_region:
        x, y, w, h = parse_region(region)
        mask[max(0, y) : y + h, max(0, x) : x + w] = False
    if args.ignore_region and not args.json:
        print(f"Ignoring {len(args.ignore_region)} region(s) of {width}x{height}")

    ratio = float(mask.mean())
    cluster, cluster_box = worst_cluster(mask)

    if not args.json:
        print(f"Differing pixels: {ratio:.2%} (threshold {args.threshold:.2%})")
        print(f"Worst region:     {cluster:.2%} (threshold {args.max_cluster:.2%})")

    if args.output:
        write_overlay(actual, mask, args.output)
        if not args.json:
            print(f"Diff image:       {args.output}  (differences in red)")

    over_global = ratio > args.threshold
    over_local = cluster > args.max_cluster

    if args.json:
        result = {
            'status': 'DIFF' if over_global or over_local else 'PASS',
            'overall_ratio': ratio, 'worst_region_ratio': cluster,
            'overall_percent': round(ratio * 100, 2),
            'worst_region_percent': round(cluster * 100, 2),
            'size': {'width': width, 'height': height},
            'settings': {'threshold': args.threshold, 'max_cluster': args.max_cluster,
                         'tolerance': args.tolerance, 'shift': args.shift,
                         'ignored_regions': args.ignore_region, 'allow_resize': args.allow_resize},
            'artifacts': {'actual': args.actual, 'expected': args.expected, 'diff': args.output},
            'bounds': bounding_box(mask), 'worst_region_bounds': cluster_box,
            'inspection_required': True,
        }
        print(json.dumps(result))
        return EXIT_DIFF if over_global or over_local else EXIT_OK

    if not (over_global or over_local):
        print("PASS")
        return EXIT_OK

    print()
    if over_global and over_local:
        print("FAIL — difference above both the overall and the localized threshold.")
    elif over_global:
        print("FAIL — overall difference above threshold.")
    else:
        print(
            "FAIL — localized difference above threshold. The overall share is small, "
            "so this is a specific element in the wrong place rather than a global "
            "color or scale problem."
        )

    box = bounding_box(mask)
    if box:
        print(f"  all differences fit in x={box[0]} y={box[1]} w={box[2]} h={box[3]}")
    print(f"  densest at        x={cluster_box[0]} y={cluster_box[1]} w={cluster_box[2]} h={cluster_box[3]}")

    if ratio > 0.5:
        print(
            "\n  Over half the pixels differ. Check the font is bundled and the theme "
            "and locale match before touching layout."
        )
    elif box and box[2] >= width * 0.9 and box[3] >= height * 0.9:
        print(
            "\n  Differences span the whole image. That points at a wrong color token, "
            "a missing font, or a scale mismatch — not a layout error."
        )

    return EXIT_DIFF


if __name__ == "__main__":
    try:
        sys.exit(main())
    except ComparisonError as error:
        if '--json' in sys.argv:
            print(json.dumps({'status': 'ERROR', 'error': str(error), 'inspection_required': True}))
        else:
            print(f'error: {error}', file=sys.stderr)
        sys.exit(EXIT_ERROR)
    except KeyboardInterrupt:
        sys.exit(EXIT_ERROR)
