#!/usr/bin/env python3
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT = os.path.join(ROOT, 'plugins', 'flutter-knowledge', 'skills', 'flutter-app-theme', 'scripts', 'token_audit.py')

SCREEN = '''import 'package:flutter/material.dart';

class Demo extends StatelessWidget {
  const Demo({super.key});

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final a = Color(0xFF112233);
    final b = Colors.red;
    final c = Colors.transparent;
    final d = EdgeInsets.all(16);
    final e = EdgeInsets.symmetric(
      horizontal: 20,
      vertical: tokens.space.sm,
    );
    final f = EdgeInsets.all(tokens.space.lg);
    final g = BorderRadius.circular(12);
    final h = BorderRadius.only(
      topLeft: Radius.circular(12),
    );
    final i = TextStyle(
      fontSize: 14,
    );
    final j = tokens.text.bodyMd.copyWith(color: tokens.skin.textPrimary);
    final k = BoxShadow(blurRadius: 4);
    final l = Duration(
      milliseconds: 300,
    );
    final m = tokens.motion.fast;
    final n = Theme.of(context)
        .colorScheme
        .primary;
    final o = SizedBox(
      height: 12,
    );
    final p = VerticalSpace(tokens.space.sm);
    final q = Theme.of(context).brightness;
    final r = DecoratedBox(decoration: BoxDecoration(color: Colors.transparent, border: Border.all(color: Colors.black12)));
    final s = SizedBox(width: double.infinity, height: tokens.space.md);
    final t = EdgeInsets.zero;
    final u = Duration.zero;
    final v = BorderRadius.circular(tokens.radius.mdValue);
    final w = EdgeInsetsDirectional.only(start: 8.w);
    final x = AppTextStyle(size: 14);
    final y = Theme.of(context).textTheme.bodyMedium;
    final z = SizedBox(height: 0);
    return const SizedBox.shrink();
  }
}
'''

WANT = {
    9: 'Color(0x',
    10: 'Colors.red',
    12: 'EdgeInsets.all(16)',
    13: 'horizontal: 20',
    18: 'BorderRadius.circular(12)',
    20: 'Radius.circular(12)',
    22: 'TextStyle(',
    26: 'BoxShadow(',
    27: 'milliseconds: 300',
    31: '.colorScheme',
    34: 'height: 12',
    38: '.brightness',
    39: 'Colors.black12',
    44: 'start: 8.w',
    46: '.textTheme',
}

THEME = '''import 'package:flutter/material.dart';

abstract final class AppSpacing {
  static const lg = 16.0;
  static const insets = EdgeInsets.all(16);
  static const brand = Color(0xFF112233);
}
'''

GENERATED = '''final shadow = BoxShadow(blurRadius: 4);
final color = Colors.red;
'''

CLEAN = '''import 'package:flutter/material.dart';

class Clean extends StatelessWidget {
  const Clean({super.key});

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: tokens.space.screenH,
        vertical: tokens.space.md,
      ),
      child: ColoredBox(color: Colors.transparent, child: Icon(Icons.add, size: 24)),
    );
  }
}
'''


def write(root, rel, text):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(text)


def audit(cwd, *paths):
    proc = subprocess.run([sys.executable, AUDIT, *paths], cwd=cwd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    failures = 0

    def check(ok, name, detail=''):
        nonlocal failures
        failures += not ok
        print(f"{'ok  ' if ok else 'FAIL'} {name}")
        if not ok and detail:
            print('     ' + detail.strip().replace('\n', '\n     '))

    with tempfile.TemporaryDirectory() as tmp:
        presentation = 'lib/feature/demo/presentation'
        write(tmp, f'{presentation}/demo_screen/ui/demo_screen.dart', SCREEN)
        write(tmp, f'{presentation}/demo_screen/ui/demo_screen.g.dart', GENERATED)
        write(tmp, 'lib/core/theme/app_spacing.dart', THEME)
        write(tmp, 'lib/feature/clean/presentation/clean.dart', CLEAN)

        code, out, err = audit(tmp, presentation)
        lines = [l for l in out.splitlines() if l.strip()]
        shape = all(re.match(r'^lib/feature/demo/presentation/demo_screen/ui/demo_screen\.dart:\d+: \S', l) for l in lines)
        check(shape and lines, 'each hit is printed as path:line: snippet', out + err)
        got = {}
        for l in lines:
            m = re.match(r'^[^:]+:(\d+): (.*)$', l)
            if m:
                got.setdefault(int(m.group(1)), []).append(m.group(2))
        check(sorted(got) == sorted(WANT), 'flags exactly the hardcoded values, at the line each call starts',
              f'want lines {sorted(WANT)}\ngot  lines {sorted(got)}\n{out}')
        for line, needle in WANT.items():
            check(any(needle in s for s in got.get(line, [])), f'line {line} snippet shows {needle!r}', repr(got.get(line)))
        check(code == 1, f'exit 1 when it finds anything (got {code})', err)
        check('demo_screen.g.dart' not in out, 'generated .g.dart files are skipped', out)

        code, out, err = audit(tmp, 'lib')
        check('lib/core/theme/' not in out, 'lib/core/theme/ is never audited', out)
        check(code == 1 and 'lib/feature/clean' not in out, 'a clean file reports nothing inside a wider run', out)

        code, out, err = audit(tmp, 'lib/feature/clean/presentation')
        check(code == 0 and not out.strip(), f'exit 0 and no output on clean code (got {code})', out + err)

        code, out, err = audit(tmp, f'{presentation}/demo_screen/ui/demo_screen.dart')
        check(code == 1 and len(out.splitlines()) == len(lines), 'a single file path is audited too', out + err)

        write(tmp, 'lib/wrapper_gaps.dart', 'VerticalSpace(14); HorizontalSpace(22); VerticalSpace(tokens.space.md);')
        code, out, err = audit(tmp, 'lib/wrapper_gaps.dart')
        check(code == 1 and len(out.splitlines()) == 2, 'literal wrapper gaps are flagged; token gaps are not', out + err)

        code, out, err = audit(tmp)
        check(code == 2, f'exit 2 with no path (got {code})', out + err)

        code, out, err = audit(tmp, 'lib/feature/missing')
        check(code == 2 and 'lib/feature/missing' in err, f'exit 2 on a path that does not exist (got {code})', out + err)

    print('all passed' if not failures else f'{failures} failed')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
