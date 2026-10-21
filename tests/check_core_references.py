import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'tests/fixtures/core-references/manifest.json'


def fixture_plan(components=None):
    manifest = json.loads(MANIFEST.read_text())
    selected = sorted(set(components or manifest['components']))
    unknown = set(selected) - manifest['components'].keys()
    if unknown:
        raise ValueError('Unknown components: ' + ', '.join(sorted(unknown)))
    groups = {name: manifest['components'][name] for name in selected}
    packages = sorted({name for group in groups.values() for name in group['packages']})
    return {'components': groups, 'sdk': manifest['sdk'],
            'packages': {name: manifest['tested_packages'][name] for name in packages}}


def write_fixture_file(project, target, content):
    destination = (project / target).resolve()
    if not destination.is_relative_to(project.resolve()):
        raise ValueError('Fixture output escapes its directory: ' + target)
    if destination.exists():
        raise ValueError('Duplicate fixture output: ' + target)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content)


def assemble(project, components=None):
    plan = fixture_plan(components)
    if project.exists() and any(project.iterdir()):
        raise ValueError('Fixture directory must be empty: ' + str(project))
    project.mkdir(parents=True, exist_ok=True)
    sources = {}
    for group in plan['components'].values():
        for source, target in group.get('copies', {}).items():
            path = ROOT / source
            write_fixture_file(project, target, path.read_text())
            sources[source] = hashlib.sha256(path.read_bytes()).hexdigest()
        for template in group.get('templates', []):
            path = ROOT / template['source']
            content = path.read_text()
            sources[template['source']] = hashlib.sha256(path.read_bytes()).hexdigest()
            for placeholder, source in template['bindings'].items():
                if placeholder not in content:
                    raise ValueError('Missing fixture binding: ' + placeholder)
                path = ROOT / source
                content = content.replace(placeholder, path.read_text())
                sources[source] = hashlib.sha256(path.read_bytes()).hexdigest()
            if re.search(r'@@[A-Z_]+@@', content):
                raise ValueError('Unresolved fixture binding: ' + template['source'])
            write_fixture_file(project, template['target'], content)
    pubspec = {'name': 'core_reference_check', 'environment': {'sdk': plan['sdk']},
               'dependencies': {'flutter': {'sdk': 'flutter'}, **plan['packages']},
               'dev_dependencies': {'flutter_test': {'sdk': 'flutter'}}}
    if any(group.get('uses_material_design') for group in plan['components'].values()):
        pubspec['flutter'] = {'uses-material-design': True}
    write_fixture_file(project, 'pubspec.yaml', json.dumps(pubspec, indent=2) + '\n')
    write_fixture_file(project, 'analysis_options.yaml',
                       'analyzer:\n  errors:\n    unused_import: error\n    unused_local_variable: error\n')
    write_fixture_file(project, 'reference-inputs.json', json.dumps(sources, indent=2) + '\n')
    return plan


def test_outcome(completed):
    events = []
    for line in completed.stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    failures = [event for event in events if event.get('type') == 'error' or
                (event.get('type') == 'testDone' and event.get('result') in {'failure', 'error'})]
    done = [event for event in events if event.get('type') == 'done']
    tests = [event for event in events if event.get('type') == 'testDone' and not event.get('hidden')]
    if completed.returncode:
        return completed.returncode if completed.returncode > 0 else 128 - completed.returncode
    if failures or any(event.get('success') is False for event in done):
        return 1
    if (len(done) != 1 or done[0].get('success') is not True or not tests
            or any(event.get('skipped') or event.get('result') != 'success' for event in tests)):
        return 2
    return 0


def run_reference_tests(project):
    command = ['flutter', 'test', '--no-pub', '--machine', '--timeout', '45s']
    print('Running: ' + ' '.join(command), flush=True)
    log = project / 'reference-tests.log'
    try:
        completed = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=300)
    except subprocess.TimeoutExpired as error:
        chunks = [chunk.decode('utf-8', errors='replace') if isinstance(chunk, bytes) else chunk or ''
                  for chunk in (error.stdout, error.stderr)]
        log.write_text(''.join(chunks))
        print(f'Reference tests timed out; incomplete output: {log}')
        return 2
    log.write_text(completed.stdout + completed.stderr)
    status = test_outcome(completed)
    print(f'Reference test status: {status}; full output: {log}')
    if status:
        print((completed.stdout + completed.stderr)[-8000:])
    return status


def verify(project, components=None, fetch=False):
    plan = assemble(project, components)
    if not shutil.which('flutter') or not shutil.which('dart'):
        raise RuntimeError('Flutter and Dart are required; no SDK is installed by this check')
    resolve = ['flutter', 'pub', 'get'] + ([] if fetch else ['--offline'])
    files = [str(path.relative_to(project)) for path in sorted(project.rglob('*.dart'))]
    commands = [resolve, ['dart', 'format', *files],
                ['flutter', 'analyze', '--no-pub', '--fatal-infos']]
    for command in commands:
        print('Running: ' + ' '.join(command), flush=True)
        completed = subprocess.run(command, cwd=project)
        if completed.returncode:
            return completed.returncode if completed.returncode > 0 else 128 - completed.returncode
    status = run_reference_tests(project)
    if status:
        return status
    if 'logger' in plan['components']:
        binary = project / 'build' / ('logger_release_smoke.exe' if os.name == 'nt' else 'logger_release_smoke')
        binary.parent.mkdir(exist_ok=True)
        for command in (['dart', 'compile', 'exe', 'tool/logger_release_smoke.dart', '-o', str(binary)],
                        [str(binary)]):
            print('Running: ' + ' '.join(command), flush=True)
            completed = subprocess.run(command, cwd=project, timeout=120)
            if completed.returncode:
                return completed.returncode if completed.returncode > 0 else 128 - completed.returncode
    return 0


def main():
    parser = argparse.ArgumentParser(description='Compile and exercise shipped core reference implementations in an isolated fixture.')
    parser.add_argument('--only', choices=['cache', 'logger', 'theme', 'capture'], action='append')
    parser.add_argument('--fetch', action='store_true', help='Permit fixture package downloads; default resolution is offline')
    parser.add_argument('--out', type=Path, help='Keep a fixture at a new or empty directory instead of a temporary directory')
    parser.add_argument('--list', action='store_true', help='Print the selected fixture plan without writing or running tools')
    args = parser.parse_args()
    try:
        if args.list:
            print(json.dumps(fixture_plan(args.only), indent=2))
            return 0
        if args.out:
            return verify(args.out.resolve(), args.only, args.fetch)
        with tempfile.TemporaryDirectory(prefix='flutter-core-reference-') as directory:
            return verify(Path(directory), args.only, args.fetch)
    except (ValueError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
