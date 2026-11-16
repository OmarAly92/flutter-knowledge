import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/flutter-knowledge'
SCRIPT = PLUGIN / 'hooks/dart-stop-check.mjs'
NODE = shutil.which('node')
GIT = shutil.which('git')

FAKE_DART = '''#!/usr/bin/env python3
import json, os, sys
with open(os.environ['FK_DART_LOG'], 'a') as log:
    log.write(json.dumps(sys.argv[1:]) + '\\n')
if sys.argv[1:2] == ['analyze']:
    sys.stdout.write(os.environ.get('FK_ANALYZE', ''))
    sys.exit(int(os.environ.get('FK_ANALYZE_EXIT', '0')))
'''


@unittest.skipUnless(NODE and GIT, 'node and git are required to execute the Stop hook')
class StopHookTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='stop-hook-')
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.project = base / 'app'
        self.write('pubspec.yaml', 'name: app\n')
        self.write('.dart_tool/package_config.json', '{}')
        self.write('lib/main.dart', 'void main() {}\n')
        self.git('init', '-q')
        self.git('add', 'pubspec.yaml', 'lib/main.dart')
        self.git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-qm', 'base')
        tools = base / 'bin'
        tools.mkdir()
        dart = tools / 'dart'
        dart.write_text(FAKE_DART)
        dart.chmod(0o755)
        self.log = base / 'dart.log'
        self.env = {**os.environ, 'PATH': str(tools) + os.pathsep + os.environ['PATH'], 'FK_DART_LOG': str(self.log)}
        self.env.pop('FLUTTER_KNOWLEDGE_STOP_HOOK', None)

    def write(self, relative, text):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.project), *args], check=True, capture_output=True)

    def run_hook(self, payload=None, env=None):
        payload = {'cwd': str(self.project / 'lib'), 'stop_hook_active': False} if payload is None else payload
        result = subprocess.run([NODE, str(SCRIPT)], input=json.dumps(payload), text=True, capture_output=True,
                                env={**self.env, **(env or {})}, cwd=self.temp.name, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []
        return (json.loads(result.stdout) if result.stdout.strip() else None), calls

    def change_files(self):
        self.write('lib/main.dart', 'void main() { }\n')
        self.write('lib/feature/home/home_screen.dart', 'class HomeScreen {}\n')
        self.write('test/home_test.dart', 'void main() {}\n')
        self.write('lib/feature/home/home_model.g.dart', '// generated\n')
        self.write('README.md', 'notes\n')
        self.write('lib/feature/home/home_screen.dart', 'class HomeScreen {}\n')

    def issue(self, severity, relative, message):
        return f'{severity}|TYPE|CODE|{self.project / relative}|3|5|1|{message}\n'

    def test_formats_and_analyzes_only_changed_authored_dart_files(self):
        self.change_files()
        output, calls = self.run_hook()
        self.assertIsNone(output)
        expected = ['lib/feature/home/home_screen.dart', 'lib/main.dart', 'test/home_test.dart']
        self.assertEqual(calls, [['format', *expected], ['analyze', '--format=machine', *expected]])

    def test_errors_and_warnings_block_once_and_infos_never_block(self):
        self.change_files()
        analysis = (self.issue('ERROR', 'lib/main.dart', "Undefined name 'missing'.")
                    + self.issue('WARNING', 'test/home_test.dart', 'Unused local variable.')
                    + self.issue('INFO', 'lib/main.dart', "'package:flutter/material.dart' is deprecated."))
        output, _ = self.run_hook(env={'FK_ANALYZE': analysis, 'FK_ANALYZE_EXIT': '3'})
        self.assertEqual(output['decision'], 'block')
        self.assertIn("lib/main.dart:3:5 error: Undefined name 'missing'.", output['reason'])
        self.assertIn('test/home_test.dart:3:5 warning: Unused local variable.', output['reason'])
        self.assertNotIn('deprecated', output['reason'])
        again, calls = self.run_hook({'cwd': str(self.project), 'stop_hook_active': True},
                                     env={'FK_ANALYZE': analysis, 'FK_ANALYZE_EXIT': '3'})
        self.assertIsNone(again)
        self.assertEqual(calls[-1][0], 'format')
        output, _ = self.run_hook(env={'FK_ANALYZE': self.issue('INFO', 'lib/main.dart', 'Prefer const.')})
        self.assertIsNone(output)

    def test_silent_without_flutter_project_git_changes_dependencies_or_when_disabled(self):
        plain = Path(self.temp.name) / 'plain'
        plain.mkdir()
        self.assertEqual(self.run_hook({'cwd': str(plain)}), (None, []))
        self.assertEqual(self.run_hook(), (None, []))
        self.change_files()
        self.assertEqual(self.run_hook(env={'FLUTTER_KNOWLEDGE_STOP_HOOK': '0'}), (None, []))
        (self.project / '.dart_tool/package_config.json').unlink()
        output, calls = self.run_hook()
        self.assertIsNone(output)
        self.assertEqual([call[0] for call in calls], ['format'])
        shutil.rmtree(self.project / '.git')
        self.log.unlink()
        self.assertEqual(self.run_hook(), (None, []))

    def test_missing_dart_or_malformed_input_never_fails_the_turn(self):
        self.change_files()
        output, calls = self.run_hook(env={'PATH': os.path.dirname(NODE)})
        self.assertIsNone(output)
        result = subprocess.run([NODE, str(SCRIPT)], input='{broken', text=True, capture_output=True,
                                env=self.env, cwd=self.project, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_claude_code_and_codex_register_the_same_stop_hook(self):
        hooks = {
            'Claude Code': json.loads((PLUGIN / 'hooks/hooks.json').read_text())['hooks'],
            'Codex': json.loads((PLUGIN / '.codex-plugin/plugin.json').read_text())['hooks'],
        }
        for harness, events in hooks.items():
            with self.subTest(harness=harness):
                commands = [hook['command'] for group in events['Stop'] for hook in group['hooks']]
                self.assertEqual(len(commands), 1)
                argv = shlex.split(commands[0].replace('${CLAUDE_PLUGIN_ROOT}', str(PLUGIN)).replace('${PLUGIN_ROOT}', str(PLUGIN)))
                self.assertEqual(argv[0], 'node')
                self.assertEqual(Path(argv[1]).resolve(), SCRIPT.resolve())


if __name__ == '__main__':
    unittest.main()
