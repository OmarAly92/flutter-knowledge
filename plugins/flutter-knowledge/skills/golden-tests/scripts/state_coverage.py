import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

RUNNER_PATH = Path(__file__).resolve().parents[2] / 'visual-verification/scripts/run_verification.py'
SPEC = importlib.util.spec_from_file_location('capture_runner', RUNNER_PATH)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def nonblank(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + ' must be a nonblank description')


def checked_identity(artifact):
    path = Path(artifact['path'])
    if not path.is_file() or runner.identity(path) != artifact:
        raise ValueError('Missing or changed evidence: ' + str(path))
    return path


def project_snapshot(project):
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError('Project snapshot requires an existing project directory')
    paths = set()
    for folder in ('lib', 'test', 'assets', 'packages'):
        for directory, subdirectories, filenames in os.walk(project / folder):
            package_root = folder == 'packages' and 'pubspec.yaml' in filenames
            if package_root:
                subdirectories[:] = [name for name in subdirectories if name not in ('.git', '.dart_tool', 'build')]
            for filename in filenames:
                path = Path(directory) / filename
                if package_root and filename == '.git':
                    continue
                if path.is_file() and (folder != 'test' or path.suffix == '.dart'):
                    paths.add(path)
    for filename in ('pubspec.yaml', 'pubspec.lock', 'dart_test.yaml', 'flutter-knowledge.yaml', '.dart_tool/package_config.json'):
        path = project / filename
        if path.is_file():
            paths.add(path)
    return {'project': str(project), 'files': {str(p.relative_to(project)): runner.sha256(p) for p in sorted(paths)}}


def test_paths(project, paths):
    if not isinstance(paths, list) or not paths or len(set(paths)) != len(paths):
        raise ValueError('Declare a nonempty unique test file list')
    for relative in paths:
        path = Path(relative)
        if path.is_absolute() or not relative.startswith('test/') or not relative.endswith('_test.dart'):
            raise ValueError('Tests must be project-relative test/*_test.dart paths, never argv')
        runner.require_file(runner.inside(project / 'test', project / path, 'test'), 'test')
    return paths


def machine_events(stdout):
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def successful_completion(starts, key, completion):
    return (key in starts and completion.get('result') == 'success'
            and completion.get('skipped') is False and completion.get('hidden') is False)


def machine_summary(stdout):
    starts, completions, errors, ended = {}, {}, [], False
    for event in machine_events(stdout):
        if event.get('type') == 'testStart':
            starts[event['test']['id']] = event['test']['name']
        elif event.get('type') == 'testDone':
            completions[event['testID']] = event
        elif event.get('type') == 'error':
            errors.append(event)
        elif event.get('type') == 'done':
            ended = event.get('success') is True
    successful = [starts[key] for key, completion in completions.items()
                  if successful_completion(starts, key, completion)]
    failed = any(c.get('result') != 'success' for c in completions.values())
    return {'successful_tests': successful, 'passed': ended and bool(successful) and not errors and not failed}


def validate_behavior(path, project):
    record = runner.read_json(path)
    stdout = checked_identity(record['stdout']).read_text(encoding='utf-8')
    checked_identity(record['stderr'])
    summary = machine_summary(stdout)
    if record['project_snapshot'] != record['finished_project_snapshot'] or record['project_snapshot'] != project_snapshot(project):
        raise ValueError('Behavior inputs changed since the recorded test run')
    if record['exit_code'] != 0 or not summary['passed']:
        raise ValueError('Behavior run failed, was empty, skipped, or has no completed tests')
    test_paths(project, record['tests'])
    expected_argv = [record['flutter'], 'test', '--no-pub', '--machine', *record['tests']]
    if record.get('argv') != expected_argv:
        raise ValueError('Behavior record is not a normal fixed-argv Flutter run')
    return summary['successful_tests']


def attestation(discovery):
    for key in ('inspector', 'inspected_at', 'notes'):
        nonblank(discovery.get(key), 'Discovery ' + key)
    if not discovery.get('evidence'):
        raise ValueError('Discovery requires actual source/code inspection evidence')
    for artifact in discovery['evidence']:
        checked_identity(artifact)


def unique_entries(entries, label):
    if not isinstance(entries, list) or not entries:
        raise ValueError(label + ' must be a nonempty list')
    indexed = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError(label + ' entries must be objects')
        row_id = entry.get('id')
        if not isinstance(row_id, str) or not runner.ROW_ID.fullmatch(row_id) or row_id in indexed:
            raise ValueError(label + ' need unique stable ids')
        indexed[row_id] = entry
    return indexed


def state_outputs(state_id, state, successful):
    required = state.get('required_rows')
    behaviors = state.get('required_behavior_tests', [])
    if not isinstance(required, list) or not isinstance(behaviors, list):
        raise ValueError(state_id + ': required_rows and required_behavior_tests must be lists')
    issues = []
    if not required:
        if not behaviors:
            issues.append(state_id + ': no required output rows or behavior checks')
        else:
            nonblank(state.get('behavior_only_reason'), state_id + ' behavior-only reason')
    for name in behaviors:
        nonblank(name, state_id + ' behavior test')
        if name not in successful:
            issues.append(state_id + ': behavior test did not complete: ' + name)
    if 'unsupported' in state:
        nonblank(state['unsupported'], state_id + ' unsupported reason')
        issues.append(state_id + ': unsupported: ' + state['unsupported'])
    return required, issues


def coverage_issues(ledger, declared_rows, successful):
    states = unique_entries(ledger['states'], 'States')
    issues, assigned = [], []
    for state_id, state in states.items():
        if not state.get('evidence'):
            issues.append(state_id + ': no inspection evidence')
        for artifact in state.get('evidence', []):
            checked_identity(artifact)
        required, missing = state_outputs(state_id, state, successful)
        issues.extend(missing)
        for row_id in required:
            if row_id not in declared_rows:
                issues.append(state_id + ': missing declared output ' + str(row_id))
            assigned.append(row_id)
    if sorted(assigned) != sorted(declared_rows):
        issues.append('Each manifest row must belong to exactly one inspected state')
    return issues


def baseline_paths(project, row):
    relative = row['baseline']
    if not isinstance(relative, str) or not relative.startswith('test/') or not relative.endswith('.png'):
        raise ValueError('Baselines must be project-relative test/*.png paths')
    baseline = runner.inside(project / 'test', project / relative, 'baseline')
    return [runner.inside(project / 'test', Path(str(baseline) + suffix), 'baseline metadata')
            for suffix in ('', '.profile.json', '.approval.json')]


def baseline_targets(project, rows):
    seen, names = set(), set()
    for row in rows.values():
        for target in baseline_paths(project, row):
            if target in seen:
                raise ValueError('Baseline and metadata paths must be unique')
            seen.add(target)
        nonblank(row.get('golden_test'), row['id'] + ' golden test')
        if row['golden_test'] in names:
            raise ValueError('Each output needs a unique golden test name')
        names.add(row['golden_test'])
        checks = row.get('behavior_tests')
        if not isinstance(checks, list) or not checks:
            raise ValueError(row['id'] + ': required behavior test names are missing')
        for name in checks:
            nonblank(name, row['id'] + ' behavior test')


def validate_binding(ledger, document):
    manifest_path = checked_identity(ledger['manifest'])
    if document['manifest'] != ledger['manifest']:
        raise ValueError('Capture results belong to another manifest')
    _, project, _, entries, _ = runner.parse_manifest(manifest_path, None)
    if str(project) != document['project']:
        raise ValueError('Capture project differs from ledger manifest')
    validate_snapshot(ledger['project_snapshot'], project, document['started_at'])
    declared = {entry['id']: entry for entry in entries}
    captured = unique_entries(document['rows'], 'Captured rows')
    if set(declared) != set(captured):
        raise ValueError('Capture must contain exactly the declared manifest rows')
    for row_id, entry in declared.items():
        validate_capture_binding(captured[row_id], entry)
    return project, declared, captured


def validate_snapshot(artifact, project, started_at):
    saved_snapshot = runner.read_json(checked_identity(artifact))
    recorded_at = saved_snapshot.pop('recorded_at')
    if recorded_at > started_at:
        raise ValueError('Project snapshot must precede the capture attempt')
    if saved_snapshot != project_snapshot(project):
        raise ValueError('Project source, camera, fonts, assets or configuration changed')


def validate_capture_binding(row, entry):
    row_id = row['id']
    if runner.provenance(entry) != row['provenance']:
        raise ValueError(row_id + ': source freshness differs from manifest/current inputs')
    if row['kind'] != entry['row']['kind'] or row['profile'] != entry['profile']:
        raise ValueError(row_id + ': capture kind/profile differ from manifest')
    expected_inputs = {'profile': runner.identity(entry['profile_path'])}
    for role in ('source', 'reference'):
        if entry[role] is not None:
            expected_inputs[role] = runner.identity(entry[role])
    for role, artifact in expected_inputs.items():
        if row['inputs'].get(role) != artifact:
            raise ValueError(row_id + ': capture ' + role + ' differs from manifest')


def camera_issues(row):
    issues = []
    if row['capture']['exit_code'] != 0:
        issues.append('camera failed')
    if 'actual' not in row['artifacts']:
        issues.append('missing candidate PNG')
    else:
        problem = runner.dimension_error(Path(row['artifacts']['actual']['path']), row['profile'])
        if problem:
            issues.append(problem)
    return issues


def comparison_issues(row):
    issues = []
    comparison = row['comparison']['status']
    if comparison == 'PASS':
        compare_json = row['artifacts'].get('compare_json')
        if not compare_json or runner.read_json(checked_identity(compare_json)) != row['comparison']:
            issues.append('comparison evidence absent or inconsistent')
        if not row.get('compare') or row['compare'].get('exit_code') != 0 or 'diff' not in row['artifacts']:
            issues.append('comparison did not produce a passing diff')
    elif comparison != 'NOT_RUN' or row['kind'] != 'regression' or 'reference' in row['inputs']:
        issues.append('comparison failed or did not run')
    return issues


def row_status(row, review, planned, successful):
    source_status, detail = runner.final_status(row, review)
    issues = camera_issues(row) + comparison_issues(row)
    if review['outcome'] != 'accepted':
        issues.append('PNG inspection rejected')
    if row['kind'] == 'source' and source_status != 'VERIFIED':
        issues.append('source fidelity is ' + source_status + ': ' + detail)
    missing = sorted(set(planned['behavior_tests']) - set(successful))
    if missing:
        issues.append('behavior tests did not complete: ' + ', '.join(missing))
    return {'id': row['id'], 'source_fidelity': source_status,
            'baseline_approval': 'BLOCKED' if issues else 'ELIGIBLE',
            'behavior': 'FAIL' if missing else 'PASS', 'normal_regression': 'NOT_RUN', 'issues': issues}


def validated_coverage(request):
    bindings = {key: runner.identity(path) for key, path in request.items()}
    ledger = runner.read_json(request['ledger'])
    if ledger.get('schema_version') != 1:
        raise ValueError('Coverage ledger schema_version must be 1')
    nonblank(ledger.get('scope'), 'Coverage scope')
    document = runner.read_json(request['results'])
    project, declared, captured = validate_binding(ledger, document)
    attestation(ledger['discovery'])
    planned = unique_entries(ledger['rows'], 'Ledger rows')
    if set(planned) != set(declared):
        raise ValueError('Ledger outputs must exactly match manifest outputs')
    baseline_targets(project, planned)
    test_paths(project, ledger['regression_tests'])
    inspection = runner.validate_inspection(Path(request['results']), Path(request['inspection']), document)
    reviews = {row['id']: row for row in inspection['rows']}
    successful = validate_behavior(request['behavior'], project)
    issues = coverage_issues(ledger, declared, successful)
    statuses = [row_status(row, reviews[row_id], planned[row_id], successful) for row_id, row in captured.items()]
    issues += [row['id'] + ': ' + issue for row in statuses for issue in row['issues']]
    if bindings != {key: runner.identity(path) for key, path in request.items()}:
        raise ValueError('Ledger, results, inspection or behavior record changed during validation')
    return {'schema_version': 1, 'coverage': 'BLOCKED' if issues else 'COMPLETE',
            'rows': statuses, 'issues': issues, 'project': str(project),
            'inputs': bindings}


def check_coverage(request):
    try:
        return validated_coverage(request)
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'schema_version': 1, 'coverage': 'BLOCKED', 'rows': [], 'issues': [str(error)],
                'baseline_approval': 'BLOCKED', 'source_fidelity': 'NOT VERIFIED',
                'behavior': 'NOT_PROVEN', 'normal_regression': 'NOT_RUN'}


def main():
    parser = argparse.ArgumentParser(description='Check declared state coverage without discovering or parsing a source.')
    actions = parser.add_subparsers(dest='action', required=True)
    snapshot = actions.add_parser('snapshot')
    snapshot.add_argument('--project', type=Path, required=True)
    check = actions.add_parser('check')
    for key in ('ledger', 'results', 'inspection', 'behavior'):
        check.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'snapshot':
        print(json.dumps(dict(project_snapshot(args.project), recorded_at=runner.now()), indent=2))
        return 0
    report = check_coverage({key: getattr(args, key) for key in ('ledger', 'results', 'inspection', 'behavior')})
    print(json.dumps(report, indent=2))
    return 0 if report['coverage'] == 'COMPLETE' else 2


if __name__ == '__main__':
    sys.exit(main())
