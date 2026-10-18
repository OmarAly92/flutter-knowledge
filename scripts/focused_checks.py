import argparse
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILLS = 'plugins/flutter-knowledge/skills/'
GEMINI_REFERENCES = {
    line[1:].removeprefix('./')
    for line in (ROOT / 'GEMINI.md').read_text().splitlines()
    if line.startswith('@')
}
SUITES = {
    name: f'tests/test_{name}.py'
    for name in (
        'focused_checks', 'harness_compatibility', 'skill_selection', 'flutter_init',
        'flutter_init_bootstrap', 'flutter_core', 'flutter_review', 'token_audit',
        'compare', 'design_cache', 'verification_runner', 'stage_usage',
        'golden_handoff', 'html_to_theme', 'layout_tree', 'benchmark_grade',
    )
}
SUITES['calibration'] = SKILLS + 'visual-verification/tests/test_calibration.py'
INIT = {'flutter_init', 'flutter_init_bootstrap', 'flutter_core', 'flutter_review'}
VISUAL = {'compare', 'design_cache', 'verification_runner', 'calibration', 'golden_handoff'}
GROUPS = {
    'flutter-init': INIT,
    'flutter-core': {'flutter_core'},
    'flutter-review': {'flutter_review'},
    'flutter-app-theme': {'token_audit', 'flutter_review'},
    'golden-tests': {'golden_handoff'},
    'html-to-widget': {'layout_tree', 'html_to_theme', 'calibration'},
    'set-theme-from-html': {'html_to_theme', 'calibration'},
}
KNOWN_HELPERS = {
    'flutter-init': {'dart_source.py', 'empty_project.py', 'init_config.py', 'project_discovery.py'},
    'flutter-core': {'inspect_core.py'},
    'flutter-review': {'checks.py', 'conventions.py', 'design_evidence.py', 'review.py'},
    'flutter-app-theme': {'token_audit.py'},
    'golden-tests': {'golden_handoff.py', 'state_coverage.py'},
    'html-to-widget': {'layout-tree.js'},
    'set-theme-from-html': {'audit_fonts.py', 'audit_handoff.py', 'foundation-snapshot.js', 'import_assets.py'},
}
DEPENDENCIES = {
    'package.json', 'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock',
    'pnpm-lock.yaml', 'pyproject.toml', 'poetry.lock', 'uv.lock', 'Pipfile',
    'Pipfile.lock', 'setup.py', 'setup.cfg',
}
UNITTEST_RUNNER = '''import pathlib, sys, unittest
path = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(path.parent))
suite = unittest.defaultTestLoader.discover(str(path.parent), pattern=path.name)
result = unittest.TextTestRunner(verbosity=2).run(suite)
if result.skipped:
    print('Required checks skipped:', result.skipped, file=sys.stderr)
sys.exit(0 if result.wasSuccessful() and not result.skipped and result.testsRun else 1)
'''


def select(paths):
    selected = set()
    fallback = []
    manual = set()
    for raw in paths:
        path = PurePosixPath(raw).as_posix().removeprefix('./')
        name = PurePosixPath(path).name
        if path in GEMINI_REFERENCES:
            selected.add('harness_compatibility')
        if path in {'tests/check_state_references.py', 'tests/state_reference_test.dart'} or (
            path.startswith(SKILLS + 'flutter-state-management/references/')
            and name.endswith(('.md', '.dart', '.dart.txt'))
        ):
            manual.add('Run python3 tests/check_state_references.py with Flutter on PATH and cached recipe dependencies; '
                       'changed Dart recipes are not analyzed or exercised by this CI.')
        if path.startswith('.github/workflows/') or path in {
            'scripts/focused_checks.py', 'tests/test_focused_checks.py',
        } or name in DEPENDENCIES or (name.startswith('requirements') and name.endswith('.txt')):
            selected.update(SUITES)
        elif path in SUITES.values():
            selected.update(key for key, value in SUITES.items() if value == path)
        elif path.startswith(('.claude-plugin/', '.agents/plugins/', '.cursor-plugin/',
                              '.kimi-plugin/', '.opencode/', '.pi/', 'plugins/flutter-knowledge/hooks/',
                              'plugins/flutter-knowledge/.claude-plugin/',
                              'plugins/flutter-knowledge/.codex-plugin/')) or path in {
                                  'GEMINI.md', 'gemini-extension.json', 'install.sh',
                                  'bump-version.sh', 'version.json',
                              }:
            selected.add('harness_compatibility')
        elif path in {'benchmark/skill_selection.py', 'benchmark/selection_cases.json'}:
            selected.add('skill_selection')
        elif path.startswith('tests/fixtures/layout-tree/'):
            selected.add('layout_tree')
        elif path.startswith('tests/fixtures/html-to-theme/'):
            selected.add('html_to_theme')
        elif path.startswith(SKILLS):
            relative = path[len(SKILLS):]
            skill = relative.split('/')[0]
            if name == 'SKILL.md':
                selected.update({'harness_compatibility', 'skill_selection'})
            if '/scripts/' in relative or '/tests/' in relative:
                if skill == 'visual-verification':
                    if name == 'stage_usage.py':
                        selected.add('stage_usage')
                    elif name in {'compare.py', 'design_cache.py', 'calibrate.py', 'run_verification.py'}:
                        selected.update(VISUAL)
                        selected.add('html_to_theme')
                    else:
                        selected.update(SUITES)
                        fallback.append(path)
                elif name in KNOWN_HELPERS.get(skill, set()):
                    selected.update(GROUPS[skill])
                else:
                    selected.update(SUITES)
                    fallback.append(path)
            elif skill == 'flutter-init' and name == 'package-catalog.json':
                selected.update(INIT)
            elif PurePosixPath(path).suffix in {'.py', '.js', '.mjs', '.cjs', '.ts', '.sh', '.dart'}:
                selected.update(SUITES)
                fallback.append(path)
            elif skill == 'flutter-core' and '/references/' in relative:
                selected.add('flutter_core')
        elif path in {'benchmark/grade.py', 'benchmark/build_fixtures.py', 'benchmark/tasks.json'}:
            selected.add('benchmark_grade')
        elif PurePosixPath(path).suffix in {'.py', '.js', '.mjs', '.cjs', '.ts', '.sh', '.dart'}:
            selected.update(SUITES)
            fallback.append(path)
    suites = sorted(selected)
    return {
        'files': sorted(set(paths)),
        'suites': suites,
        'commands': [suite_command(SUITES[name]) for name in suites],
        'relevant': bool(suites),
        'browser': bool(selected & {'layout_tree', 'html_to_theme'}),
        'fallback': sorted(fallback),
        'required_manual_checks': sorted(manual),
        'not_run': ['Live harness clients', 'Native apps', 'Flutter/Dart recipe analysis and tests',
                    'Model discovery probes and implementation benchmarks'],
    }


def suite_command(path):
    if path in {SUITES['compare'], SUITES['token_audit']}:
        return [sys.executable, path]
    return [sys.executable, '-c', UNITTEST_RUNNER, path]


def git_files(base, head, merge_base=False):
    revision = f'{base}{"..." if merge_base else ".."}{head}'
    result = subprocess.run(['git', 'diff', '--name-only', '-z', '--no-renames', revision, '--'],
                            cwd=ROOT, check=True, capture_output=True)
    return [os.fsdecode(path) for path in result.stdout.split(b'\0') if path]


def event_files():
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    if 'pull_request' in event:
        pr = event['pull_request']
        return git_files(pr['base']['sha'], pr['head']['sha'], merge_base=True)
    before, after = event.get('before'), event.get('after')
    if before and after and set(before) != {'0'}:
        return git_files(before, after)
    result = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, check=True, capture_output=True)
    return [os.fsdecode(path) for path in result.stdout.split(b'\0') if path]


def require_runtimes(plan):
    if 'harness_compatibility' in plan['suites']:
        if not shutil.which('bash'):
            raise RuntimeError('Required bash runtime is unavailable')
        if not shutil.which('node'):
            raise RuntimeError('Required Node runtime is unavailable')
        subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e',
                        'await import(process.argv[1])',
                        (ROOT / '.pi/extensions/flutter-knowledge.ts').as_uri()],
                       input='', text=True, check=True)
    if plan['browser']:
        chrome = os.environ.get('CHROME_EXECUTABLE') or next((str(path) for path in (
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path(shutil.which('google-chrome') or '/missing'),
            Path(shutil.which('chromium') or '/missing'),
        ) if path.is_file()), None)
        if not chrome or not Path(chrome).is_file():
            raise RuntimeError('Required Chrome runtime is unavailable; no browser is downloaded')
        if shutil.which('npm'):
            modules = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True, check=True).stdout.strip()
            os.environ['NODE_PATH'] = os.pathsep.join(filter(None, [os.environ.get('NODE_PATH'), modules]))
        subprocess.run(['node', '-e', "require('playwright')"], check=True)
        os.environ['CHROME_EXECUTABLE'] = chrome


def execute(plan):
    require_runtimes(plan)
    for name, command in zip(plan['suites'], plan['commands']):
        print(f'Running {name}', flush=True)
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode:
            return result.returncode if result.returncode > 0 else 128 - result.returncode
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--files', nargs='*')
    source.add_argument('--base')
    source.add_argument('--all', action='store_true')
    source.add_argument('--github-event', action='store_true')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--github-output', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.all:
            paths = ['scripts/focused_checks.py']
        elif args.github_event:
            paths = event_files()
        elif args.base:
            paths = git_files(args.base, args.head)
        else:
            paths = args.files
        plan = select(paths)
        if args.github_output:
            with args.github_output.open('a') as output:
                output.write(f'relevant={str(plan["relevant"]).lower()}\n')
                output.write(f'browser={str(plan["browser"]).lower()}\n')
        print(json.dumps(plan, indent=2) if args.json else
              ('Selected: ' + ', '.join(plan['suites']) if plan['relevant'] else 'No relevant checks.'),
              flush=True)
        if plan['required_manual_checks'] and not args.json:
            print('Required manual checks: ' + ' '.join(plan['required_manual_checks']), flush=True)
        return 0 if args.dry_run else execute(plan)
    except (OSError, RuntimeError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'Focused checks failed: {error}', file=sys.stderr)
        return error.returncode if isinstance(error, subprocess.CalledProcessError) and error.returncode > 0 else 2


if __name__ == '__main__':
    sys.exit(main())
