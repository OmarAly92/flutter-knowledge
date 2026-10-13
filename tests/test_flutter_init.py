import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/flutter-init/scripts/init_config.py'


class FlutterInitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.pubspec = self.project / 'pubspec.yaml'
        self.config = self.project / 'flutter-knowledge.yaml'

    def write_project(self, dependencies=None, dev_dependencies=None):
        self.pubspec.write_text(yaml.safe_dump({
            'name': 'sample',
            'dependencies': {'flutter': {'sdk': 'flutter'}, **(dependencies or {})},
            'dev_dependencies': dev_dependencies or {},
        }, sort_keys=False))

    def run_init(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), *args],
                              capture_output=True, text=True)

    def read_config(self):
        return yaml.safe_load(self.config.read_text())

    def test_missing_categories_get_the_whole_default_stack_without_editing_pubspec(self):
        self.write_project()
        original = self.pubspec.read_bytes()
        run = self.run_init()
        self.assertEqual(run.returncode, 0, run.stderr)
        config = self.read_config()
        for category, expected in {
            'state_management': 'flutter_bloc', 'dependency_injection': 'get_it',
            'routing': 'navigator', 'http_client': 'dio', 'localization': 'easy_localization',
            'local_database': 'drift', 'equality': 'equatable', 'serialization': 'manual',
            'mocking': 'mocktail', 'state_testing': 'bloc_test', 'logging': 'talker',
            'preferences': 'shared_preferences', 'typography_scaling': 'flutter_screenutil',
            'motion': 'motor', 'shapes': 'material_shapes', 'network_status': 'connectivity_plus',
            'test_runner': 'flutter_test',
        }.items():
            with self.subTest(category=category):
                self.assertEqual(config['packages'][category], expected)
        self.assertFalse(config['resolution']['state_management']['declared'])
        self.assertEqual(config['resolution']['state_management']['source'], 'recommended')
        self.assertEqual(self.pubspec.read_bytes(), original)
        self.assertEqual({p.name for p in self.project.iterdir()}, {'pubspec.yaml', 'flutter-knowledge.yaml'})

    def test_existing_alternatives_and_companion_packages_are_detected(self):
        self.write_project({'flutter_riverpod': '^2.0.0', 'riverpod': '^2.0.0',
                            'go_router': '^14.0.0', 'http': '^1.0.0', 'hive_ce': '^2.0.0',
                            'flutter_localizations': {'sdk': 'flutter'}, 'intl': 'any'},
                           {'mockito': 'any', 'flutter_test': {'sdk': 'flutter'}})
        run = self.run_init()
        self.assertEqual(run.returncode, 0, run.stderr)
        config = self.read_config()
        for category, expected in {'state_management': 'flutter_riverpod', 'routing': 'go_router',
                                   'http_client': 'http', 'local_database': 'hive_ce',
                                   'localization': 'flutter_localizations', 'mocking': 'mockito'}.items():
            self.assertEqual(config['packages'][category], expected)
            self.assertTrue(config['resolution'][category]['declared'])
        self.assertEqual(config['packages']['state_testing'], 'flutter_test')

    def test_ambiguity_is_visible_and_explicit_choice_resolves_it(self):
        self.write_project({'drift': 'any', 'hive_ce': 'any', 'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        self.assertEqual(self.run_init().returncode, 1)
        config = self.read_config()
        self.assertIsNone(config['packages']['local_database'])
        self.assertCountEqual(config['resolution']['local_database']['candidates'], ['drift', 'hive_ce'])
        self.assertIsNone(config['packages']['state_testing'])
        self.assertEqual(self.run_init('--check').returncode, 1)
        config['packages'].update(local_database='hive_ce', state_management='flutter_bloc', state_testing='bloc_test')
        self.config.write_text(yaml.safe_dump(config))
        self.assertEqual(self.run_init('--check').returncode, 0)

    def test_rerun_preserves_choices_custom_fields_and_is_byte_stable(self):
        self.write_project({'dio': 'any', 'http': 'any'})
        self.config.write_text('schema_version: 1\npackages:\n  http_client: http\n  local_database: none\nproject_contracts:\n  api: lib/custom/client.dart\n')
        self.assertEqual(self.run_init().returncode, 0)
        config = self.read_config()
        self.assertEqual(config['packages']['http_client'], 'http')
        self.assertEqual(config['packages']['local_database'], 'none')
        self.assertEqual(config['project_contracts']['api'], 'lib/custom/client.dart')
        first = self.config.read_bytes()
        self.assertEqual(self.run_init().returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)
        self.assertEqual(self.run_init('--check').returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)

    def test_yaml_anchors_git_path_and_sdk_declarations_are_read_without_overrides_as_installs(self):
        self.pubspec.write_text('name: sample\ndependencies: &runtime\n  flutter: {sdk: flutter}\n  flutter_bloc: {git: https://example.invalid/bloc.git}\n  dio: {path: ../dio}\ndev_dependencies:\n  mocktail: any\ndependency_overrides:\n  riverpod: any\n')
        self.assertEqual(self.run_init().returncode, 0)
        config = self.read_config()
        self.assertEqual(config['packages']['state_management'], 'flutter_bloc')
        self.assertEqual(config['packages']['http_client'], 'dio')
        self.assertEqual(config['packages']['mocking'], 'mocktail')

    def test_invalid_input_never_overwrites_existing_config(self):
        for invalid in ['schema_version: 99\npackages: {}\n', 'schema_version: 1\npackages: []\n',
                        'schema_version: 1\npackages:\n  routing: [go_router]\n',
                        'schema_version: 1\npackages: {}\npackages: {}\n', '[broken',
                        'schema_version: 1\npackages: {routing: manual}\n',
                        'schema_version: 1\npackages: {state_management: navigator}\n',
                        'schema_version: 1\npackages: {local_database: manual}\n',
                        'schema_version: 1\npackages: {state_managment: flutter_riverpod}\n']:
            with self.subTest(invalid=invalid):
                self.write_project()
                self.config.write_text(invalid)
                run = self.run_init()
                self.assertEqual(run.returncode, 2)
                self.assertEqual(self.config.read_text(), invalid)

    def test_malformed_pubspec_and_non_flutter_projects_do_not_create_config(self):
        for content in ['[broken', 'name: sample\ndependencies: []\n', 'name: sample\ndependencies: {flutter: {sdk: flutter}}\ndev_dependencies: []\n', 'name: plain_dart\n',
                        'name: sample\ndependencies: {flutter: {sdk: flutter}}\ndependencies: {}\n']:
            with self.subTest(content=content):
                self.pubspec.write_text(content)
                self.assertEqual(self.run_init().returncode, 2)
                self.assertFalse(self.config.exists())

    def test_localization_and_codegen_companions_are_not_false_conflicts(self):
        self.write_project({'easy_localization': 'any', 'intl': 'any', 'flutter_localizations': {'sdk': 'flutter'},
                            'freezed_annotation': 'any', 'json_annotation': 'any'},
                           {'freezed': 'any', 'json_serializable': 'any', 'build_runner': 'any'})
        self.assertEqual(self.run_init().returncode, 0)
        config = self.read_config()
        self.assertEqual(config['packages']['localization'], 'easy_localization')
        self.assertEqual(config['packages']['serialization'], 'freezed')

    def test_check_requires_complete_config_and_does_not_write(self):
        self.write_project()
        self.assertEqual(self.run_init('--check').returncode, 2)
        self.assertFalse(self.config.exists())
        self.config.write_text('schema_version: 1\npackages: {}\n')
        original = self.config.read_bytes()
        self.assertEqual(self.run_init('--check').returncode, 1)
        self.assertEqual(self.config.read_bytes(), original)


    def write_source(self, relative, text):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_decisive_source_usage_resolves_lingering_declared_stack(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        self.write_source('lib/feature/demo/presentation/demo_screen/logic/demo_cubit.dart',
                          "import 'package:flutter_riverpod/flutter_riverpod.dart';\nclass DemoCubit extends Notifier<DemoState> {}\n")
        run = self.run_init()
        self.assertEqual(run.returncode, 0, run.stderr)
        config = self.read_config()
        self.assertEqual(config['packages']['state_management'], 'flutter_riverpod')
        self.assertIn('lib/feature/demo/presentation/demo_screen/logic/demo_cubit.dart',
                      config['resolution']['state_management']['used_in'])
        self.assertEqual(config['packages']['state_testing'], 'flutter_test')

    def test_unused_state_import_does_not_outvote_active_backend(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        self.write_source('lib/stale.dart', "import 'package:flutter_bloc/flutter_bloc.dart';")
        self.write_source('lib/live.dart', "import 'package:flutter_riverpod/flutter_riverpod.dart';\nclass LiveCubit extends Notifier<LiveState> {}")
        self.assertEqual(self.run_init().returncode, 0)
        self.assertEqual(self.read_config()['packages']['state_management'], 'flutter_riverpod')

    def test_generated_riverpod_owner_annotations_are_active_evidence(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any', 'riverpod_annotation': 'any'})
        self.write_source('lib/owner.dart', "import 'package:riverpod_annotation/riverpod_annotation.dart';\n@Riverpod(keepAlive: true) class Owner extends _$Owner {}")
        self.assertEqual(self.run_init().returncode, 0)
        self.assertEqual(self.read_config()['packages']['state_management'], 'flutter_riverpod')

    def test_comments_strings_and_generated_imports_do_not_vote_for_a_stack(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        self.write_source('lib/fake.dart', "/* import 'package:flutter_bloc/flutter_bloc.dart'; */\nconst sample = \"import 'package:flutter_riverpod/flutter_riverpod.dart';\";\n")
        self.write_source('lib/generated.g.dart', "import 'package:flutter_bloc/flutter_bloc.dart';")
        self.assertEqual(self.run_init().returncode, 1)
        self.assertIsNone(self.read_config()['packages']['state_management'])

    def test_discovery_reports_locations_without_changing_fixed_conventions_or_explicit_choices(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        self.config.write_text('schema_version: 1\npackages:\n  state_management: flutter_bloc\nproject_contracts:\n  api: lib/custom/api.dart\n')
        self.write_source('lib/core/widgets/buttons/app_button.dart', 'class AppButton extends StatelessWidget {}')
        self.write_source('lib/design_system/components/app_action.dart', 'class AppAction extends StatelessWidget {}')
        self.write_source('lib/core/theme/app_tokens.dart', 'class AppTokens {}')
        self.write_source('lib/core/data/api/api_consumer.dart', 'abstract class ApiConsumer {}')
        self.write_source('lib/wallet_page.dart', "import 'package:flutter_riverpod/flutter_riverpod.dart';\nclass WalletPage extends ConsumerWidget {}")
        self.assertEqual(self.run_init().returncode, 0)
        config = self.read_config()
        self.assertEqual(config['packages']['state_management'], 'flutter_bloc')
        self.assertEqual(config['project_contracts']['api'], 'lib/custom/api.dart')
        self.assertEqual(config['project_contracts']['theme'], 'lib/core/theme/app_tokens.dart')
        self.assertIn('lib/core/widgets', config['discovery']['shared_widget_locations'])
        self.assertIn('lib/design_system/components', config['discovery']['shared_widget_locations'])
        self.assertEqual(config['discovery']['routed_widget_suffixes']['Page'], 1)
        self.assertNotIn('AppButton', str(config['discovery']))
        first = self.config.read_bytes()
        self.assertEqual(self.run_init().returncode, 0)
        self.assertEqual(self.config.read_bytes(), first)

    def test_asset_declarations_and_multiple_live_stacks_remain_evidence_not_an_automatic_choice(self):
        self.write_project({'flutter_bloc': 'any', 'flutter_riverpod': 'any'})
        pubspec = yaml.safe_load(self.pubspec.read_text())
        pubspec['flutter'] = {'assets': ['assets/icons/', 'assets/images/logo.png']}
        self.pubspec.write_text(yaml.safe_dump(pubspec))
        self.write_source('lib/a.dart', "import 'package:flutter_bloc/flutter_bloc.dart';\nclass ACubit extends Cubit<AState> {}")
        self.write_source('lib/b.dart', "import 'package:flutter_riverpod/flutter_riverpod.dart';\nclass BCubit extends Notifier<BState> {}")
        self.assertEqual(self.run_init().returncode, 1)
        config = self.read_config()
        self.assertIsNone(config['packages']['state_management'])
        self.assertEqual(config['discovery']['assets'], ['assets/icons/', 'assets/images/logo.png'])


if __name__ == '__main__':
    unittest.main()
