import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/flutter-review/scripts/review.py'
INIT = ROOT / 'plugins/flutter-knowledge/skills/flutter-init/scripts/init_config.py'


class FlutterReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        self.project = self.repo / 'apps/sample'
        self.project.mkdir(parents=True)
        self.write('pubspec.yaml', yaml.safe_dump({'name': 'sample', 'dependencies': {'flutter': {'sdk': 'flutter'}},
                                                 'dev_dependencies': {'flutter_test': {'sdk': 'flutter'}}}))
        subprocess.run([sys.executable, str(INIT), '--project', str(self.project)], capture_output=True, check=True)
        self.write('lib/core/theme/app_tokens.dart', 'class AppTokens {}')
        self.write('lib/main.dart', 'class MainScreen extends StatelessWidget {}')
        self.write('test/main_test.dart', 'void main() {}')
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        self.tool_dir = self.base / 'tools'
        self.tool_dir.mkdir()
        self.log = self.base / 'calls.jsonl'
        stub = '''#!/usr/bin/env python3
import json,os,sys
from pathlib import Path
with open(os.environ['FK_REVIEW_LOG'], 'a') as stream:
    stream.write(json.dumps(sys.argv) + '\\n')
if len(sys.argv)>1 and sys.argv[1]=='format' and '--output=none' not in sys.argv:
    Path(sys.argv[-1]).write_text('MUTATED')
sys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))
'''
        for name in ('dart', 'flutter'):
            tool = self.tool_dir / name
            tool.write_text(stub)
            tool.chmod(0o755)
        self.env = {**os.environ, 'PATH': str(self.tool_dir) + os.pathsep + os.environ['PATH'],
                    'FK_REVIEW_LOG': str(self.log)}

    def write(self, path, text):
        target = self.project / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, check=True)

    def run_review(self, *args, env=None):
        run = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), '--json', *args],
                             capture_output=True, text=True, env=env or self.env)
        report = json.loads(run.stdout) if run.stdout else {}
        return run, report

    def snapshot(self):
        return {str(p.relative_to(self.project)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.project.rglob('*') if p.is_file()}

    def test_subdirectory_scope_includes_tracked_and_untracked_files_without_writes(self):
        self.write('lib/main.dart', 'class MainScreen extends StatelessWidget { void load() {} }')
        self.write('lib/feature/new/presentation/new_screen/ui/new_screen.dart', 'class NewScreen extends StatelessWidget {}')
        before = self.snapshot()
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertCountEqual(report['scope'], ['lib/main.dart', 'lib/feature/new/presentation/new_screen/ui/new_screen.dart'])
        calls = [json.loads(line) for line in self.log.read_text().splitlines()]
        formatter = next(call for call in calls if 'format' in call)
        self.assertIn('--output=none', formatter)
        self.assertIn('--set-exit-if-changed', formatter)
        self.assertTrue(all('--update-goldens' not in call for call in calls))
        self.assertTrue(any('analyze' in call and '--no-pub' in call for call in calls))
        self.assertTrue(any('test' in call and '--no-pub' in call for call in calls))
        self.assertEqual(before, self.snapshot())

    def test_ignored_nested_project_falls_back_to_all_authored_files(self):
        (self.repo / '.gitignore').write_text('ignored_app/\n')
        self.git('add', '.gitignore')
        self.git('commit', '-qm', 'ignore')
        self.project = self.repo / 'ignored_app'
        self.project.mkdir()
        self.write('pubspec.yaml', yaml.safe_dump({'name': 'nested', 'dependencies': {'flutter': {'sdk': 'flutter'}},
                                                 'dev_dependencies': {'flutter_test': {'sdk': 'flutter'}}}))
        subprocess.run([sys.executable, str(INIT), '--project', str(self.project)], capture_output=True, check=True)
        self.write('lib/feature/demo/presentation/demo_screen/ui/demo_screen.dart', "class DemoScreen extends StatelessWidget { void f() { print('x'); } }")
        self.write('test/demo_test.dart', 'void main() {}')
        self.write('lib/generated.g.dart', "print('generated');")
        before = self.snapshot()
        run, report = self.run_review()
        self.assertEqual(report['scope_kind'], 'all authored Dart files')
        self.assertCountEqual(report['scope'], ['lib/feature/demo/presentation/demo_screen/ui/demo_screen.dart', 'test/demo_test.dart'])
        self.assertTrue(any(f['rule'] == 'print' for f in report['findings']))
        self.assertEqual(run.returncode, 1)
        self.assertEqual(before, self.snapshot())

    def test_generated_only_git_representation_falls_back_to_all_authored_files(self):
        (self.repo / '.gitignore').write_text('ignored_app/lib/feature/\nignored_app/test/\n')
        self.project = self.repo / 'ignored_app'
        self.project.mkdir()
        self.write('pubspec.yaml', yaml.safe_dump({'name': 'nested', 'dependencies': {'flutter': {'sdk': 'flutter'}},
                                                 'dev_dependencies': {'flutter_test': {'sdk': 'flutter'}}}))
        subprocess.run([sys.executable, str(INIT), '--project', str(self.project)], capture_output=True, check=True)
        self.write('lib/models.g.dart', "print('generated');")
        self.git('add', '.gitignore', 'ignored_app')
        self.git('commit', '-qm', 'generated only')
        self.write('lib/feature/a.dart', "class A { void f() { print('x'); } }")
        self.write('test/a_test.dart', 'void main() {}')
        run, report = self.run_review()
        self.assertEqual(report['scope_kind'], 'all authored Dart files')
        self.assertCountEqual(report['scope'], ['lib/feature/a.dart', 'test/a_test.dart'])
        self.assertNotIn('lib/models.g.dart', report['scope'])
        self.assertEqual(run.returncode, 1)

    def test_clean_tracked_project_keeps_changed_only_scope(self):
        run, report = self.run_review()
        self.assertEqual(report['scope'], [])
        self.assertEqual(report['scope_kind'], 'changed and untracked files')
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_tracked_project_with_one_ignored_file_keeps_changed_only_scope(self):
        self.write('.gitignore', 'lib/ignored.dart\n')
        self.write('lib/ignored.dart', "void f() { print('x'); }")
        self.write('lib/new_file.dart', 'class NewFile {}')
        run, report = self.run_review()
        self.assertEqual(report['scope_kind'], 'changed and untracked files')
        self.assertEqual(report['scope'], ['lib/new_file.dart'])

    def test_real_print_and_token_literals_block_but_comments_strings_and_generated_files_do_not(self):
        self.write('lib/feature/demo/presentation/demo_screen/ui/demo_screen.dart',
                   "class DemoScreen extends StatelessWidget { final color = Color(0xFF112233); void f() { print('x'); } }")
        self.write('lib/feature/demo/presentation/demo_screen/ui/fake.dart',
                   "// print('comment'); Color(0xFF000000)\nconst example = \"print('sample') Color(0xFF000000)\";")
        self.write('lib/generated.g.dart', "print('generated'); Color(0xFF000000);")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1)
        blocking = [finding for finding in report['findings'] if finding['severity']=='blocking']
        self.assertTrue(any(finding['rule']=='print' for finding in blocking))
        self.assertTrue(any(finding['rule']=='token' for finding in blocking))
        self.assertTrue(all(finding.get('path','').endswith('demo_screen.dart') for finding in blocking))
        self.assertNotIn('lib/generated.g.dart', report['scope'])

    def test_executable_interpolation_is_checked_but_raw_examples_are_not(self):
        self.write('lib/interpolation.dart', "void f() { final message = '${print(1)}'; final example = r'${print(2)}'; }")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1)
        prints = [finding for finding in report['findings'] if finding['rule']=='print']
        self.assertEqual(len(prints), 1)

    def test_literal_missing_assets_block_and_dynamic_assets_are_not_guessed(self):
        self.write('lib/feature/demo/presentation/demo_screen/ui/demo_screen.dart',
                   "final a = Image.asset('assets/missing.png'); final b = Image.asset('assets/$id.png');")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1)
        missing = [f for f in report['findings'] if f['rule']=='asset_missing']
        self.assertEqual(len(missing), 1)
        self.assertIn('assets/missing.png', missing[0]['message'])

    def test_existing_asset_must_be_declared_and_fonts_count_as_declarations(self):
        self.write('assets/icons/a.png', 'fixture')
        self.write('lib/assets.dart', "const a = 'assets/icons/a.png';")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1)
        self.assertTrue(any(f['rule']=='asset_undeclared' for f in report['findings']))
        pubspec = yaml.safe_load((self.project/'pubspec.yaml').read_text())
        pubspec['flutter'] = {'assets': ['assets/icons/']}
        self.write('pubspec.yaml', yaml.safe_dump(pubspec))
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_tool_failure_and_skip_are_visible_without_modifying_files(self):
        self.write('lib/main.dart', 'class MainScreen extends StatelessWidget {}')
        before = self.snapshot()
        run, report = self.run_review('--all', '--skip-tests', env={**self.env, 'FK_TOOL_EXIT':'1'})
        self.assertEqual(run.returncode, 1)
        self.assertTrue(any(f['rule']=='format' and f['severity']=='blocking' for f in report['findings']))
        self.assertTrue(any(check['name']=='tests' and check['status']=='skipped' for check in report['checks']))
        self.assertEqual(before, self.snapshot())

    def test_malformed_pubspec_returns_cannot_run_with_structured_evidence(self):
        self.write('pubspec.yaml', '[broken')
        run, report = self.run_review()
        self.assertEqual(run.returncode, 2)
        self.assertTrue(any(f['severity']=='error' for f in report['findings']))

    def test_valid_asset_directory_prefix_is_reviewed_without_false_missing_file(self):
        self.write('assets/images/logo.png', 'fixture')
        pubspec = yaml.safe_load((self.project/'pubspec.yaml').read_text())
        pubspec['flutter'] = {'assets': ['assets/images/']}
        self.write('pubspec.yaml', yaml.safe_dump(pubspec))
        self.write('lib/assets.dart', "const prefix = 'assets/images/';")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(any(f['rule']=='asset_missing' for f in report['findings']))

    def test_directory_constants_without_a_trailing_separator_remain_manual(self):
        self.write('assets/icons/a.png', 'fixture')
        pubspec = yaml.safe_load((self.project / 'pubspec.yaml').read_text())
        pubspec['flutter'] = {'assets': ['assets/icons/']}
        self.write('pubspec.yaml', yaml.safe_dump(pubspec))
        cases = [("static const String _icons = 'assets/icons';", 0),
                 ("final icon = Image.asset('assets/icons');", 1),
                 ("const missing = 'assets/missing';", 1)]
        for code, expected in cases:
            with self.subTest(code=code):
                self.write('lib/assets.dart', code)
                run, report = self.run_review()
                self.assertEqual(run.returncode, expected, run.stderr)
                if expected == 0:
                    self.assertTrue(any(hit['rule'] == 'asset_prefix' for hit in report['findings']))

    def test_malformed_asset_metadata_reports_cannot_run(self):
        for flutter in [{'fonts': [{'family':'Demo', 'fonts':value}]} for value in (7, 0, False, {})] + [{'assets':7}, {'fonts':7}, 0, False, []]:
            with self.subTest(flutter=flutter):
                pubspec = yaml.safe_load((self.project/'pubspec.yaml').read_text())
                pubspec['flutter'] = flutter
                self.write('pubspec.yaml', yaml.safe_dump(pubspec))
                run, report = self.run_review('--all')
                self.assertEqual(run.returncode, 2)
                self.assertTrue(any(f['severity']=='error' for f in report['findings']))

    def test_missing_config_is_reported_without_initializing_it(self):
        (self.project/'flutter-knowledge.yaml').unlink()
        run, report = self.run_review()
        self.assertEqual(run.returncode, 2)
        self.assertFalse((self.project/'flutter-knowledge.yaml').exists())
        self.assertTrue(any(f['rule']=='configuration' for f in report['findings']))

    def test_local_logs_preserve_full_failures_with_a_concise_report(self):
        tool = self.tool_dir / 'flutter'
        tool.write_text(tool.read_text().replace("sys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))",
            "print('progress line\\n' * 2000)\nprint('Failing tests:\\n  example: actual failing case')\nsys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))"))
        before = self.snapshot()
        logs = self.base / 'review-logs'
        run, report = self.run_review('--log-dir', str(logs), env={**self.env, 'FK_TOOL_EXIT': '1'})
        self.assertEqual(run.returncode, 1, run.stderr)
        failed = [item for item in report['checks'] if item['status'] == 'failed']
        self.assertTrue(failed)
        for check in failed:
            raw = Path(check['log_path']).read_text()
            self.assertEqual(check['exit_code'], 1)
            if check['name'] != 'format':
                self.assertIn('example: actual failing case', raw)
                self.assertGreater(check['output_bytes'], check['summary_bytes'])
        self.assertLess(len(run.stdout), 8000)
        self.assertEqual(before, self.snapshot())

    def test_timeout_retains_partial_output_as_incomplete_evidence(self):
        import importlib.util
        from unittest.mock import patch
        sys.path.insert(0, str(SCRIPT.parent))
        spec = importlib.util.spec_from_file_location('review_timeout_subject', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        logs = self.base / 'timeout-logs'
        logs.mkdir()
        report = {'checks': [], 'findings': [], 'log_directory': str(logs)}
        command = ['flutter', 'test', '--no-pub']
        error = subprocess.TimeoutExpired(command, 300, output=b'failed case before timeout', stderr=b'partial stack')
        with patch.object(module.subprocess, 'run', side_effect=error):
            module.run_check('tests', command, self.project, report)
        check = report['checks'][0]
        self.assertEqual(check['status'], 'error')
        self.assertFalse(check.get('log_complete', True))
        raw = Path(check['log_path']).read_text()
        self.assertIn('failed case before timeout', raw)
        self.assertIn('partial stack', raw)
        self.assertTrue(any(hit['severity'] == 'error' for hit in report['findings']))

    def test_truncated_flutter_failure_list_retains_every_case_once(self):
        cases = [f'/fixture/test/feature_{index}/screen_test.dart: ' +
                 (f'failed scenario {index} with a long descriptive requirement ' * 3).rstrip()
                 for index in range(12)]
        progress = [f'00:30 +519 ~5 -7: {case} [E]' for case in cases]
        output = '\r'.join(progress + [progress[-1], 'Failing tests:',
                                      *cases[:4], '  ... and 8 more'])
        tool = self.tool_dir / 'flutter'
        tool.write_text(tool.read_text().replace(
            "sys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))",
            f"print({output!r})\nsys.exit(1)"))
        run, report = self.run_review('--log-dir', str(self.base / 'logs'))
        self.assertEqual(run.returncode, 1, run.stderr)
        failures = next(hit for hit in report['findings'] if hit['rule'] == 'tests')
        for case in cases:
            self.assertEqual(failures['message'].count(case), 1)
        self.assertNotIn('and 8 more', failures['message'])

    def test_reported_test_failures_block_despite_zero_process_exit(self):
        output = ('00:02 +21 -2: /fixture/test/profile_test.dart: save and reopen [E]\n'
                  '00:02 +21 -2: Some tests failed.')
        tool = self.tool_dir / 'flutter'
        tool.write_text(tool.read_text().replace(
            "sys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))",
            f"if len(sys.argv)>1 and sys.argv[1]=='test':\n    print({output!r})\nsys.exit(0)"))
        before = self.snapshot()
        run, report = self.run_review('--log-dir', str(self.base / 'logs'))
        self.assertEqual(run.returncode, 1, run.stderr)
        check = next(item for item in report['checks'] if item['name'] == 'tests')
        self.assertEqual(check['status'], 'failed')
        self.assertEqual(check['exit_code'], 0)
        self.assertIn(output, Path(check['log_path']).read_text())
        self.assertTrue(any(hit['rule'] == 'tests' and hit['severity'] == 'blocking'
                            for hit in report['findings']))
        self.assertEqual(before, self.snapshot())

    def test_passing_test_name_with_error_marker_is_not_a_failure(self):
        output = ('00:00 +0: /fixture/test/profile_test.dart: displays [E]\n'
                  '00:00 +1: All tests passed!')
        tool = self.tool_dir / 'flutter'
        tool.write_text(tool.read_text().replace(
            "sys.exit(int(os.environ.get('FK_TOOL_EXIT','0')))",
            f"if len(sys.argv)>1 and sys.argv[1]=='test':\n    print({output!r})\nsys.exit(0)"))
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        check = next(item for item in report['checks'] if item['name'] == 'tests')
        self.assertEqual(check['status'], 'passed')

    def test_convention_candidates_ignore_strings_and_report_real_code(self):
        self.write('lib/feature/x/presentation/x_screen/ui/x_screen.dart',
                   "class XScreen extends StatelessWidget { Widget build(BuildContext context) { return BlocProvider(create: (_) => XCubit(), child: AppText('Hello')); } }")
        self.write('lib/feature/x/presentation/x_screen/logic/x_state.dart',
                   'final class GetXSuccessState extends XState { final XModel model; GetXSuccessState(this.model); }')
        self.write('lib/feature/x/presentation/x_screen/logic/wrong.dart',
                   'class XNotifier extends ChangeNotifier { Future<void> load() async { await fetch(); notifyListeners(); } }')
        self.write('lib/example.dart', 'const example = "class FakeNotifier extends ChangeNotifier { BlocProvider(create: x); }";')
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        rules = {hit['rule'] for hit in report['findings']}
        self.assertTrue({'screen_provider', 'success_payload', 'state_naming', 'async_lifecycle', 'localized_text'} <= rules)

    def test_nav_bar_change_tab_state_is_not_a_success_payload(self):
        self.write('lib/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/app_nav_bar_state.dart',
                   'final class ChangeTabSuccessState extends AppNavBarState { final AppNavTab tab; const ChangeTabSuccessState(this.tab); }')
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(any(hit['rule'] == 'success_payload' for hit in report['findings']))

    def test_file_placement_flags_misplaced_presentation_files(self):
        cases = {
            'lib/feature/x/presentation/widgets/x_avatar.dart': ('class XAvatar extends StatelessWidget {}', True),
            'lib/feature/x/presentation/widget/x_avatar.dart': ('class XAvatar extends StatelessWidget {}', False),
            'lib/feature/x/presentation/x_screen/logic/x_board.dart': ('class XBoard {\n  final String name;\n}', True),
            'lib/feature/x/presentation/x_screen/logic/helpers/x_board.dart': ('class XBoard {\n  final String name;\n}', True),
            'lib/feature/x/presentation/x_screen/logic/helpers/x_board_builder.dart': ('sealed class XBoardBuilder {\n  static XBoardModel build(XInputsParams input) {\n    final name = input.name;\n    return XBoardModel(name: name);\n  }\n}', False),
            'lib/feature/x/presentation/x_screen/logic/helpers/x_tab.dart': ('enum XTab {\n  home(labelKey: \'home\');\n\n  const XTab({required this.labelKey});\n\n  final String labelKey;\n}', False),
            'lib/feature/x/presentation/x_screen/logic/x_cubit.dart': ('class XCubit extends Cubit<XState> {\n  final XRepository repository;\n}', False),
            'lib/feature/x/presentation/x_screen/ui/widgets/x_row.dart': ('class XRow extends StatelessWidget {\n  final String name;\n}', False),
        }
        for path, (source, _) in cases.items():
            self.write(path, source)
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        flagged = {hit['path'] for hit in report['findings'] if hit['rule'] == 'file_placement'}
        self.assertEqual(flagged, {path for path, (_, expected) in cases.items() if expected})

    def test_state_instance_identity_cannot_replace_value_equality(self):
        path = 'lib/feature/x/presentation/x_screen/logic/x_state.dart'
        cases = [
            ('List<Object?> get props => [identityHashCode(this)];', True),
            ('List<Object?> get props => [identityHashCode(owner)];', False),
            ("const example = 'identityHashCode(this)';", False),
            ('void recordState() => log(identityHashCode(this));', False),
            ('int get hashCode => identityHashCode(this);', True),
        ]
        for source, blocked in cases:
            with self.subTest(source=source):
                self.write(path, source)
                run, report = self.run_review()
                findings = [hit for hit in report['findings'] if hit['rule'] == 'state_identity_equality']
                self.assertEqual(bool(findings), blocked)
                if blocked:
                    self.assertEqual(run.returncode, 1)
                    self.assertEqual(findings[0]['severity'], 'blocking')
                    self.assertEqual(findings[0]['path'], path)
        self.assertFalse(any(hit.get('path') == 'lib/example.dart' for hit in report['findings']))

    def test_localized_accessor_and_physical_geometry_are_not_blocked(self):
        self.write('lib/feature/x/presentation/x_screen/ui/x_body.dart',
                   "class XBody extends StatelessWidget { Widget build(BuildContext context) => AppText(LocaleKeys.title.tr()); final padding = EdgeInsets.only(left: tokens.space.md); }")
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertFalse(any(hit['rule'] == 'localized_text' for hit in report['findings']))
        self.assertTrue(any(hit['rule'] == 'directional_layout' and hit['severity'] == 'review' for hit in report['findings']))

    def test_design_scope_requires_evidence_without_writes(self):
        before = self.snapshot()
        run, report = self.run_review('--design-screen', 'Login / loaded')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertTrue(any(hit['rule'] == 'design_evidence' and hit['severity'] == 'blocking' for hit in report['findings']))
        self.assertEqual(before, self.snapshot())

    def test_design_rows_require_artifacts_percentages_and_manual_inspection(self):
        self.write('docs/design/verification.md',
                   '| Screen / state | Source and reference PNG | Capture profile | Flutter PNG / diff PNG | Overall difference | Worst region | Status / remaining differences |\n'
                   '| --- | --- | --- | --- | --- | --- | --- |\n'
                   '| Login / loaded | [source](screen.html) [ref](ref.png) | 375x812 DPR2 | [actual](actual.png) [diff](diff.png) | 1.24% | 8.10% | VERIFIED |\n')
        run, report = self.run_review('--design-screen', 'Login / loaded')
        self.assertEqual(run.returncode, 1, run.stderr)
        import base64
        png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aD1sAAAAASUVORK5CYII=')
        for name in ('ref.png', 'actual.png', 'diff.png'):
            path = self.project / 'docs/design' / name
            path.write_bytes(png)
        before = self.snapshot()
        run, report = self.run_review('--design-screen', 'Login / loaded')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(any(hit['rule'] == 'design_inspection' for hit in report['findings']))
        self.assertEqual(report['design_results'][0]['overall_percent'], 1.24)
        self.assertEqual(before, self.snapshot())
        run, report = self.run_review('--design-screen', 'Checkout / loaded')
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertEqual(report['completion'], 'blocked')

    def test_design_evidence_rejects_claims_without_valid_distinct_artifacts(self):
        for name in ('ref.png', 'actual.png', 'diff.png'):
            self.write('docs/design/' + name, 'presence fixture; image inspection is manual')
        base = '| Login / loaded | [ref](ref.png) | DPR2 | [actual](actual.png) [diff](diff.png) | 1.24% | 8.10% | VERIFIED |'
        cases = [
            base.replace('VERIFIED', 'DIFF'),
            base.replace('VERIFIED', 'NOT VERIFIED'),
            base.replace('1.24%', '101%'),
            base.replace('8.10%', 'unknown'),
            base.replace('actual.png', 'ref.png'),
            base + '\n' + base,
        ]
        for row in cases:
            with self.subTest(row=row):
                self.write('docs/design/verification.md', row)
                run, report = self.run_review('--design-screen', 'Login / loaded')
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(report['design_results'], [])
                self.assertEqual(report['completion'], 'blocked')

    def test_deleted_translation_is_checked_without_reading_deleted_dart(self):
        self.write('assets/translations/en.json', '{"title": "Title"}')
        self.write('assets/translations/ar.json', '{"title": "عنوان"}')
        self.git('add', '.')
        self.git('commit', '-qm', 'translations')
        (self.project / 'assets/translations/ar.json').unlink()
        (self.project / 'lib/main.dart').unlink()
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertTrue(any(hit['rule'] == 'translation_keys' for hit in report['findings']))
        self.assertNotIn('lib/main.dart', report['scope'])

    def test_missing_translation_keys_and_dependency_selection_are_visible(self):
        self.write('assets/translations/en.json', '{"title": "Title"}')
        self.write('assets/translations/ar.json', '{}')
        pubspec = yaml.safe_load((self.project / 'pubspec.yaml').read_text())
        pubspec['dependencies']['http'] = '^1.0.0'
        self.write('pubspec.yaml', yaml.safe_dump(pubspec))
        run, report = self.run_review()
        self.assertEqual(run.returncode, 1, run.stderr)
        self.assertTrue(any(hit['rule'] == 'translation_keys' for hit in report['findings']))
        self.assertTrue(any(hit['rule'] == 'package_selection' and 'http' in hit['message'] for hit in report['findings']))
        self.assertTrue(any(hit['rule'] == 'dependency_added' and 'http' in hit['message'] for hit in report['findings']))

    def test_duplicate_widget_in_new_file_is_reported(self):
        self.write('lib/feature/new/presentation/new_screen/ui/main_screen.dart', 'class MainScreen extends StatelessWidget {}')
        run, report = self.run_review()
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertTrue(any(f['rule']=='duplicate_widget' for f in report['findings']))


if __name__ == '__main__':
    unittest.main()
