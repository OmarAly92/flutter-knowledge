import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/flutter-knowledge/skills/golden-tests/scripts'
sys.path.insert(0, str(SCRIPTS))
import state_coverage as coverage
import golden_handoff as handoff


class GoldenHandoffTests(unittest.TestCase):
    def setUp(self):
        self.sandbox = tempfile.TemporaryDirectory()
        self.addCleanup(self.sandbox.cleanup)
        self.root = Path(self.sandbox.name).resolve()
        self.project = self.root / 'app'
        (self.project / 'lib').mkdir(parents=True)
        (self.project / 'test').mkdir()
        (self.project / 'lib/screen.dart').write_text('auth screen with focus and error')
        (self.project / 'test/camera_test.dart').write_text('real camera contract')
        (self.project / 'test/behavior_test.dart').write_text('real behavior contract')
        self.authored_inputs = (
            'lib/feature/build/screen.dart', 'assets/build/font.otf',
            'packages/local/lib/build/widget.dart', 'test/feature/build/camera_test.dart',
            'lib/feature/.git/screen.dart', 'assets/.dart_tool/font.otf',
            'packages/local/lib/.dart_tool/widget.dart', 'test/feature/.git/camera_test.dart')
        for relative in self.authored_inputs:
            authored = self.project / relative
            authored.parent.mkdir(parents=True, exist_ok=True)
            authored.write_bytes(b'authored snapshot input')
        (self.project / 'packages/local/pubspec.yaml').write_text('name: local')
        self.profile = self.root / 'profile.json'
        self.profile.write_text(json.dumps({
            'viewport': {'width': 16, 'height': 12}, 'dpr': 2,
            'screen': 'auth', 'state': 'error', 'selector': '.auth',
            'skin': 'dark', 'locale': 'en', 'text_scale': 1,
            'capture_adapter': 'test-camera', 'data': {'fixture': 'error'},
            'safe_area': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
            'conditions': {'fonts': 'bundled', 'shadows': True, 'motion': 'settled',
                           'pointer': 'none', 'expected_state': 'error', 'keyboard_inset': 0}}))
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'schema_version': 1, 'project': str(self.project),
            'capture': {'command': ['flutter', 'test', 'test/camera_test.dart',
                                    '--dart-define=CAPTURE_ROUND={attempt}']},
            'rows': [{'id': 'error', 'label': 'auth error', 'kind': 'regression',
                      'profile': str(self.profile), 'actual': 'test/candidates/{attempt}/error.png'}]}))
        self.snapshot = self.root / 'snapshot.json'
        coverage.runner.write_json(self.snapshot, dict(coverage.project_snapshot(self.project), recorded_at=coverage.runner.now()))
        self.real_run = subprocess.run
        with patch.object(coverage.runner.subprocess, 'run', side_effect=self.camera):
            self.attempt, _ = coverage.runner.run_manifest(self.manifest, self.root / 'captures')
        self.results = self.attempt / 'results.json'
        review = coverage.runner.template(self.results)
        review.update(inspector='test fixture reviewer', inspected_at=coverage.runner.now())
        for row in review['rows']:
            row.update(inspected=True, outcome='accepted', notes='Opened full PNG; error state and type inspected')
        self.inspection = self.root / 'inspection.json'
        coverage.runner.write_json(self.inspection, review)
        self.ledger = self.root / 'ledger.json'
        self.ledger_data = {
            'schema_version': 1, 'scope': 'minimal auth error exercise', 'manifest': coverage.runner.identity(self.manifest),
            'project_snapshot': coverage.runner.identity(self.snapshot),
            'discovery': {'inspector': 'test fixture reader', 'inspected_at': coverage.runner.now(),
                          'notes': 'Driven error state; read source and camera',
                          'evidence': [coverage.runner.identity(self.project / 'lib/screen.dart')]},
            'states': [{'id': 'auth-error', 'evidence': [coverage.runner.identity(self.project / 'lib/screen.dart')],
                        'required_rows': ['error']}],
            'rows': [{'id': 'error', 'baseline': 'test/goldens/error.png',
                      'golden_test': 'auth error', 'behavior_tests': ['validation displays error']}],
            'regression_tests': ['test/camera_test.dart']}
        self.save_ledger()
        self.behavior = self.root / 'behavior'
        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
            handoff.run_tests(self.project, Path('/trusted/flutter'), ['test/behavior_test.dart'], self.behavior)
        self.request = {'ledger': self.ledger, 'results': self.results,
                        'inspection': self.inspection, 'behavior': self.behavior / 'tests.json'}

    def camera(self, argv, **kwargs):
        if argv[0] != 'flutter':
            return self.real_run(argv, **kwargs)
        round_id = next(arg.rsplit('=', 1)[1] for arg in argv if arg.startswith('--dart-define=CAPTURE_ROUND='))
        target = self.project / 'test/candidates' / round_id / 'error.png'
        target.parent.mkdir(parents=True)
        Image.new('RGB', (32, 24), 'navy').save(target)
        return subprocess.CompletedProcess(argv, 0, 'camera output', '')

    def successful_tests(self, argv, **kwargs):
        names = ['auth error'] if 'test/camera_test.dart' in argv else ['validation displays error']
        events = [{'type': 'testStart', 'test': {'id': i, 'name': name}} for i, name in enumerate(names)]
        events += [{'type': 'testDone', 'testID': i, 'result': 'success', 'skipped': False, 'hidden': False}
                   for i in range(len(names))]
        events += [{'type': 'done', 'success': True}]
        return subprocess.CompletedProcess(argv, 0, '\n'.join(json.dumps(event) for event in events), '')

    def save_ledger(self):
        coverage.runner.write_json(self.ledger, self.ledger_data)

    def test_nested_authored_input_additions_edits_and_deletions_block_promotion(self):
        for relative in self.authored_inputs:
            original = self.project / relative
            contents = original.read_bytes()
            added = original.with_name('added-' + original.name)
            for change in ('addition', 'edit', 'deletion'):
                with self.subTest(path=relative, change=change):
                    before = coverage.project_snapshot(self.project)
                    if change == 'addition':
                        added.write_bytes(b'new authored input')
                    elif change == 'edit':
                        original.write_bytes(b'changed authored input')
                    else:
                        original.unlink()
                    try:
                        self.assertNotEqual(before, coverage.project_snapshot(self.project))
                        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')
                        with self.assertRaises(ValueError):
                            handoff.promote(self.request, Path('/trusted/flutter'), self.root / 'blocked')
                        self.assertFalse((self.project / 'test/goldens/error.png').exists())
                    finally:
                        original.write_bytes(contents)
                        added.unlink(missing_ok=True)
                    self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'COMPLETE')

    def test_known_package_caches_do_not_hide_nested_authored_directories(self):
        before = coverage.project_snapshot(self.project)
        for relative in ('packages/local/build/output.dart', 'packages/local/.git/index',
                         'packages/local/.dart_tool/generated.dart'):
            with self.subTest(cache=relative):
                generated = self.project / relative
                generated.parent.mkdir(parents=True, exist_ok=True)
                generated.write_bytes(b'cache added')
                self.assertEqual(before, coverage.project_snapshot(self.project))
                generated.write_bytes(b'cache edited')
                self.assertEqual(before, coverage.project_snapshot(self.project))
                generated.unlink()
                self.assertEqual(before, coverage.project_snapshot(self.project))
        for relative in self.authored_inputs:
            self.assertIn(relative, before['files'])

    def test_visible_loading_state_names_supply_behavior_and_hidden_loaders_do_not(self):
        self.ledger_data['rows'][0]['behavior_tests'] = ['loading state shows progress']
        self.save_ledger()
        for hidden, accepted in ((False, True), (True, False), (None, False)):
            with self.subTest(hidden=hidden):
                events = [
                    {'type': 'testStart', 'test': {'id': 1, 'name': 'loading test/behavior_test.dart',
                     'groupIDs': [], 'metadata': {'skip': False, 'skipReason': None}, 'url': None}},
                    {'type': 'testDone', 'testID': 1, 'result': 'success', 'skipped': False, 'hidden': True},
                    {'type': 'testStart', 'test': {'id': 4, 'name': 'loading state shows progress',
                     'groupIDs': [2], 'metadata': {'skip': False, 'skipReason': None},
                     'url': 'package:flutter_test/src/widget_tester.dart'}},
                    {'type': 'testDone', 'testID': 4, 'result': 'success', 'skipped': False},
                    {'type': 'done', 'success': True}]
                if hidden is not None:
                    events[-2]['hidden'] = hidden
                folder = self.root / ('loading-' + str(hidden))
                with patch.object(handoff.subprocess, 'run', return_value=subprocess.CompletedProcess(
                        ['flutter'], 0, '\n'.join(json.dumps(event) for event in events), '')):
                    checked = handoff.run_tests(self.project, Path('/trusted/flutter'),
                                                ['test/behavior_test.dart'], folder)
                report = coverage.check_coverage(dict(self.request, behavior=folder / 'tests.json'))
                self.assertEqual(checked['status'], 'PASS' if accepted else 'FAIL')
                self.assertEqual(report['coverage'], 'COMPLETE' if accepted else 'BLOCKED')
                self.assertNotIn('loading test/behavior_test.dart', checked['successful_tests'])
                if accepted:
                    self.ledger_data['rows'][0]['golden_test'] = 'loading auth error'
                    self.save_ledger()
                    events[2]['test']['name'] = 'loading auth error'
                    with patch.object(handoff.subprocess, 'run', return_value=subprocess.CompletedProcess(
                            ['flutter'], 0, '\n'.join(json.dumps(event) for event in events), '')):
                        promoted = handoff.promote(dict(self.request, behavior=folder / 'tests.json'),
                                                   Path('/trusted/flutter'), self.root / 'loading-golden')
                    self.assertEqual(promoted['baseline_approval'], 'APPROVED')
                    self.assertEqual(promoted['normal_regression'], 'PASS')

    def test_rollback_cli_restores_history_or_removes_new_targets_despite_lost_staging(self):
        baseline = self.project / 'test/goldens/error.png'
        baseline.parent.mkdir()
        targets = [Path(str(baseline) + suffix) for suffix in ('', '.profile.json', '.approval.json')]
        for historical in (True, False):
            for role in range(3):
                for damage in ('missing', 'tampered'):
                    with self.subTest(historical=historical, role=role, damage=damage):
                        originals = {path: b'historical ' + path.name.encode() for path in targets} if historical else {}
                        for path in targets:
                            if historical:
                                path.write_bytes(originals[path])
                            else:
                                path.unlink(missing_ok=True)
                        out = self.root / ('recover-' + str(historical) + '-' + str(role) + '-' + damage)
                        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
                            handoff.promote(self.request, Path('/trusted/flutter'), out)
                        transaction = coverage.runner.read_json(out / 'transaction.json')
                        staged = Path(transaction['targets'][role]['staged']['path'])
                        if damage == 'missing':
                            staged.unlink()
                        else:
                            staged.write_bytes(b'tampered replacement')
                        returned = self.real_run([sys.executable, str(SCRIPTS / 'golden_handoff.py'),
                                                 'rollback', '--out', str(out)], capture_output=True, text=True)
                        self.assertEqual(returned.returncode, 0, returned.stdout + returned.stderr)
                        self.assertEqual(json.loads(returned.stdout)['phase'], 'ROLLED_BACK')
                        self.assertEqual({p: p.read_bytes() for p in targets if p.exists()}, originals)
                        persisted = coverage.runner.read_json(out / 'handoff.json')
                        self.assertEqual(persisted['baseline_approval'], 'ROLLED_BACK')
                        self.assertEqual(persisted['normal_regression'], 'PASS')
                        for target in transaction['targets']:
                            if target['previous']:
                                self.assertEqual(coverage.runner.identity(target['previous']['path']), target['previous'])

    def test_rollback_revokes_durable_approval_before_interrupted_restore_and_resume(self):
        baseline = self.project / 'test/goldens/error.png'
        baseline.parent.mkdir()
        originals = {Path(str(baseline) + suffix): b'previous ' + suffix.encode()
                     for suffix in ('', '.profile.json', '.approval.json')}
        for path, contents in originals.items():
            path.write_bytes(contents)
        out = self.root / 'interrupted-restore'
        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
            handoff.promote(self.request, Path('/trusted/flutter'), out)
        replacement = Path.replace

        def interrupted_replace(pending, destination):
            if Path(destination) == Path(str(baseline) + '.profile.json'):
                raise OSError('interrupted profile restoration')
            return replacement(pending, destination)

        with patch.object(Path, 'replace', interrupted_replace):
            with self.assertRaisesRegex(OSError, 'interrupted profile restoration'):
                handoff.rollback(out)
        self.assertEqual(baseline.read_bytes(), originals[baseline])
        self.assertEqual(coverage.runner.read_json(out / 'transaction.json')['phase'], 'ROLLING_BACK')
        persisted = coverage.runner.read_json(out / 'handoff.json')
        self.assertEqual(persisted['baseline_approval'], 'ROLLING_BACK')
        self.assertEqual(persisted['normal_regression'], 'PASS')
        transaction = coverage.runner.read_json(out / 'transaction.json')
        Path(transaction['targets'][0]['staged']['path']).unlink()
        returned = self.real_run([sys.executable, str(SCRIPTS / 'golden_handoff.py'), 'resume',
                                 '--out', str(out), '--flutter', '/trusted/flutter'], capture_output=True, text=True)
        self.assertEqual(returned.returncode, 1, returned.stdout + returned.stderr)
        self.assertEqual(json.loads(returned.stdout)['baseline_approval'], 'ROLLED_BACK')
        self.assertEqual({p: p.read_bytes() for p in originals}, originals)
        self.assertEqual(coverage.runner.read_json(out / 'handoff.json')['baseline_approval'], 'ROLLED_BACK')

    def test_rollback_with_lost_staging_still_rejects_external_edits_and_invalid_backups(self):
        baseline = self.project / 'test/goldens/error.png'
        baseline.parent.mkdir()
        for damage in ('external-target', 'backup-bytes', 'backup-escape', 'target-escape', 'staging-escape'):
            with self.subTest(damage=damage):
                baseline.write_bytes(b'historical image')
                out = self.root / damage
                with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
                    handoff.promote(self.request, Path('/trusted/flutter'), out)
                transaction = coverage.runner.read_json(out / 'transaction.json')
                target = transaction['targets'][0]
                Path(target['staged']['path']).unlink()
                external = self.root / ('outside-' + damage)
                external.write_bytes(b'historical image')
                if damage == 'external-target':
                    baseline.write_bytes(b'external edit')
                elif damage == 'backup-bytes':
                    Path(target['previous']['path']).write_bytes(b'changed backup')
                elif damage == 'backup-escape':
                    target['previous'] = coverage.runner.identity(external)
                elif damage == 'target-escape':
                    target['path'] = str(external)
                else:
                    target['staged']['path'] = str(external)
                coverage.runner.write_json(out / 'transaction.json', transaction)
                installed = baseline.read_bytes()
                returned = self.real_run([sys.executable, str(SCRIPTS / 'golden_handoff.py'),
                                         'rollback', '--out', str(out)], capture_output=True, text=True)
                self.assertEqual(returned.returncode, 2, returned.stdout + returned.stderr)
                self.assertEqual(json.loads(returned.stdout)['baseline_approval'], 'BLOCKED')
                self.assertEqual(coverage.runner.read_json(out / 'handoff.json')['baseline_approval'], 'BLOCKED')
                self.assertEqual(baseline.read_bytes(), installed)
                self.assertEqual(external.read_bytes(), b'historical image')
                for suffix in ('', '.profile.json', '.approval.json'):
                    Path(str(baseline) + suffix).unlink(missing_ok=True)

    def test_rollback_with_unavailable_historical_check_revokes_approval_and_restores(self):
        out = self.root / 'lost-check'
        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
            handoff.promote(self.request, Path('/trusted/flutter'), out)
        (out / 'check-001/stdout.log').unlink()
        returned = self.real_run([sys.executable, str(SCRIPTS / 'golden_handoff.py'),
                                 'rollback', '--out', str(out)], capture_output=True, text=True)
        self.assertEqual(returned.returncode, 0, returned.stdout + returned.stderr)
        persisted = coverage.runner.read_json(out / 'handoff.json')
        self.assertEqual(persisted['baseline_approval'], 'ROLLED_BACK')
        self.assertEqual(persisted['normal_regression'], 'FAIL')
        self.assertTrue(persisted['approval_issues'])
        self.assertFalse((self.project / 'test/goldens/error.png').exists())

    def test_regression_without_design_can_be_approved_but_never_source_verified(self):
        report = coverage.check_coverage(self.request)
        self.assertEqual(report['coverage'], 'COMPLETE')
        self.assertEqual(report['rows'][0]['source_fidelity'], 'NOT VERIFIED')
        self.assertEqual(report['rows'][0]['baseline_approval'], 'ELIGIBLE')
        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
            report = handoff.promote(self.request, Path('/trusted/flutter'), self.root / 'promotion')
        self.assertEqual(report['baseline_approval'], 'APPROVED')
        self.assertEqual(report['normal_regression'], 'PASS')
        self.assertEqual(report['coverage_report']['rows'][0]['source_fidelity'], 'NOT VERIFIED')
        argv = json.loads((self.root / 'promotion/check-001/tests.json').read_text())['argv']
        self.assertNotIn('--update-goldens', argv)

    def test_omitted_or_unsupported_states_block_all_promotion(self):
        for state in ({'id': 'focus', 'evidence': self.ledger_data['states'][0]['evidence'], 'required_rows': ['focus']},
                      {'id': 'loading', 'evidence': self.ledger_data['states'][0]['evidence'],
                       'required_rows': [], 'unsupported': 'No controlled loading camera yet'}):
            with self.subTest(state=state['id']):
                self.ledger_data['states'].append(state)
                self.save_ledger()
                report = coverage.check_coverage(self.request)
                self.assertEqual(report['coverage'], 'BLOCKED')
                self.assertTrue(report['issues'])
                with self.assertRaises(ValueError):
                    handoff.promote(self.request, Path('/trusted/flutter'), self.root / state['id'])
                self.assertFalse((self.project / 'test/goldens/error.png').exists())
                self.ledger_data['states'].pop()

    def test_failed_uninspected_stale_or_missing_evidence_cannot_be_promoted(self):
        originals = {p: p.read_bytes() for p in (self.results, self.inspection, self.profile,
                                               self.project / 'lib/screen.dart')}
        mutations = [
            (self.inspection, lambda d: d['rows'][0].update(inspected=False)),
            (self.inspection, lambda d: d['rows'][0].update(outcome='rejected')),
            (self.results, lambda d: d['rows'][0]['capture'].update(exit_code=1)),
            (self.results, lambda d: d['rows'][0]['comparison'].update(status='DIFF')),
        ]
        for target, mutation in mutations:
            with self.subTest(target=target.name, mutation=mutation):
                payload = json.loads(originals[target]); mutation(payload)
                coverage.runner.write_json(target, payload)
                if target == self.results:
                    review = json.loads(originals[self.inspection])
                    review['results_sha256'] = coverage.runner.sha256(self.results)
                    coverage.runner.write_json(self.inspection, review)
                self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')
                for path, contents in originals.items():
                    path.write_bytes(contents)
        for target in (self.profile, self.project / 'lib/screen.dart', self.behavior / 'stdout.log'):
            with self.subTest(stale=target.name):
                contents = target.read_bytes(); target.write_bytes(contents + b'changed')
                self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')
                target.write_bytes(contents)
        actual = Path(json.loads(self.results.read_text())['rows'][0]['artifacts']['actual']['path'])
        actual.unlink()
        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')

    def test_source_numeric_pass_without_freshness_does_not_qualify_as_regression(self):
        manifest = json.loads(self.manifest.read_text())
        reference = self.root / 'reference.png'; Image.new('RGB', (32, 24), 'navy').save(reference)
        source = self.root / 'source.html'; source.write_text('<input>')
        manifest['rows'][0].update(kind='source', source={'path': str(source)}, reference={'path': str(reference)})
        coverage.runner.write_json(self.manifest, manifest)
        with patch.object(coverage.runner.subprocess, 'run', side_effect=self.camera):
            attempt, _ = coverage.runner.run_manifest(self.manifest, self.root / 'source-capture')
        self.request['results'] = attempt / 'results.json'
        review = coverage.runner.template(self.request['results'])
        review.update(inspector='reviewer', inspected_at=coverage.runner.now())
        review['rows'][0].update(inspected=True, outcome='accepted', notes='Opened candidate, reference and diff')
        coverage.runner.write_json(self.inspection, review)
        self.ledger_data['manifest'] = coverage.runner.identity(self.manifest); self.save_ledger()
        report = coverage.check_coverage(self.request)
        self.assertEqual(report['coverage'], 'BLOCKED')
        self.assertEqual(report['rows'][0]['source_fidelity'], 'NOT VERIFIED')

    def test_empty_skipped_or_unrelated_tests_never_supply_behavior_pass(self):
        for events in ([], [{'type': 'done', 'success': True}],
                       [{'type': 'testStart', 'test': {'id': 1, 'name': 'validation displays error'}},
                        {'type': 'testDone', 'testID': 1, 'result': 'success', 'skipped': True},
                        {'type': 'done', 'success': True}]):
            with self.subTest(events=events):
                with patch.object(handoff.subprocess, 'run', return_value=subprocess.CompletedProcess(
                        ['flutter'], 0, '\n'.join(json.dumps(e) for e in events), '')):
                    folder = self.root / ('empty-' + str(len(events)))
                    handoff.run_tests(self.project, Path('/trusted/flutter'), ['test/behavior_test.dart'], folder)
                request = dict(self.request, behavior=folder / 'tests.json')
                self.assertEqual(coverage.check_coverage(request)['coverage'], 'BLOCKED')

    def test_baseline_profile_and_prior_review_preserved_and_failed_check_rolls_back(self):
        baseline = self.project / 'test/goldens/error.png'; baseline.parent.mkdir()
        Image.new('RGB', (32, 24), 'red').save(baseline)
        profile = Path(str(baseline) + '.profile.json'); profile.write_text('old profile')
        review = Path(str(baseline) + '.approval.json'); review.write_text('old review')
        old = {p: p.read_bytes() for p in (baseline, profile, review)}
        with patch.object(handoff.subprocess, 'run', return_value=subprocess.CompletedProcess(
                ['flutter'], 1, '{"type":"done","success":false}', 'real golden mismatch')):
            report = handoff.promote(self.request, Path('/trusted/flutter'), self.root / 'failed')
        self.assertEqual(report['baseline_approval'], 'ROLLED_BACK')
        self.assertEqual(report['normal_regression'], 'FAIL')
        self.assertEqual({p: p.read_bytes() for p in old}, old)
        transaction = json.loads((self.root / 'failed/transaction.json').read_text())
        self.assertEqual(len(transaction['targets']), 3)
        self.assertTrue(all(Path(t['previous']['path']).read_bytes() == old[Path(t['path'])]
                            for t in transaction['targets']))
        self.assertIn('real golden mismatch', (self.root / 'failed/check-001/stderr.log').read_text())

    def test_interrupted_promotion_resumes_and_external_changes_block_rollback(self):
        out = self.root / 'interrupted'
        with patch.object(handoff.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                handoff.promote(self.request, Path('/trusted/flutter'), out)
        self.assertTrue((out / 'transaction.json').exists())
        with patch.object(handoff.subprocess, 'run', side_effect=self.successful_tests):
            report = handoff.resume(out, Path('/trusted/flutter'))
        self.assertEqual(report['baseline_approval'], 'APPROVED')
        baseline = self.project / 'test/goldens/error.png'
        baseline.write_bytes(b'external edit')
        with self.assertRaises(ValueError):
            handoff.rollback(out)
        self.assertEqual(baseline.read_bytes(), b'external edit')

    def test_fresh_inspected_source_pass_is_eligible_until_a_bound_input_changes(self):
        manifest = coverage.runner.read_json(self.manifest)
        source = self.root / 'source.html'; source.write_text('<input>')
        reference = self.root / 'reference.png'; Image.new('RGB', (32, 24), 'navy').save(reference)
        inputs = self.root / 'inputs.json'
        inputs.write_text('{"complete":true,"files":[],"external_resources":[]}')
        facts = self.root / 'facts.json'; facts.write_text('{"fixture":"visited error input"}')
        cache = self.root / 'cache.json'
        cache_script = coverage.RUNNER_PATH.parent / 'design_cache.py'
        argv = [sys.executable, str(cache_script), 'record', '--source', str(source),
                '--profile', str(self.profile), '--inputs-manifest', str(inputs),
                '--facts', str(facts), '--cache', str(cache)]
        recorded = self.real_run(argv, capture_output=True, text=True, check=True)
        metadata = self.root / 'capture.json'
        coverage.runner.write_json(metadata, {
            'fingerprint': json.loads(recorded.stdout)['fingerprint'], 'tool': 'test-camera',
            'captured_at': coverage.runner.now(), 'reference_sha256': coverage.runner.sha256(reference)})
        self.real_run(argv + ['--reference', str(reference), '--reference-status', 'fresh',
                             '--capture-metadata', str(metadata)], capture_output=True, text=True, check=True)
        manifest['rows'][0].update(kind='source', reference={'path': str(reference)},
                                  source={'path': str(source), 'cache': str(cache), 'inputs_manifest': str(inputs)})
        coverage.runner.write_json(self.manifest, manifest)
        with patch.object(coverage.runner.subprocess, 'run', side_effect=self.camera):
            attempt, _ = coverage.runner.run_manifest(self.manifest, self.root / 'fresh-source')
        self.request['results'] = attempt / 'results.json'
        review = coverage.runner.template(self.request['results'])
        review.update(inspector='fixture inspector', inspected_at=coverage.runner.now())
        review['rows'][0].update(inspected=True, outcome='accepted', notes='Fixture PNG, reference and diff read')
        coverage.runner.write_json(self.inspection, review)
        self.ledger_data['manifest'] = coverage.runner.identity(self.manifest); self.save_ledger()
        report = coverage.check_coverage(self.request)
        self.assertEqual(report['coverage'], 'COMPLETE')
        self.assertEqual(report['rows'][0]['source_fidelity'], 'VERIFIED')
        facts.write_text('{"fixture":"changed after inspection"}')
        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')

    def test_nonvisual_state_requires_its_named_behavior_check(self):
        self.ledger_data['states'].append({
            'id': 'owner-closed', 'evidence': self.ledger_data['states'][0]['evidence'],
            'required_rows': [], 'required_behavior_tests': ['owner close emits nothing'],
            'behavior_only_reason': 'No surviving visual screen after owner close'})
        self.save_ledger()
        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')
        self.ledger_data['states'][-1]['required_behavior_tests'] = ['validation displays error']
        self.save_ledger()
        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'COMPLETE')

    def test_changed_or_missing_inputs_block_resume_but_do_not_prevent_rollback(self):
        out = self.root / 'stale-resume'
        with patch.object(handoff.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                handoff.promote(self.request, Path('/trusted/flutter'), out)
        self.results.unlink()
        with self.assertRaises(ValueError):
            handoff.resume(out, Path('/trusted/flutter'))
        transaction = handoff.rollback(out)
        self.assertEqual(transaction['phase'], 'ROLLED_BACK')
        self.assertFalse((self.project / 'test/goldens/error.png').exists())
        self.assertTrue((out / 'evidence/results.json').is_file())

    def test_unrelated_successful_normal_suite_rolls_back_instead_of_approving(self):
        out = self.root / 'unrelated'
        events = [{'type': 'testStart', 'test': {'id': 1, 'name': 'unrelated test'}},
                  {'type': 'testDone', 'testID': 1, 'result': 'success', 'skipped': False},
                  {'type': 'done', 'success': True}]
        with patch.object(handoff.subprocess, 'run', return_value=subprocess.CompletedProcess(
                ['flutter'], 0, '\n'.join(json.dumps(e) for e in events), '')):
            report = handoff.promote(self.request, Path('/trusted/flutter'), out)
        self.assertEqual(report['normal_regression'], 'FAIL')
        self.assertEqual(report['baseline_approval'], 'ROLLED_BACK')
        self.assertFalse((self.project / 'test/goldens/error.png').exists())

    def test_tampered_staged_image_cannot_replace_inspected_candidate(self):
        out = self.root / 'tampered'
        with patch.object(handoff.subprocess, 'run', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                handoff.promote(self.request, Path('/trusted/flutter'), out)
        journal_path = out / 'transaction.json'
        journal = coverage.runner.read_json(journal_path)
        staged = Path(journal['targets'][0]['staged']['path'])
        Image.new('RGB', (32, 24), 'lime').save(staged)
        journal['targets'][0]['staged'] = coverage.runner.identity(staged)
        coverage.runner.write_json(journal_path, journal)
        baseline = self.project / 'test/goldens/error.png'
        original = baseline.read_bytes()
        with self.assertRaises(ValueError):
            handoff.resume(out, Path('/trusted/flutter'))
        self.assertEqual(baseline.read_bytes(), original)

    def test_baseline_escape_duplicate_paths_or_untrusted_test_argv_are_rejected(self):
        for path in ('../escape.png', '/tmp/escape.png', 'test/camera_test.dart'):
            with self.subTest(path=path):
                self.ledger_data['rows'][0]['baseline'] = path; self.save_ledger()
                self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')
        self.ledger_data['rows'][0]['baseline'] = 'test/goldens/error.png'
        self.ledger_data['regression_tests'] = ['--update-goldens']; self.save_ledger()
        self.assertEqual(coverage.check_coverage(self.request)['coverage'], 'BLOCKED')


if __name__ == '__main__':
    unittest.main()
