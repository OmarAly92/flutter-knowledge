import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import yaml


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/focused_checks.py'
SPEC = importlib.util.spec_from_file_location('focused_checks', SCRIPT)
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class FocusedCheckSelectionTests(unittest.TestCase):
    def test_owner_and_shared_dependencies_select_downstream_suites(self):
        cases = {
            'flutter-init/scripts/dart_source.py': CHECKS.INIT,
            'flutter-init/scripts/empty_project.py': CHECKS.INIT,
            'flutter-init/package-catalog.json': CHECKS.INIT,
            'flutter-core/scripts/inspect_core.py': {'flutter_core'},
            'flutter-review/scripts/checks.py': {'flutter_review'},
            'flutter-app-theme/scripts/token_audit.py': {'token_audit', 'flutter_review'},
            'golden-tests/scripts/state_coverage.py': {'golden_handoff'},
            'html-to-widget/scripts/layout-tree.js': {'layout_tree', 'html_to_theme', 'calibration'},
            'set-theme-from-html/scripts/audit_fonts.py': {'html_to_theme', 'calibration'},
            'visual-verification/scripts/stage_usage.py': {'stage_usage'},
            'visual-verification/scripts/compare.py': CHECKS.VISUAL | {'html_to_theme'},
            'visual-verification/scripts/design_cache.py': CHECKS.VISUAL | {'html_to_theme'},
        }
        for relative, expected in cases.items():
            with self.subTest(path=relative):
                plan = CHECKS.select([CHECKS.SKILLS + relative])
                self.assertEqual(set(plan['suites']), expected)

    def test_every_harness_entry_point_is_covered(self):
        paths = [
            '.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json',
            '.cursor-plugin/plugin.json', '.kimi-plugin/plugin.json',
            '.opencode/plugins/flutter-knowledge.js', '.pi/extensions/flutter-knowledge.ts',
            'plugins/flutter-knowledge/.claude-plugin/plugin.json',
            'plugins/flutter-knowledge/.codex-plugin/plugin.json',
            'plugins/flutter-knowledge/hooks/hooks.json',
            'plugins/flutter-knowledge/hooks/force-flutter-knowledge.mjs',
            'gemini-extension.json', 'GEMINI.md', 'install.sh', 'bump-version.sh',
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(CHECKS.select([path])['suites'], ['harness_compatibility'])
        self.assertIn('harness_compatibility', CHECKS.select(['package.json'])['suites'])

    def test_ci_dependency_and_unknown_helper_changes_fail_closed_to_all_suites(self):
        paths = [
            '.github/workflows/focused-checks.yml', 'scripts/focused_checks.py',
            'tests/test_focused_checks.py', 'requirements-ci.txt', 'package-lock.json',
            CHECKS.SKILLS + 'flutter-init/requirements.txt',
            CHECKS.SKILLS + 'new-skill/scripts/check.py',
            CHECKS.SKILLS + 'new-skill/references/unknown.py',
            CHECKS.SKILLS + 'flutter-core/references/unknown.py',
            CHECKS.SKILLS + 'flutter-init/scripts/new_helper.py',
            CHECKS.SKILLS + 'visual-verification/scripts/new_helper.py',
            'scripts/unmapped.py', 'tests/test_new_helper.py',
        ]
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(set(CHECKS.select([path])['suites']), set(CHECKS.SUITES))

    def test_discovery_and_fixture_changes_are_distinct_from_irrelevant_docs(self):
        cases = {
            CHECKS.SKILLS + 'flutter-screen-ui/SKILL.md': {'harness_compatibility', 'skill_selection'},
            'benchmark/skill_selection.py': {'skill_selection'},
            'benchmark/selection_cases.json': {'skill_selection'},
            'benchmark/grade.py': {'benchmark_grade'},
            'tests/fixtures/layout-tree/composition.html': {'layout_tree'},
            'tests/fixtures/html-to-theme/css/app.css': {'html_to_theme'},
            'tests/test_flutter_review.py': {'flutter_review'},
            'README.md': set(),
            'benchmark/README.md': set(),
            'docs/plans/ci.md': set(),
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                plan = CHECKS.select([path, path])
                self.assertEqual(set(plan['suites']), expected)
                self.assertEqual(plan['relevant'], bool(expected))
                self.assertEqual(plan['browser'], bool(expected & {'layout_tree', 'html_to_theme'}))
                self.assertEqual(plan['files'], [path])

    def test_json_dry_run_reports_selection_without_running_or_installing(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--files', 'README.md',
                                 '--dry-run', '--json'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertFalse(plan['relevant'])
        self.assertEqual(plan['commands'], [])
        self.assertIn('Live harness clients', plan['not_run'])

    def test_gemini_included_references_select_discovery_even_when_deleted(self):
        references = [path for path in CHECKS.GEMINI_REFERENCES if not path.endswith('/SKILL.md')]
        self.assertTrue(references)
        for path in references:
            with self.subTest(path=path):
                self.assertIn('harness_compatibility', CHECKS.select([path])['suites'])
        with tempfile.TemporaryDirectory() as directory, patch.object(CHECKS, 'ROOT', Path(directory)):
            path = CHECKS.SKILLS + 'flutter-knowledge/references/workflows.md'
            self.assertFalse((CHECKS.ROOT / path).exists())
            self.assertEqual(CHECKS.select([path])['suites'], ['harness_compatibility'])

    def test_changed_dart_recipes_report_required_flutter_followup(self):
        for path in [CHECKS.SKILLS + 'flutter-state-management/references/cubit.md',
                     'tests/check_state_references.py', 'tests/state_reference_test.dart']:
            with self.subTest(path=path):
                plan = CHECKS.select([path])
                self.assertEqual(len(plan['required_manual_checks']), 1)
                self.assertIn('not analyzed or exercised', plan['required_manual_checks'][0])
        self.assertEqual(CHECKS.select(['docs/plans/ci.md'])['required_manual_checks'], [])

    def test_changed_file_detection_keeps_deleted_and_shell_special_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            target = root / '.opencode/plugins/old.js'
            target.parent.mkdir(parents=True)
            target.write_text('export {};')
            subprocess.run(['git', 'add', '.'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=CI test', '-c', 'user.email=ci@example.invalid',
                            'commit', '-qm', 'fixture'], cwd=root, check=True)
            target.unlink()
            special = 'literal$(touch NOPE).py'
            (root / special).write_text('pass')
            subprocess.run(['git', 'add', '-A'], cwd=root, check=True)
            subprocess.run(['git', '-c', 'user.name=CI test', '-c', 'user.email=ci@example.invalid',
                            'commit', '-qm', 'changes'], cwd=root, check=True)
            event = root / 'event.json'
            head = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, check=True,
                                  capture_output=True, text=True).stdout.strip()
            base = subprocess.run(['git', 'rev-parse', 'HEAD~1'], cwd=root, check=True,
                                  capture_output=True, text=True).stdout.strip()
            for payload in ({'before': base, 'after': head},
                            {'pull_request': {'base': {'sha': base}, 'head': {'sha': head}}}):
                with self.subTest(payload=payload), patch.object(CHECKS, 'ROOT', root), \
                        patch.dict(os.environ, {'GITHUB_EVENT_PATH': str(event)}):
                    event.write_text(json.dumps(payload))
                    self.assertEqual(set(CHECKS.event_files()), {'.opencode/plugins/old.js', special})
            self.assertFalse((root / 'NOPE').exists())

    def test_failed_or_skipped_child_checks_cannot_succeed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            marker = root / 'should-not-run'
            plan = {'suites': ['failure', 'later'], 'browser': False,
                    'commands': [[sys.executable, '-c', 'import sys; sys.exit(7)'],
                                 [sys.executable, '-c', f'from pathlib import Path; Path({str(marker)!r}).touch()']]}
            self.assertEqual(CHECKS.execute(plan), 7)
            self.assertFalse(marker.exists())
            skipped = root / 'test_skipped.py'
            skipped.write_text("import unittest\nclass Required(unittest.TestCase):\n"
                               "    @unittest.skip('missing required runtime')\n"
                               "    def test_required(self):\n        pass\n")
            result = subprocess.run(CHECKS.suite_command(str(skipped)), capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Required checks skipped', result.stderr)

    def test_missing_designated_runtime_fails_before_checks(self):
        with patch.dict(os.environ, {'PATH': ''}):
            with self.assertRaisesRegex(RuntimeError, 'Required bash runtime'):
                CHECKS.require_runtimes({'suites': ['harness_compatibility'], 'browser': False})
        with patch.dict(os.environ, {'CHROME_EXECUTABLE': '/does-not-exist/focused-chrome'}):
            with self.assertRaisesRegex(RuntimeError, 'Required Chrome runtime'):
                CHECKS.require_runtimes({'suites': ['layout_tree'], 'browser': True})

    def test_workflow_has_two_pairs_read_only_permissions_and_pinned_actions(self):
        workflow = yaml.safe_load((ROOT / '.github/workflows/focused-checks.yml').read_text())
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        self.assertEqual(workflow['jobs']['checks']['strategy']['matrix'], {'include': [
            {'python': '3.10', 'node': '22'}, {'python': '3.14', 'node': '24'},
        ]})
        self.assertEqual(workflow['jobs']['checks']['if'], "needs.select.outputs.relevant == 'true'")
        for job in workflow['jobs'].values():
            for step in job['steps']:
                if 'uses' in step:
                    self.assertRegex(step['uses'], r'^actions/[a-z-]+@[0-9a-f]{40}$')
                if 'run' in step:
                    self.assertNotIn('${{', step['run'])
                if step.get('uses', '').startswith('actions/checkout@'):
                    self.assertIs(step['with']['persist-credentials'], False)


if __name__ == '__main__':
    unittest.main()
