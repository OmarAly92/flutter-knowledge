import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('core_references', ROOT / 'tests/check_core_references.py')
REFERENCES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REFERENCES)


class CoreReferenceFixtureTests(unittest.TestCase):
    def test_every_shipped_implementation_is_bound_to_the_executable_fixture(self):
        manifest = json.loads(REFERENCES.MANIFEST.read_text())
        sources = set()
        for group in manifest['components'].values():
            sources.update(group.get('copies', {}))
            for template in group.get('templates', []):
                sources.update(template['bindings'].values())
        shipped = set()
        for skill in ('flutter-core', 'flutter-app-theme'):
            assets = ROOT / 'plugins/flutter-knowledge/skills' / skill / 'assets/reference-implementations'
            shipped.update(str(path.relative_to(ROOT)) for path in assets.rglob('*')
                           if path.is_file() and path.name.endswith(('.dart', '.dart.inc')))
        self.assertTrue(shipped)
        self.assertEqual({source for source in sources if '/assets/reference-implementations/' in source}, shipped)

    def test_component_selection_keeps_unrelated_packages_and_sources_out(self):
        theme = REFERENCES.fixture_plan(['theme'])
        self.assertEqual(theme['packages'], {})
        self.assertEqual(set(theme['components']), {'theme'})
        logger = REFERENCES.fixture_plan(['logger'])
        self.assertEqual(set(logger['packages']), {'dio', 'talker', 'talker_dio_logger'})
        with self.assertRaises(ValueError):
            REFERENCES.fixture_plan(['unknown'])

    def test_assembly_uses_the_shipped_sources_and_resolves_all_bindings(self):
        manifest = json.loads(REFERENCES.MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            REFERENCES.assemble(project)
            inputs = json.loads((project / 'reference-inputs.json').read_text())
            for group in manifest['components'].values():
                for source, target in group.get('copies', {}).items():
                    with self.subTest(target=target):
                        self.assertEqual((project / target).read_bytes(), (ROOT / source).read_bytes())
                        self.assertIn(source, inputs)
                for template in group.get('templates', []):
                    text = (project / template['target']).read_text()
                    self.assertNotRegex(text, r'@@[A-Z_]+@@')
                    for source in template['bindings'].values():
                        self.assertIn((ROOT / source).read_text(), text)
            pubspec = json.loads((project / 'pubspec.yaml').read_text())
            self.assertEqual(set(pubspec['dependencies']) - {'flutter'}, set(manifest['tested_packages']))

    def test_fixture_refuses_existing_files_duplicate_targets_and_directory_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / 'fixture'
            project.mkdir()
            existing = project / 'existing.dart'
            existing.write_text('preserve')
            with self.assertRaises(ValueError):
                REFERENCES.assemble(project, ['theme'])
            for target in ('existing.dart', '../outside.dart'):
                with self.subTest(target=target), self.assertRaises(ValueError):
                    REFERENCES.write_fixture_file(project, target, 'changed')
            self.assertEqual(existing.read_text(), 'preserve')
            self.assertFalse((Path(folder) / 'outside.dart').exists())

    def test_reporter_failure_and_incomplete_runs_cannot_pass_on_zero_exit(self):
        success = [{'type': 'testDone', 'result': 'success', 'hidden': False, 'skipped': False},
                   {'type': 'done', 'success': True}]
        variants = [
            (success, 0, 0),
            ([{'type': 'testDone', 'result': 'failure'}, {'type': 'done', 'success': True}], 0, 1),
            ([{'type': 'error', 'error': 'failure'}, *success], 0, 1),
            ([{'type': 'done', 'success': False}], 0, 1),
            (success[:-1], 0, 2),
            ([success[-1]], 0, 2),
            ([{**success[0], 'skipped': True}, success[-1]], 0, 2),
            ([{**success[0], 'result': None}, success[-1]], 0, 2),
            ([*success, success[-1]], 0, 2),
            (success, 7, 7),
            (success, -9, 137),
        ]
        for events, exit_code, expected in variants:
            with self.subTest(events=events, exit_code=exit_code):
                stdout = '\n'.join(json.dumps(event) for event in events)
                completed = subprocess.CompletedProcess(['flutter', 'test'], exit_code, stdout, '')
                self.assertEqual(REFERENCES.test_outcome(completed), expected)

    def test_timeout_keeps_partial_report_and_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder)
            error = subprocess.TimeoutExpired(['flutter', 'test'], 300,
                                             output=b'partial reporter output', stderr=b'partial stderr')
            with patch.object(REFERENCES.subprocess, 'run', side_effect=error):
                self.assertEqual(REFERENCES.run_reference_tests(project), 2)
            self.assertEqual((project / 'reference-tests.log').read_text(),
                             'partial reporter outputpartial stderr')


if __name__ == '__main__':
    unittest.main()
