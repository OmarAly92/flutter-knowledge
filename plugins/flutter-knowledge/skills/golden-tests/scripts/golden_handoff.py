import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import state_coverage as coverage

runner = coverage.runner


def atomic_bytes(path, contents):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name(path.name + '.handoff-pending')
    with pending.open('wb') as stream:
        stream.write(contents)
        stream.flush()
        os.fsync(stream.fileno())
    pending.replace(path)


def save_transaction(out, transaction):
    atomic_bytes(out / 'transaction.json', (json.dumps(transaction, indent=2) + '\n').encode())


def run_tests(project, flutter, tests, out):
    project, out = Path(project).resolve(), Path(out).resolve()
    coverage.test_paths(project, tests)
    if Path(flutter).name != 'flutter':
        raise ValueError('Use the trusted installed Flutter executable, never a manifest command')
    before = coverage.project_snapshot(project)
    out.mkdir(parents=True, exist_ok=False)
    argv = [str(flutter), 'test', '--no-pub', '--machine', *tests]
    try:
        done = subprocess.run(argv, cwd=project, capture_output=True, text=True)
    except OSError as error:
        done = subprocess.CompletedProcess(argv, None, '', str(error))
    stdout = runner.save_log(out, 'stdout.log', done.stdout)
    stderr = runner.save_log(out, 'stderr.log', done.stderr)
    summary = coverage.machine_summary(done.stdout)
    after = coverage.project_snapshot(project)
    passed = done.returncode == 0 and summary['passed'] and before == after
    record = {'schema_version': 1, 'flutter': str(flutter), 'project': str(project), 'tests': tests, 'argv': argv,
              'exit_code': done.returncode, 'stdout': stdout, 'stderr': stderr, 'project_snapshot': before, 'finished_project_snapshot': after,
              'successful_tests': summary['successful_tests'], 'status': 'PASS' if passed else 'FAIL'}
    runner.write_json(out / 'tests.json', record)
    return record


def stage_target(out, relative, candidate, target):
    staged = out / 'staged' / relative
    staged.parent.mkdir(parents=True, exist_ok=True)
    staged.write_bytes(candidate)
    previous = None
    if target.exists():
        if not target.is_file():
            raise ValueError('Baseline target is not a file: ' + str(target))
        backup = out / 'previous' / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        backup.write_bytes(target.read_bytes())
        previous = runner.identity(backup)
    return {'path': str(target), 'staged': runner.identity(staged), 'previous': previous}


def prepare(request, report, out):
    ledger = runner.read_json(request['ledger'])
    document = runner.read_json(request['results'])
    captured = {row['id']: row for row in document['rows']}
    project = Path(report['project'])
    targets = []
    for planned in ledger['rows']:
        row = captured[planned['id']]
        baseline = runner.inside(project, project / planned['baseline'], 'baseline')
        profile_bytes = Path(row['inputs']['profile']['path']).read_bytes()
        review_path = out / 'reviews' / (planned['id'] + '.json')
        review_path.parent.mkdir(parents=True, exist_ok=True)
        runner.write_json(review_path, {'row': planned['id'], 'reviewed_at': runner.now(),
                          'candidate': row['artifacts']['actual'], 'profile': row['inputs']['profile'],
                          'prior_review': runner.identity(Path(str(baseline) + '.approval.json'))
                          if Path(str(baseline) + '.approval.json').is_file() else None,
                          'evidence': report['inputs'], 'coverage': report})
        candidates = (Path(row['artifacts']['actual']['path']).read_bytes(), profile_bytes, review_path.read_bytes())
        for suffix, contents in zip(('', '.profile.json', '.approval.json'), candidates):
            relative = planned['baseline'] + suffix
            staged = stage_target(out, relative, contents, Path(str(baseline) + suffix))
            if suffix in ('', '.profile.json'):
                expected = row['artifacts']['actual'] if not suffix else row['inputs']['profile']
                if staged['staged']['sha256'] != expected['sha256']:
                    raise ValueError('Candidate or profile changed during staging')
            targets.append(staged)
    evidence = {}
    for key, path in request.items():
        saved = out / 'evidence' / (key + '.json')
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(Path(path).read_bytes())
        evidence[key] = runner.identity(saved)
        if evidence[key]['sha256'] != report['inputs'][key]['sha256']:
            raise ValueError('Evidence changed during staging: ' + key)
    transaction = {'schema_version': 1, 'phase': 'PREPARED', 'project': str(project), 'targets': targets,
                   'request': {key: str(Path(path).resolve()) for key, path in request.items()},
                   'coverage_report': report, 'evidence': evidence, 'regression_tests': ledger['regression_tests'], 'checks': []}
    save_transaction(out, transaction)
    return transaction


def current_hash(path):
    return runner.sha256(path) if Path(path).is_file() else None


def expected_targets(transaction):
    for key, artifact in transaction['evidence'].items():
        coverage.checked_identity(artifact)
        if artifact['sha256'] != transaction['coverage_report']['inputs'][key]['sha256']:
            raise ValueError('Transaction evidence differs from validated inputs')
    ledger = runner.read_json(transaction['evidence']['ledger']['path'])
    captured = {row['id']: row for row in runner.read_json(transaction['evidence']['results']['path'])['rows']}
    project = Path(transaction['project'])
    if str(project) != runner.read_json(transaction['evidence']['results']['path'])['project']:
        raise ValueError('Transaction project differs from the captured project')
    if transaction['regression_tests'] != ledger['regression_tests']:
        raise ValueError('Transaction tests differ from declared normal regression tests')
    expected = {}
    for planned in ledger['rows']:
        baseline = runner.inside(project / 'test', project / planned['baseline'], 'baseline')
        row = captured[planned['id']]
        expected[str(baseline)] = row['artifacts']['actual']['sha256']
        expected[str(baseline) + '.profile.json'] = row['inputs']['profile']['sha256']
        expected[str(baseline) + '.approval.json'] = None
    return expected


def validate_restoration(transaction, out):
    project = Path(transaction['project'])
    expected = expected_targets(transaction)
    paths = [target['path'] for target in transaction['targets']]
    if len(set(paths)) != len(paths) or set(paths) != set(expected):
        raise ValueError('Transaction targets differ from declared baselines/profiles/reviews')
    for target in transaction['targets']:
        validate_restoration_target(target, expected, project, out)


def validate_artifact_location(artifact, root, relative):
    path = runner.inside(root, Path(artifact['path']), 'transaction artifact')
    if path != root / relative:
        raise ValueError('Transaction artifact path differs from the declared target')


def validate_restoration_target(target, expected, project, out):
    path = runner.inside(project / 'test', Path(target['path']), 'baseline')
    if path.exists() and not path.is_file():
        raise ValueError('Baseline is not a file: ' + str(path))
    relative = path.relative_to(project)
    validate_artifact_location(target['staged'], out / 'staged', relative)
    if expected[str(path)] is not None and target['staged']['sha256'] != expected[str(path)]:
        raise ValueError('Staged PNG/profile differs from the inspected capture')
    previous = target['previous']
    if previous:
        validate_artifact_location(previous, out / 'previous', relative)
        coverage.checked_identity(previous)
    allowed = (target['staged']['sha256'], previous['sha256'] if previous else None)
    if current_hash(path) not in allowed:
        raise ValueError('External baseline change; refusing overwrite: ' + str(path))


def validate_targets(transaction, out):
    validate_restoration(transaction, out)
    for target in transaction['targets']:
        coverage.checked_identity(target['staged'])


def save_recovery_report(out, transaction, approval):
    try:
        regression = retained_regression_status(transaction)
        issues = []
    except (OSError, ValueError, KeyError, TypeError) as error:
        regression = 'FAIL'
        issues = ['Historical candidate regression evidence unavailable: ' + str(error)]
    report = promotion_report(transaction, approval, regression)
    if issues:
        report['approval_issues'] = issues
    atomic_bytes(out / 'handoff.json', (json.dumps(report, indent=2) + '\n').encode())


def rollback(out):
    out = Path(out).resolve()
    transaction = runner.read_json(out / 'transaction.json')
    if transaction['phase'] in ('ROLLING_BACK', 'ROLLED_BACK'):
        save_recovery_report(out, transaction, transaction['phase'])
    try:
        validate_restoration(transaction, out)
    except (OSError, ValueError, KeyError, TypeError):
        save_recovery_report(out, transaction, 'BLOCKED')
        raise
    transaction['phase'] = 'ROLLING_BACK'
    save_transaction(out, transaction)
    save_recovery_report(out, transaction, transaction['phase'])
    for target in transaction['targets']:
        path = Path(target['path'])
        if target['previous']:
            atomic_bytes(path, Path(target['previous']['path']).read_bytes())
        elif path.exists():
            path.unlink()
    transaction['phase'] = 'ROLLED_BACK'
    save_transaction(out, transaction)
    save_recovery_report(out, transaction, transaction['phase'])
    return transaction


def promotion_report(transaction, approval, regression):
    return {'schema_version': 1, 'baseline_approval': approval, 'normal_regression': regression,
            'behavior': 'PASS', 'coverage_report': transaction['coverage_report'], 'checks': transaction['checks']}


def check_promoted(out, transaction, flutter):
    check_dir = out / ('check-' + str(len(transaction['checks']) + 1).zfill(3))
    while check_dir.exists():
        check_dir = check_dir.with_name('check-' + str(int(check_dir.name.split('-')[-1]) + 1).zfill(3))
    transaction['phase'] = 'CHECKING'
    save_transaction(out, transaction)
    checked = run_tests(Path(transaction['project']), flutter, transaction['regression_tests'], check_dir)
    transaction['checks'].append(runner.identity(check_dir / 'tests.json'))
    save_transaction(out, transaction)
    names = {row['golden_test'] for row in runner.read_json(transaction['request']['ledger'])['rows']}
    regression_passed = checked['status'] == 'PASS' and names <= set(checked['successful_tests'])
    fresh = coverage.check_coverage(transaction['request'])
    approved = regression_passed and fresh == transaction['coverage_report']
    if approved:
        validate_targets(transaction, out)
        approved = all(current_hash(target['path']) == target['staged']['sha256'] for target in transaction['targets'])
    transaction['phase'] = 'APPROVED' if approved else 'CHECK_FAILED'
    save_transaction(out, transaction)
    if not approved:
        transaction = rollback(out)
    report = promotion_report(transaction, 'APPROVED' if approved else 'ROLLED_BACK', 'PASS' if regression_passed else 'FAIL')
    if fresh != transaction['coverage_report']:
        report['current_coverage'] = fresh
        report['approval_issues'] = ['Capture/review/behavior evidence changed during the normal check']
    runner.write_json(out / 'handoff.json', report)
    return report


def retained_regression_status(transaction):
    if not transaction['checks']:
        return 'NOT_RUN'
    record = runner.read_json(coverage.checked_identity(transaction['checks'][-1]))
    stdout = coverage.checked_identity(record['stdout']).read_text(encoding='utf-8')
    coverage.checked_identity(record['stderr'])
    summary = coverage.machine_summary(stdout)
    ledger = runner.read_json(transaction['evidence']['ledger']['path'])
    names = {row['golden_test'] for row in ledger['rows']}
    passed = (record['exit_code'] == 0 and summary['passed']
              and record['project_snapshot'] == record['finished_project_snapshot']
              and names <= set(summary['successful_tests']))
    return 'PASS' if passed else 'FAIL'


def resume(out, flutter):
    out = Path(out).resolve()
    transaction = runner.read_json(out / 'transaction.json')
    if transaction['phase'] in ('ROLLED_BACK', 'ROLLING_BACK', 'CHECK_FAILED'):
        rollback(out)
        return runner.read_json(out / 'handoff.json')
    fresh = coverage.check_coverage(transaction['request'])
    if fresh['coverage'] != 'COMPLETE' or fresh != transaction['coverage_report']:
        raise ValueError('Resume blocked by changed or missing capture/review/behavior evidence; rollback remains available')
    validate_targets(transaction, out)
    if transaction['phase'] == 'APPROVED':
        if any(current_hash(t['path']) != t['staged']['sha256'] for t in transaction['targets']):
            raise ValueError('Approved baseline changed since the check')
        checked_path = coverage.checked_identity(transaction['checks'][-1])
        successful = coverage.validate_behavior(checked_path, Path(transaction['project']))
        names = {row['golden_test'] for row in runner.read_json(transaction['request']['ledger'])['rows']}
        if not names <= set(successful):
            raise ValueError('Approved regression evidence no longer covers every output')
        return promotion_report(transaction, 'APPROVED', 'PASS')
    transaction['phase'] = 'PROMOTING'
    save_transaction(out, transaction)
    for target in transaction['targets']:
        atomic_bytes(Path(target['path']), Path(target['staged']['path']).read_bytes())
    transaction['phase'] = 'PROMOTED'
    save_transaction(out, transaction)
    return check_promoted(out, transaction, flutter)


def promote(request, flutter, out):
    report = coverage.check_coverage(request)
    if report['coverage'] != 'COMPLETE':
        raise ValueError('Promotion blocked: ' + '; '.join(report['issues']))
    out = Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    prepare(request, report, out)
    return resume(out, flutter)


def main():
    parser = argparse.ArgumentParser(description='Promote inspected candidates with backups and a normal Flutter golden check.')
    actions = parser.add_subparsers(dest='action', required=True)
    behavior = actions.add_parser('behavior')
    behavior.add_argument('--project', type=Path, required=True)
    behavior.add_argument('--test', action='append', required=True)
    promote_parser = actions.add_parser('promote')
    for key in ('ledger', 'results', 'inspection', 'behavior'):
        promote_parser.add_argument('--' + key, type=Path, required=True)
    resume_parser = actions.add_parser('resume')
    rollback_parser = actions.add_parser('rollback')
    for command in (behavior, promote_parser, resume_parser):
        command.add_argument('--flutter', type=Path, required=True)
    for command in (behavior, promote_parser, resume_parser, rollback_parser):
        command.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'behavior':
            report = run_tests(args.project, args.flutter, args.test, args.out)
            code = 0 if report['status'] == 'PASS' else 1
        elif args.action == 'rollback':
            report = rollback(args.out)
            code = 0
        elif args.action == 'resume':
            report = resume(args.out, args.flutter)
            code = 0 if report['baseline_approval'] == 'APPROVED' else 1
        else:
            request = {key: getattr(args, key) for key in ('ledger', 'results', 'inspection', 'behavior')}
            report = promote(request, args.flutter, args.out)
            code = 0 if report['baseline_approval'] == 'APPROVED' else 1
        if args.action == 'behavior':
            report = {key: report[key] for key in ('status', 'exit_code', 'successful_tests')}
            report['record'] = str(args.out / 'tests.json')
        print(json.dumps(report, indent=2))
        return code
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'baseline_approval': 'BLOCKED', 'normal_regression': 'NOT_RUN', 'error': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
