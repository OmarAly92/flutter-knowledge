import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'plugins/flutter-knowledge/skills/flutter-init/scripts'
sys.path.insert(0, str(SCRIPTS))
import init_config


TEMPLATE = "import 'package:flutter/material.dart';\n{{#withEmptyMain}}\nvoid main() { runApp(const MainApp()); }\n{{/withEmptyMain}}\n{{^withEmptyMain}}\nvoid main() { runApp(const MyApp()); }\n{{/withEmptyMain}}\n"


class EmptyProjectBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'app'
        self.project.mkdir()
        self.pubspec = self.project / 'pubspec.yaml'
        self.pubspec.write_text('name: sample\nenvironment:\n  sdk: ">=3.5.0 <4.0.0"\n'
                               'dependencies:\n  flutter:\n    sdk: flutter\n'
                               '  cupertino_icons: ^1.0.8\ndev_dependencies:\n'
                               '  flutter_test:\n    sdk: flutter\n  flutter_lints: ^5.0.0\n'
                               'flutter:\n  uses-material-design: true\n')
        self.flutter = Path(self.temp.name) / 'sdk/bin/flutter'
        template = self.flutter.parent.parent / 'packages/flutter_tools/templates/app/lib/main.dart.tmpl'
        template.parent.mkdir(parents=True)
        template.write_text(TEMPLATE)
        self.commands = []

    def source(self, text):
        path = self.project / 'lib/main.dart'
        path.parent.mkdir(exist_ok=True)
        path.write_text(text)

    def pub_add(self, command, **kwargs):
        self.commands.append(command)
        pubspec = yaml.safe_load(self.pubspec.read_text())
        for argument in command[3:]:
            if argument.startswith('--'):
                continue
            section = 'dev_dependencies' if argument.startswith('dev:') else 'dependencies'
            name = argument.removeprefix('dev:').split('@', 1)[0]
            pubspec.setdefault(section, {})[name] = '^1.0.0'
        self.pubspec.write_text(yaml.safe_dump(pubspec, sort_keys=False))
        (self.project / 'pubspec.lock').write_text('packages: {}\n')
        return subprocess.CompletedProcess(command, 0, stdout='Resolved packages\n', stderr='')

    def initialize(self, process=None, check=False):
        with patch('shutil.which', return_value=str(self.flutter)), \
                patch('subprocess.run', side_effect=process or self.pub_add), \
                contextlib.redirect_stdout(io.StringIO()):
            return init_config.run(self.project, check, bootstrap_empty=True)

    def test_empty_starter_adds_selected_dependencies_and_refreshes_config_idempotently(self):
        self.source("import 'package:flutter/material.dart';\nvoid main() {runApp(const MainApp());}\n")
        source = (self.project / 'lib/main.dart').read_bytes()
        self.assertEqual(self.initialize(), 0)
        pubspec = yaml.safe_load(self.pubspec.read_text())
        self.assertIn('flutter_bloc', pubspec['dependencies'])
        self.assertIn('flutter_secure_storage', pubspec['dependencies'])
        self.assertIn('mocktail', pubspec['dev_dependencies'])
        self.assertIn('bloc_test', pubspec['dev_dependencies'])
        self.assertNotIn('navigator', pubspec['dependencies'])
        self.assertNotIn('manual', pubspec['dependencies'])
        self.assertNotIn('build_runner', pubspec['dev_dependencies'])
        self.assertEqual(pubspec['dependencies']['cupertino_icons'], '^1.0.8')
        self.assertEqual(pubspec['dev_dependencies']['flutter_test'], {'sdk': 'flutter'})
        config_path = self.project / 'flutter-knowledge.yaml'
        config = yaml.safe_load(config_path.read_text())
        self.assertEqual(config['resolution']['secure_storage']['source'], 'pubspec')
        self.assertEqual(config['resolution']['mocking']['section'], 'dev_dependencies')
        before = (self.pubspec.read_bytes(), config_path.read_bytes())
        self.assertEqual(self.initialize(), 0)
        self.assertEqual(before, (self.pubspec.read_bytes(), config_path.read_bytes()))
        self.assertEqual(source, (self.project / 'lib/main.dart').read_bytes())

    def test_customized_or_non_starter_projects_keep_pubspec_unchanged(self):
        original = self.pubspec.read_text()
        for scenario in ('custom_main', 'extra_file', 'custom_dependency', 'workspace', 'assets', 'overrides'):
            with self.subTest(scenario=scenario):
                self.pubspec.write_text(original)
                self.source("import 'package:flutter/material.dart';\nvoid main() { runApp(const MyApp()); }\n")
                extra = self.project / 'lib/feature.dart'
                extra.unlink(missing_ok=True)
                overrides = self.project / 'pubspec_overrides.yaml'
                overrides.unlink(missing_ok=True)
                if scenario == 'custom_main':
                    self.source('void main() { runApp(const LoginScreen()); }')
                elif scenario == 'extra_file':
                    extra.write_text('class Feature {}')
                else:
                    pubspec = yaml.safe_load(original)
                    if scenario == 'custom_dependency':
                        pubspec['dependencies']['http'] = '^1.2.0'
                    elif scenario == 'workspace':
                        pubspec['resolution'] = 'workspace'
                    elif scenario == 'assets':
                        pubspec['flutter']['assets'] = ['assets/design/']
                    elif scenario == 'overrides':
                        overrides.write_text('dependency_overrides: {}\n')
                    self.pubspec.write_text(yaml.safe_dump(pubspec))
                before = self.pubspec.read_bytes()
                self.assertEqual(self.initialize(), 0)
                self.assertEqual(self.pubspec.read_bytes(), before)
                self.assertFalse(self.commands)

    def test_explicit_alternative_and_none_selections_are_honored(self):
        (self.project / 'flutter-knowledge.yaml').write_text(
            'schema_version: 1\npackages:\n  state_management: flutter_riverpod\n'
            '  local_database: none\n  secure_storage: none\n')
        self.assertEqual(self.initialize(), 0)
        pubspec = yaml.safe_load(self.pubspec.read_text())
        self.assertIn('flutter_riverpod', pubspec['dependencies'])
        for excluded in ('flutter_bloc', 'drift', 'flutter_secure_storage'):
            self.assertNotIn(excluded, pubspec['dependencies'])
        self.assertNotIn('bloc_test', pubspec['dev_dependencies'])

    def test_blank_entrypoint_is_treated_as_empty_without_rewriting_it(self):
        self.source(' \n\t')
        self.assertEqual(self.initialize(), 0)
        pubspec = yaml.safe_load(self.pubspec.read_text())
        self.assertIn('flutter_bloc', pubspec['dependencies'])
        self.assertEqual((self.project / 'lib/main.dart').read_text(), ' \n\t')

    def test_failed_package_resolution_restores_pubspec_and_lockfile(self):
        lock = self.project / 'pubspec.lock'
        original = self.pubspec.read_bytes()
        for failure in ('exit', 'timeout'):
            with self.subTest(failure=failure):
                lock.write_text('original lock\n')
                def fail(command, **kwargs):
                    self.pubspec.write_text('corrupted: true\n')
                    lock.write_text('changed lock\n')
                    if failure == 'timeout':
                        raise subprocess.TimeoutExpired(command, 180)
                    return subprocess.CompletedProcess(command, 1, stdout='', stderr='Solver failed')
                with self.assertRaisesRegex(ValueError, 'package|Package|Flutter'):
                    self.initialize(process=fail)
                self.assertEqual(self.pubspec.read_bytes(), original)
                self.assertEqual(lock.read_text(), 'original lock\n')
                self.assertTrue((self.project / 'flutter-knowledge.yaml').is_file())

    def test_unavailable_flutter_reports_incomplete_setup_but_retains_config(self):
        original = self.pubspec.read_bytes()
        for starter_source in (False, True):
            with self.subTest(starter_source=starter_source):
                if starter_source:
                    self.source("import 'package:flutter/material.dart'; void main() { runApp(const MainApp()); }")
                with patch('shutil.which', return_value=None), \
                        patch('subprocess.run', side_effect=AssertionError('No Flutter process expected')), \
                        contextlib.redirect_stdout(io.StringIO()):
                    with self.assertRaisesRegex(ValueError, 'Flutter is required'):
                        init_config.run(self.project, False, bootstrap_empty=True)
                self.assertEqual(self.pubspec.read_bytes(), original)
                self.assertTrue((self.project / 'flutter-knowledge.yaml').is_file())

    def test_linked_pubspec_is_not_modified_outside_project(self):
        external = self.project.parent / 'external-pubspec.yaml'
        self.pubspec.rename(external)
        self.pubspec.symlink_to(external)
        original = external.read_bytes()
        with self.assertRaisesRegex(ValueError, 'symlinks'):
            self.initialize()
        self.assertEqual(external.read_bytes(), original)
        self.assertFalse(self.commands)

    def test_check_combination_never_writes_or_runs_package_commands(self):
        config = self.project / 'flutter-knowledge.yaml'
        config.write_text('schema_version: 1\npackages: {}\n')
        before = (self.pubspec.read_bytes(), config.read_bytes())
        with self.assertRaisesRegex(ValueError, 'check'):
            self.initialize(check=True)
        self.assertEqual(before, (self.pubspec.read_bytes(), config.read_bytes()))
        self.assertFalse(self.commands)


if __name__ == '__main__':
    unittest.main()
