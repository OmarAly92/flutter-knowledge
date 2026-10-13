import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/flutter-knowledge/skills/visual-verification/scripts'
SCRIPT = SCRIPTS / 'run_verification.py'


class VerificationRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        spec = importlib.util.spec_from_file_location('verification_runner', SCRIPT)
        self.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.runner)
        self.source = self.root / 'design.html'
        self.source.write_text('<html>Login</html>')
        self.profile = self.root / 'profile.json'
        self.profile_data = {
            'viewport': {'width': 16, 'height': 12}, 'dpr': 2,
            'screen': 'Login', 'state': 'loaded', 'selector': '.login',
            'skin': 'dark', 'locale': 'en', 'text_scale': 1,
            'capture_adapter': 'fixture-browser-v1',
            'safe_area': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
            'data': {'fixture': 'login-v1'},
            'conditions': {'fonts': 'loaded', 'shadows': True, 'motion': 'fixed frame 20',
                           'pointer': 'none', 'expected_state': 'loaded login', 'keyboard_inset': 0},
        }
        self.profile.write_text(json.dumps(self.profile_data))
        self.reference = self.root / 'reference.png'
        Image.new('RGB', (32, 24), 'black').save(self.reference)
        self.row = {
            'id': 'login', 'label': 'Login loaded', 'kind': 'source', 'profile': 'profile.json',
            'source': {'path': 'design.html'}, 'reference': {'path': 'reference.png'},
            'capture': {'command': ['flutter', 'test', 'test/login_camera_test.dart',
                                    '--dart-define=OUTPUT={actual}', '--dart-define=PROFILE={profile}']},
        }
        self.manifest = self.root / 'manifest.json'
        self.out = self.root / 'attempts'
        self.camera_color = 'black'
        self.camera_size = (32, 24)
        self.camera_exit = 0
        self.camera_write = True
        self.camera_format = 'PNG'
        self.commands = []
        self.batch_actuals = []
        real_run = subprocess.run

        def boundary(command, **kwargs):
            self.commands.append(command)
            if Path(command[0]).name == 'flutter':
                if self.batch_actuals:
                    attempt = next(arg.split('=', 2)[2] for arg in command if arg.startswith('--dart-define=CAPTURE_ROUND='))
                    for relative in self.batch_actuals:
                        target = self.root / relative.replace('{attempt}', attempt)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        if self.camera_write:
                            Image.new('RGB', self.camera_size, self.camera_color).save(target, format=self.camera_format)
                    return subprocess.CompletedProcess(command, self.camera_exit, 'batch stdout\n', 'batch stderr\n')
                target = Path(next(arg.split('=', 2)[2] for arg in command if arg.startswith('--dart-define=OUTPUT=')))
                if self.camera_write:
                    Image.new('RGB', self.camera_size, self.camera_color).save(target, format=self.camera_format)
                return subprocess.CompletedProcess(command, self.camera_exit, 'complete capture stdout\n', 'complete capture stderr\n')
            return real_run(command, **kwargs)

        self.boundary = boundary

    def run_attempt(self, rows=None):
        self.manifest.write_text(json.dumps({'schema_version': 1, 'project': '.', 'rows': rows or [self.row]}))
        with patch.object(self.runner.subprocess, 'run', side_effect=self.boundary):
            path, code = self.runner.run_manifest(self.manifest, self.out)
        return path, code, json.loads((path / 'results.json').read_text())

    def inspection(self, path, results, outcome='accepted'):
        inspection = self.root / 'inspection.json'
        inspection.write_text(json.dumps({
            'schema_version': 1, 'results_sha256': hashlib.sha256((path / 'results.json').read_bytes()).hexdigest(),
            'inspector': 'fixture inspector', 'inspected_at': '2026-10-11T12:00:00Z',
            'rows': [{'id': row['id'], 'artifact_hashes': self.runner.artifact_hashes(row),
                      'inspected': True, 'outcome': outcome, 'notes': 'Read full-resolution PNGs and state.'}
                     for row in results['rows']],
        }))
        return inspection

    def fresh_cache(self, files=None, facts_payload=None):
        inputs = self.root / 'inputs.json'
        inputs.write_text(json.dumps({'complete': True, 'files': files or [], 'external_resources': []}))
        facts = self.root / 'facts.json'
        facts.write_text(facts_payload or '{"w":16,"h":12,"visible":true}')
        cache = self.root / 'cache.json'
        args = [sys.executable, str(SCRIPTS / 'design_cache.py'), 'record', '--source', str(self.source),
                '--profile', str(self.profile), '--inputs-manifest', str(inputs), '--facts', str(facts), '--cache', str(cache)]
        initial = subprocess.run(args, capture_output=True, text=True, check=True)
        metadata = self.root / 'capture.json'
        metadata.write_text(json.dumps({'fingerprint': json.loads(initial.stdout)['fingerprint'],
                                       'tool': self.profile_data['capture_adapter'],
                                       'captured_at': '2026-10-11T10:00:00Z',
                                       'reference_sha256': hashlib.sha256(self.reference.read_bytes()).hexdigest()}))
        subprocess.run(args + ['--reference', str(self.reference), '--reference-status', 'fresh',
                               '--capture-metadata', str(metadata)], capture_output=True, text=True, check=True)
        self.row['source'].update({'inputs_manifest': 'inputs.json', 'cache': 'cache.json'})

    def test_reruns_preserve_attempts_logs_and_candidate_paths(self):
        first, code, results = self.run_attempt()
        before = {str(file.relative_to(first)): file.read_bytes() for file in first.rglob('*') if file.is_file()}
        second, _, newer = self.run_attempt()
        self.assertNotEqual(first, second)
        self.assertEqual(before, {str(file.relative_to(first)): file.read_bytes() for file in first.rglob('*') if file.is_file()})
        self.assertEqual(code, 0)
        row = results['rows'][0]
        self.assertEqual(row['comparison']['status'], 'PASS')
        self.assertTrue(row['inspection_required'])
        self.assertIn('NOT VERIFIED', (first / 'verification.md').read_text())
        self.assertNotEqual(row['artifacts']['actual']['path'], newer['rows'][0]['artifacts']['actual']['path'])
        self.assertIn('complete capture stderr', Path(row['artifacts']['capture_stderr']['path']).read_text())
        self.assertIn('--no-pub', self.commands[0])
        self.assertIn('--update-goldens', self.commands[0])
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), row['inputs']['source']['sha256'])

    def test_batch_capture_runs_once_with_unique_project_candidates(self):
        rows = []
        for name in ('login', 'setup'):
            row = copy.deepcopy(self.row)
            row.update({'id': name, 'label': name, 'actual': 'test/goldens/{attempt}/' + name + '.png'})
            row.pop('capture')
            rows.append(row)
        self.batch_actuals = [row['actual'] for row in rows]
        self.manifest.write_text(json.dumps({'schema_version': 1, 'rows': rows,
                                           'capture': {'command': ['flutter', 'test', 'test/camera.dart',
                                                                   '--dart-define=CAPTURE_ROUND={attempt}']}}))
        with patch.object(self.runner.subprocess, 'run', side_effect=self.boundary):
            first, code = self.runner.run_manifest(self.manifest, self.out, project=self.root)
            second, _ = self.runner.run_manifest(self.manifest, self.out, project=self.root)
        self.assertEqual(code, 0)
        self.assertEqual(len([command for command in self.commands if command[0] == 'flutter']), 2)
        first_rows = json.loads((first / 'results.json').read_text())['rows']
        second_rows = json.loads((second / 'results.json').read_text())['rows']
        self.assertNotEqual(first_rows[0]['inputs']['candidate']['path'], second_rows[0]['inputs']['candidate']['path'])
        self.assertTrue(all(row['comparison']['status'] == 'PASS' for row in first_rows))

    def test_batch_paths_must_be_unique_candidates_inside_project(self):
        for actual in ('test/goldens/baseline.png', '../{attempt}/escape.png'):
            with self.subTest(actual=actual):
                row = copy.deepcopy(self.row)
                row.pop('capture')
                row['actual'] = actual
                self.manifest.write_text(json.dumps({'schema_version': 1, 'project': '.', 'rows': [row],
                                                   'capture': {'command': ['flutter', 'test', '--dart-define=CAPTURE_ROUND={attempt}']}}))
                with self.assertRaises(ValueError):
                    self.runner.run_manifest(self.manifest, self.out)
        self.assertEqual(self.commands, [])

    def test_failed_camera_never_compares_partial_or_previous_capture(self):
        first, _, _ = self.run_attempt()
        self.camera_exit = 1
        for write in (False, True):
            with self.subTest(partial_output=write):
                self.camera_write = write
                self.commands.clear()
                failed, code, results = self.run_attempt()
                row = results['rows'][0]
                self.assertEqual(code, 2)
                self.assertEqual(row['capture']['exit_code'], 1)
                self.assertEqual(row['comparison']['status'], 'ERROR')
                self.assertNotIn('overall_percent', row['comparison'])
                self.assertEqual(len(self.commands), 1)
                self.assertNotEqual(first, failed)
                self.assertEqual('uncompared_actual' in row['artifacts'], write)
                self.assertNotIn('actual', row['artifacts'])

    def test_invalid_profiles_and_unsafe_camera_are_rejected_before_launch(self):
        profiles = [dict(self.profile_data, dpr=0), dict(self.profile_data, text_scale=True),
                    dict(self.profile_data, capture_adapter='unknown'), dict(self.profile_data, conditions={})]
        commands = [['sh', '-c', 'flutter test'], ['flutter', 'test', 'camera.dart'],
                    ['flutter', 'run', '{actual}', '{profile}']]
        for profile in profiles:
            with self.subTest(profile=profile):
                self.profile.write_text(json.dumps(profile))
                with self.assertRaises(ValueError):
                    self.run_attempt()
        self.profile.write_text(json.dumps(self.profile_data))
        for command in commands:
            with self.subTest(command=command):
                self.row['capture']['command'] = command
                with self.assertRaises(ValueError):
                    self.run_attempt()
        self.assertEqual(self.commands, [])

    def test_compare_pass_diff_and_errors_preserve_default_scoring(self):
        for color, size, expected_code, status in [('black', (32, 24), 0, 'PASS'),
                                                  ('white', (32, 24), 1, 'DIFF'),
                                                  ('black', (31, 24), 2, 'ERROR')]:
            with self.subTest(color=color, size=size):
                self.camera_color, self.camera_size = color, size
                path, code, results = self.run_attempt()
                row = results['rows'][0]
                self.assertEqual(code, expected_code)
                self.assertEqual(row['comparison']['status'], status)
                if status == 'ERROR':
                    self.assertNotIn('overall_percent', row['comparison'])
                    self.assertNotIn('%', (path / 'verification.md').read_text())
                else:
                    settings = row['comparison']['settings']
                    self.assertEqual(settings, {'threshold': .02, 'max_cluster': .25, 'tolerance': 12,
                                                'shift': 2, 'ignored_regions': [], 'allow_resize': False})
                    direct = subprocess.run([sys.executable, str(SCRIPTS / 'compare.py'), '--actual', row['artifacts']['actual']['path'],
                                             '--expected', str(self.reference), '--json'], capture_output=True, text=True)
                    self.assertEqual(direct.returncode, row['compare']['exit_code'])
                    self.assertEqual(json.loads(direct.stdout)['overall_percent'], row['comparison']['overall_percent'])

    def test_missing_and_regression_references_do_not_invent_design_fidelity(self):
        for baseline in (False, True):
            row = copy.deepcopy(self.row)
            row.update({'kind': 'regression'})
            row.pop('source')
            if not baseline:
                row.pop('reference')
            path, code, results = self.run_attempt([row])
            result = results['rows'][0]
            self.assertEqual(code, 0)
            self.assertIn('NOT VERIFIED', (path / 'verification.md').read_text())
            if not baseline:
                self.assertEqual(result['comparison']['status'], 'NOT_RUN')
                self.assertNotIn('overall_percent', result['comparison'])
            inspection = self.inspection(path, results)
            reviewed = self.root / ('reviewed-' + str(baseline))
            self.runner.finalize(path / 'results.json', inspection, reviewed)
            self.assertNotIn('| VERIFIED', (reviewed / 'verification.md').read_text())

    def test_fresh_source_pass_requires_inspection_and_keeps_raw_results(self):
        self.fresh_cache()
        path, _, results = self.run_attempt()
        original = (path / 'results.json').read_bytes()
        self.assertTrue(results['rows'][0]['provenance']['reference_reusable'])
        inspection = self.inspection(path, results)
        reviewed = self.root / 'reviewed'
        self.runner.finalize(path / 'results.json', inspection, reviewed)
        self.assertIn('| VERIFIED', (reviewed / 'verification.md').read_text())
        self.assertEqual(original, (path / 'results.json').read_bytes())
        self.assertTrue((reviewed / 'reviewed_results.json').is_file())

    def test_changed_artifact_or_source_refuses_inspection(self):
        for role in ('actual', 'reference', 'source', 'results'):
            with self.subTest(role=role):
                path, _, results = self.run_attempt()
                inspection = self.inspection(path, results)
                row = results['rows'][0]
                target = path / 'results.json' if role == 'results' else (
                    self.source if role == 'source' else Path(row['artifacts'][role]['path']))
                target.write_bytes(target.read_bytes() + b'changed')
                output = self.root / ('reviewed-' + role)
                with self.assertRaises(ValueError):
                    self.runner.finalize(path / 'results.json', inspection, output)
                self.assertFalse(output.exists())

    def test_cache_miss_after_asset_change_cannot_be_inspected_as_verified(self):
        self.fresh_cache()
        self.source.write_text('<html>changed source</html>')
        path, code, results = self.run_attempt()
        self.assertEqual(code, 0)
        self.assertFalse(results['rows'][0]['provenance']['reference_reusable'])
        inspection = self.inspection(path, results)
        reviewed = self.root / 'reviewed'
        self.runner.finalize(path / 'results.json', inspection, reviewed)
        self.assertNotIn('| VERIFIED', (reviewed / 'verification.md').read_text())

    def test_comparator_failure_retains_complete_stdout_and_stderr(self):
        self.reference.write_bytes(b'unreadable reference')
        path, code, results = self.run_attempt()
        row = results['rows'][0]
        self.assertEqual(code, 2)
        self.assertEqual(row['compare']['exit_code'], 2)
        stdout = Path(row['artifacts']['compare_stdout']['path']).read_text()
        self.assertIn('could not be read', stdout)
        self.assertTrue(Path(row['artifacts']['compare_stderr']['path']).is_file())
        self.assertNotIn('%', (path / 'verification.md').read_text())

    def test_source_bundle_changes_refuse_previously_accepted_inspection(self):
        asset = self.root / 'assets' / 'font.ttf'
        asset.parent.mkdir()
        asset.write_bytes(b'original font')
        self.fresh_cache(['assets'])
        for name in ('assets/font.ttf', 'inputs.json', 'cache.json', 'facts.json', 'capture.json', 'assets/new.ttf'):
            with self.subTest(changed=name):
                path, _, results = self.run_attempt()
                inspection = self.inspection(path, results)
                target = self.root / name
                previous = target.read_bytes() if target.exists() else None
                target.write_bytes((previous or b'') + b'changed')
                output = self.root / ('reviewed-' + name.replace('/', '-'))
                with self.assertRaises(ValueError):
                    self.runner.finalize(path / 'results.json', inspection, output)
                self.assertFalse(output.exists())
                if previous is None:
                    target.unlink()
                else:
                    target.write_bytes(previous)

    def test_batch_candidate_aliases_are_rejected_before_launch(self):
        rows = []
        for name, actual in [('login', 'test/goldens/{attempt}/login.png'),
                             ('alias', 'test/goldens/{attempt}/nested/../login.png')]:
            row = copy.deepcopy(self.row)
            row.update({'id': name, 'actual': actual})
            row.pop('capture')
            rows.append(row)
        self.batch_actuals = [row['actual'] for row in rows]
        self.manifest.write_text(json.dumps({'schema_version': 1, 'rows': rows,
            'capture': {'command': ['flutter', 'test', '--dart-define=CAPTURE_ROUND={attempt}']}}))
        with patch.object(self.runner.subprocess, 'run', side_effect=self.boundary):
            with self.assertRaises(ValueError):
                self.runner.run_manifest(self.manifest, self.out)
        self.assertEqual(self.commands, [])

    def test_manifest_and_row_capture_commands_cannot_silently_override_each_other(self):
        self.manifest.write_text(json.dumps({'schema_version': 1, 'rows': [self.row],
            'capture': {'command': ['flutter', 'test', '--dart-define=CAPTURE_ROUND={attempt}']}}))
        self.batch_actuals = ['test/goldens/{attempt}/login.png']
        with patch.object(self.runner.subprocess, 'run', side_effect=self.boundary):
            with self.assertRaises(ValueError):
                self.runner.run_manifest(self.manifest, self.out)
        self.assertEqual(self.commands, [])

    def test_camera_launch_failure_retains_error_attempt(self):
        self.manifest.write_text(json.dumps({'schema_version': 1, 'rows': [self.row]}))
        with patch.object(self.runner.subprocess, 'run', side_effect=FileNotFoundError('flutter unavailable')):
            path, code = self.runner.run_manifest(self.manifest, self.out)
        results = json.loads((path / 'results.json').read_text())
        row = results['rows'][0]
        self.assertEqual(code, 2)
        self.assertIsNone(row['capture']['exit_code'])
        self.assertIn('flutter unavailable', row['comparison']['error'])
        self.assertIn('flutter unavailable', Path(row['artifacts']['capture_stderr']['path']).read_text())
        self.assertNotIn('overall_percent', row['comparison'])

    def test_profile_conditions_require_explicit_control_values(self):
        for key, invalid in [('fonts', False), ('motion', []), ('pointer', {}),
                             ('expected_state', ' '), ('shadows', 'unknown'), ('keyboard_inset', -1)]:
            with self.subTest(condition=key):
                profile = copy.deepcopy(self.profile_data)
                profile['conditions'][key] = invalid
                self.profile.write_text(json.dumps(profile))
                with self.assertRaises(ValueError):
                    self.run_attempt()
        self.assertEqual(self.commands, [])

    def test_regression_baseline_report_omits_design_percentages(self):
        row = copy.deepcopy(self.row)
        row['kind'] = 'regression'
        row.pop('source')
        path, code, results = self.run_attempt([row])
        self.assertEqual(code, 0)
        self.assertEqual(results['rows'][0]['comparison']['status'], 'PASS')
        self.assertNotIn('%', (path / 'verification.md').read_text())

    def test_capture_input_mutation_is_not_compared_as_current_source(self):
        boundary = self.boundary

        def mutating_camera(command, **kwargs):
            completed = boundary(command, **kwargs)
            if Path(command[0]).name == 'flutter':
                self.source.write_text('<html>changed during camera</html>')
            return completed

        self.manifest.write_text(json.dumps({'schema_version': 1, 'rows': [self.row]}))
        with patch.object(self.runner.subprocess, 'run', side_effect=mutating_camera):
            path, code = self.runner.run_manifest(self.manifest, self.out)
        row = json.loads((path / 'results.json').read_text())['rows'][0]
        self.assertEqual(code, 2)
        self.assertEqual(row['comparison']['status'], 'ERROR')
        self.assertIn('changed', row['comparison']['error'])

    def test_non_png_camera_output_is_an_error(self):
        self.camera_format = 'JPEG'
        path, code, results = self.run_attempt()
        row = results['rows'][0]
        self.assertEqual(code, 2)
        self.assertEqual(row['comparison']['status'], 'ERROR')
        self.assertNotIn('overall_percent', row['comparison'])
        self.assertNotIn('%', (path / 'verification.md').read_text())

    def test_inspection_refuses_missing_rows_and_uninspected_artifacts(self):
        path, _, results = self.run_attempt()
        for change in ('missing', 'uninspected', 'no_notes'):
            with self.subTest(change=change):
                inspection = self.inspection(path, results)
                content = json.loads(inspection.read_text())
                if change == 'missing':
                    content['rows'] = []
                elif change == 'uninspected':
                    content['rows'][0]['inspected'] = False
                else:
                    content['rows'][0]['notes'] = ''
                inspection.write_text(json.dumps(content))
                output = self.root / ('reviewed-' + change)
                with self.assertRaises(ValueError):
                    self.runner.finalize(path / 'results.json', inspection, output)
                self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
