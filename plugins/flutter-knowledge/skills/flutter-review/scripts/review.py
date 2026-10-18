import argparse
import json
import re
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path, PurePosixPath

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / 'flutter-init/scripts'))
from init_config import ConfigError, declared_packages, read_mapping, yaml
from dart_source import authored_dart
from checks import finding, inspect_scope
from conventions import source_findings, translation_findings, package_findings
from design_evidence import inspect_design

MANUAL_CHECKS = [
    'Preserve the state/data naming and ownership contract, including late async completion after disposal.',
    'Confirm Screen/Body and route-owned provisioning, repository boundaries and per-method Params.',
    'Inspect RTL/semantics, large text and parent constraints on affected UI.',
    'Review changed golden PNGs and their reason; never regenerate them merely to pass.',
    'Confirm necessary dependency additions and reuse existing components by role.',
    'Establish design-driven scope from the task; inspect every screen/state source, capture, diff and comparison settings/output.',
    'Check state/file naming, payload-free success, builder effects, controller cleanup and stale-request handling.',
]


def capture(command, cwd):
    return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=300)


def git_changes(project):
    if shutil.which('git') is None:
        return None
    root = capture(['git', 'rev-parse', '--show-toplevel'], project)
    if root.returncode:
        return None
    repo = Path(root.stdout.strip()).resolve()
    head = capture(['git', 'rev-parse', '--verify', 'HEAD'], repo)
    diff = ['git', 'diff', '--name-only', '-z', '--diff-filter=ACDMRTUXB']
    if head.returncode == 0:
        diff.append('HEAD')
    else:
        diff.append('--cached')
    changed = capture(diff, repo)
    untracked = capture(['git', 'ls-files', '--others', '--exclude-standard', '-z'], repo)
    if changed.returncode or untracked.returncode:
        raise ConfigError('Git scope could not be read')
    selected = []
    for name in (changed.stdout + untracked.stdout).split('\0'):
        if not name:
            continue
        try:
            relative = (repo / name).resolve().relative_to(project)
        except ValueError:
            continue
        selected.append(relative.as_posix())
    return sorted(set(selected))


def source_scope(project, all_files):
    changes = git_changes(project)
    if not all_files and changes is not None:
        scoped = [name for name in changes if PurePosixPath(name).parts[0] in ('lib', 'test') and (project / name).is_file() and authored_dart(project / name)]
        return scoped, 'changed and untracked files', changes
    paths = [path.relative_to(project).as_posix() for directory in ('lib', 'test')
             for path in (project / directory).rglob('*.dart') if authored_dart(path)]
    return sorted(paths), 'all authored Dart files', changes or []


def artifact_findings(changes):
    hits = []
    for path in changes:
        if 'goldens' in PurePosixPath(path).parts and path.endswith('.png'):
            hits.append(finding('golden_png', 'review', 'Inspect this changed/new baseline and its intentional reason.', path))
        elif path == 'pubspec.yaml':
            hits.append(finding('dependencies', 'review', 'Inspect dependency/asset changes against the selected config and task scope.', path))
    return hits


def dependency_changes(project, pubspec, changes):
    if 'pubspec.yaml' not in changes:
        return []
    root = capture(['git', 'rev-parse', '--show-toplevel'], project)
    if root.returncode:
        return [finding('dependency_baseline', 'review', 'No Git baseline; inspect all declared packages.', 'pubspec.yaml')]
    relative = (project / 'pubspec.yaml').relative_to(Path(root.stdout.strip()).resolve()).as_posix()
    previous = capture(['git', 'show', 'HEAD:' + relative], project)
    if previous.returncode:
        return [finding('dependency_baseline', 'review', 'No HEAD pubspec available; inspect all declared packages.', 'pubspec.yaml')]
    old = yaml.safe_load(previous.stdout)
    if not isinstance(old, dict):
        return [finding('dependency_baseline', 'review', 'HEAD pubspec is not a mapping; inspect dependency changes manually.', 'pubspec.yaml')]
    hits = []
    for section in ('dependencies', 'dev_dependencies'):
        current, before = pubspec.get(section) or {}, old.get(section) or {}
        if not isinstance(before, dict):
            hits.append(finding('dependency_baseline', 'review', f'Cannot compare HEAD {section}; inspect manually.', 'pubspec.yaml'))
            continue
        for name in sorted(current.keys() - before.keys()):
            hits.append(finding('dependency_added', 'review', f'Added {section} package {name}. Confirm purpose, existing alternatives and config selection.', 'pubspec.yaml'))
        for name in sorted(current.keys() & before.keys()):
            if current[name] != before[name]:
                hits.append(finding('dependency_changed', 'review', f'Changed {section} package {name}. Inspect its source/version constraint and check compatibility.', 'pubspec.yaml'))
    return hits


def flutter_test_failures(lines):
    failures = []
    for line in lines:
        match = re.match(r'^\d+:\d+\s+[^:]*-[1-9]\d*[^:]*:\s+(.+?)\s+\[E\]$', line)
        if match and match.group(1) not in failures:
            failures.append(match.group(1))
    if failures and 'Failing tests:' in lines:
        for line in lines[lines.index('Failing tests:') + 1:]:
            case = line.strip()
            if re.search(r'\.dart:\s', case) and case not in failures:
                failures.append(case)
    return failures


def output_lines(output):
    clean = re.sub(r'\x1b\[[0-9;]*m', '', output).replace('\r', '\n')
    return [line for line in clean.splitlines() if line.strip()]


def concise_output(output):
    lines = output_lines(output)
    failures = flutter_test_failures(lines)
    if failures:
        return 'Failing tests:\n' + '\n'.join('  ' + case for case in failures)
    if 'Failing tests:' in lines:
        selected = lines[lines.index('Failing tests:'):]
    else:
        selected = [line for line in lines if ' • ' in line or 'Error:' in line or 'Exception' in line]
        if not selected:
            selected = lines[-8:]
    summary = '\n'.join(selected)
    if len(summary) > 2000:
        summary = summary[:2000] + '\nMore details retained in the full log.'
    return summary


def retain_output(name, output, report, check, complete=True):
    check['log_complete'] = complete
    summary = output.strip()[-12000:]
    if report.get('log_directory'):
        log_path = Path(report['log_directory']) / (name + '.log')
        try:
            log_path.write_text(output, encoding='utf-8')
            summary = concise_output(output)
            check.update({'log_path': str(log_path), 'output_bytes': len(output.encode()),
                          'summary_bytes': len(summary.encode())})
        except OSError as error:
            report['findings'].append(finding('check_log', 'error', str(error), str(log_path)))
    return summary


def run_check(name, command, project, report):
    try:
        completed = capture(command, project)
    except subprocess.TimeoutExpired as error:
        check = {'name': name, 'status': 'error', 'command': command}
        report['checks'].append(check)
        chunks = [chunk.decode('utf-8', errors='replace') if isinstance(chunk, bytes) else chunk or ''
                  for chunk in (error.output, error.stderr)]
        summary = retain_output(name, ''.join(chunks), report, check, complete=False)
        message = str(error) + '\nIncomplete output: ' + summary
        if check.get('log_path'):
            message += '\nPartial log: ' + check['log_path']
        report['findings'].append(finding(name, 'error', message))
        return
    except OSError as error:
        report['checks'].append({'name': name, 'status': 'error', 'command': command})
        report['findings'].append(finding(name, 'error', str(error)))
        return
    output = completed.stdout + completed.stderr
    reported_failures = name == 'tests' and bool(flutter_test_failures(output_lines(output)))
    failed = completed.returncode != 0 or reported_failures
    status = 'failed' if failed else 'passed'
    check = {'name': name, 'status': status, 'command': command, 'exit_code': completed.returncode}
    report['checks'].append(check)
    summary = retain_output(name, output, report, check)
    if failed:
        message = summary or f'{name} returned {completed.returncode}'
        if reported_failures and completed.returncode == 0:
            message = 'Test output reports failures despite process exit code 0.\n' + message
        if check.get('log_path'):
            message += '\nFull log: ' + check['log_path']
        report['findings'].append(finding(name, 'blocking', message))


def check_configuration(project, report):
    init = SKILLS / 'flutter-init/scripts/init_config.py'
    completed = capture([sys.executable, str(init), '--project', str(project), '--check'], project)
    if completed.returncode:
        raise ConfigError('Configuration requires attention: ' + (completed.stderr or completed.stdout).strip())
    return read_mapping(project / 'flutter-knowledge.yaml')


def run_tools(project, scope, config, skip_tests, report):
    for tool in ('dart', 'flutter'):
        if shutil.which(tool) is None:
            raise ConfigError(f'Missing tool: {tool}')
    if scope:
        run_check('format', ['dart', 'format', '--output=none', '--set-exit-if-changed', *scope], project, report)
    else:
        report['checks'].append({'name': 'format', 'status': 'skipped', 'reason': 'No changed authored Dart files'})
    run_check('analysis', ['flutter', 'analyze', '--no-pub', '--fatal-infos'], project, report)
    tests = any(authored_dart(path) for path in (project / 'test').rglob('*.dart'))
    if skip_tests or not tests:
        report['checks'].append({'name': 'tests', 'status': 'skipped', 'reason': 'Explicit --skip-tests' if skip_tests else 'No authored test files'})
        return
    runner = config['packages']['test_runner']
    if runner == 'flutter_test':
        command = ['flutter', 'test', '--no-pub']
    else:
        raise ConfigError(f'No verified review command for test_runner: {runner}')
    run_check('tests', command, project, report)


def review(project, all_files, skip_tests, design_screens=None, design_report=Path('docs/design/verification.md'), log_dir=None):
    report = {'project': str(project), 'scope': [], 'scope_kind': '', 'checks': [], 'findings': [], 'manual_checks': MANUAL_CHECKS, 'design_results': [], 'completion': 'manual_review_required'}
    try:
        if log_dir is not None:
            directory = (project / log_dir).resolve()
            directory.mkdir(parents=True, exist_ok=True)
            report['log_directory'] = tempfile.mkdtemp(prefix='review-', dir=directory)
        pubspec = read_mapping(project / 'pubspec.yaml')
        declared_packages(pubspec)
        config = check_configuration(project, report)
        scope, label, changes = source_scope(project, all_files)
        report['changed_files'] = changes
        report['findings'].extend(artifact_findings(changes))
        report['scope'], report['scope_kind'] = scope, label
        report['findings'].extend(inspect_scope(project, scope, pubspec))
        report['findings'].extend(source_findings(project, scope))
        report['findings'].extend(package_findings(pubspec, config))
        report['findings'].extend(dependency_changes(project, pubspec, changes))
        translation_hits, translation_status = translation_findings(project, config, changes, all_files)
        report['findings'].extend(translation_hits)
        report['checks'].append({'name': 'translation_keys', 'status': translation_status.split(':')[0], 'reason': translation_status})
        design_hits, results, design_check = inspect_design(project, design_screens or [], design_report)
        report['findings'].extend(design_hits)
        report['design_results'] = results
        report['checks'].append(design_check)
        run_tools(project, scope, config, skip_tests, report)
    except (ValueError, OSError, yaml.YAMLError, subprocess.TimeoutExpired) as error:
        report['findings'].append(finding('configuration' if not report['scope_kind'] else 'tooling', 'error', str(error)))
    errors = any(hit['severity'] == 'error' for hit in report['findings'])
    blocking = any(hit['severity'] == 'blocking' for hit in report['findings'])
    report['completion'] = 'could_not_complete' if errors else 'blocked' if blocking else 'manual_review_required'
    return report, 2 if errors else 1 if blocking else 0


def print_report(report):
    print(f"Scope: {report['scope_kind']} ({len(report['scope'])} files)")
    for severity, label in [('error', 'COULD NOT COMPLETE'), ('blocking', 'BLOCKING'), ('review', 'REVIEW REQUIRED')]:
        entries = [entry for entry in report['findings'] if entry['severity'] == severity]
        if entries:
            print(label)
            for entry in entries:
                location = f"{entry.get('path', '')}:{entry.get('line', '')}".strip(':')
                print(f"  {location} {entry['rule']}: {entry['message']}")
    for check in report['checks']:
        print(f"{check['name']}: {check['status']} {check.get('reason', '')}")
    print('Completion: ' + report['completion'])
    print('NOT CHECKED AUTOMATICALLY — manual review still required:')
    for item in report['manual_checks']:
        print('  ' + item)


def main():
    parser = argparse.ArgumentParser(description='Read-only Flutter mechanical checks and review findings.')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--all', action='store_true', dest='all_files')
    parser.add_argument('--skip-tests', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--design-screen', action='append', default=[], help='Exact screen/state label from the evidence table; repeat for every design-backed variant in scope')
    parser.add_argument('--design-report', type=Path, default=Path('docs/design/verification.md'), help='Evidence Markdown file, relative to the project unless absolute')
    parser.add_argument('--log-dir', type=Path, help='Retain full check output in a new report directory and emit concise findings')
    args = parser.parse_args()
    report, exit_code = review(args.project.resolve(), args.all_files, args.skip_tests, args.design_screen, args.design_report, args.log_dir)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
