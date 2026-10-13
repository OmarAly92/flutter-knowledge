#!/usr/bin/env python3
"""Find hardcoded visual values in Flutter widget code.

Walks the .dart files under each path (lib/core/theme/ and *.g.dart are
skipped) and prints path:line: snippet for every literal color, padding,
gap, radius, text style, shadow or duration, and every Theme.of(context)
lookup that bypasses context.tokens. Calls that dart format splits over
several lines are matched as one.

Exit codes:
  0  nothing found
  1  hardcoded values found
  2  could not run (no path, or a path that does not exist)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'flutter-init/scripts'))
from dart_source import scan_dart

NUMBER = re.compile(r'^-?(\d+(\.\d+)?|\.\d+)(\.(w|h|r|sp|sw|sh))?$')
CALL = re.compile(
    r'\b(?P<name>EdgeInsets(?:Directional)?\.\w+|BorderRadius\.circular|Radius\.circular'
    r'|VerticalSpace|HorizontalSpace|TextStyle|BoxShadow|Duration|SizedBox|Color(?:\.from(?:ARGB|RGBO))?)\s*\('
)
COLORS = re.compile(r'\bColors\.(?!transparent\b)\w+')
THEME = re.compile(r'\bTheme\.of\(\s*context\s*\)\s*\.\s*(colorScheme|textTheme|brightness)\b')
SNIPPET = 100


def closing(text: str, start: int) -> int:
    depth = 0
    i = start
    while i < len(text):
        ch = text[i]
        if ch in '\'"':
            i += 1
            while i < len(text) and text[i] != ch:
                i += 2 if text[i] == '\\' else 1
        elif ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return len(text) - 1


def arguments(inner: str) -> list[tuple[str | None, str]]:
    parts, depth, current = [], 0, ''
    for ch in inner:
        if ch in '([{':
            depth += 1
        elif ch in ')]}':
            depth -= 1
        if ch == ',' and depth == 0:
            parts.append(current)
            current = ''
        else:
            current += ch
    parts.append(current)
    out = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        named = re.match(r'^(\w+)\s*:\s*(.*)$', part, re.S)
        out.append((named.group(1), named.group(2).strip()) if named else (None, part))
    return out


def numeric(value: str) -> bool:
    if not NUMBER.match(value):
        return False
    return float(re.match(r'^-?(\d+(\.\d+)?|\.\d+)', value).group(0)) != 0


def hardcoded(name: str, args: list[tuple[str | None, str]], inner: str) -> bool:
    if name.startswith('EdgeInsets') or name == 'Duration':
        return any(numeric(v) for _, v in args)
    if name in ('BorderRadius.circular', 'Radius.circular', 'VerticalSpace', 'HorizontalSpace'):
        return bool(args) and args[0][0] is None and numeric(args[0][1])
    if name == 'SizedBox':
        return any(k in ('height', 'width') and numeric(v) for k, v in args)
    if name.startswith('Color'):
        return bool(re.match(r'^\s*(0x|\d)', inner))
    return True


def collapse(text: str) -> str:
    text = ' '.join(text.split())
    text = re.sub(r'([(\[{]) ', r'\1', text)
    text = re.sub(r',? ([)\]}])', r'\1', text)
    text = re.sub(r' \.', '.', text)
    return text if len(text) <= SNIPPET else text[: SNIPPET - 3] + '...'


def audit_text(text: str) -> list[tuple[int, str]]:
    code, _ = scan_dart(text)
    hits = []
    for m in CALL.finditer(code):
        open_at = m.end() - 1
        close_at = closing(code, open_at)
        inner = code[open_at + 1 : close_at]
        if hardcoded(m.group('name'), arguments(inner), inner):
            hits.append((m.start(), collapse(text[m.start() : close_at + 1])))
    for pattern in (COLORS, THEME):
        for m in pattern.finditer(code):
            hits.append((m.start(), collapse(text[m.start():m.end()])))
    return sorted((text.count('\n', 0, pos) + 1, snippet) for pos, snippet in hits)


def audit(path: str) -> list[tuple[int, str]]:
    with open(path, encoding='utf-8', errors='replace') as stream:
        return audit_text(stream.read())


def skipped(path: str) -> bool:
    posix = path.replace(os.sep, '/')
    return posix.endswith('.g.dart') or 'lib/core/theme/' in posix or posix.endswith('lib/core/theme')


def dart_files(root: str) -> list[str]:
    if os.path.isfile(root):
        return [] if skipped(root) else [root]
    found = []
    for directory, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if not skipped(os.path.join(directory, d)))
        for f in sorted(files):
            path = os.path.join(directory, f)
            if f.endswith('.dart') and not skipped(path):
                found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('paths', nargs='+', metavar='PATH', help='a .dart file or a folder to audit')
    args = parser.parse_args()
    missing = [p for p in args.paths if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f'error: no such file or folder: {p}', file=sys.stderr)
        return 2
    found = 0
    for root in args.paths:
        for path in dart_files(root):
            for line, snippet in audit(path):
                print(f'{path}:{line}: {snippet}')
                found += 1
    return 1 if found else 0


if __name__ == '__main__':
    sys.exit(main())
