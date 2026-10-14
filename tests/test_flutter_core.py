import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/flutter-core/scripts/inspect_core.py'
INIT = ROOT / 'plugins/flutter-knowledge/skills/flutter-init/scripts/init_config.py'


ALIGNED_ROOT = 'class MyApp {\n  const MyApp({super.key});\n  Widget build() => MultiBlocProvider(\n    providers: [BlocProvider<NetworkCubit>(create: (_) => sl<NetworkCubit>(), lazy: false)],\n    child: MaterialApp(initialRoute: AppRouter.initialRoute),\n  );\n}'
ALIGNED_CORE_DI = 'final GetIt sl = GetIt.instance;\nvoid registerCoreDependencies() {\n  sl.registerFactory<NetworkCubit>(() => NetworkCubit(sl<NetworkStatus>()));\n}'


class CoreInspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name)
        self.write('pubspec.yaml', 'name: new_app\ndependencies:\n  flutter:\n    sdk: flutter\n')

    def write(self, relative, text):
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def run_inspector(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--project', str(self.project), '--json'],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def initialize(self):
        subprocess.run([sys.executable, str(INIT), '--project', str(self.project)], check=True,
                       capture_output=True)

    def test_missing_config_is_reported_without_initializing_or_creating_core(self):
        code, report = self.run_inspector()
        self.assertEqual(code, 1)
        self.assertEqual(report['configuration']['status'], 'init_required')
        self.assertFalse((self.project / 'flutter-knowledge.yaml').exists())
        self.assertFalse((self.project / 'lib').exists())

    def test_initialized_empty_project_produces_missing_contract_plan_without_writes(self):
        self.initialize()
        before = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.project.rglob('*') if p.is_file()}
        code, report = self.run_inspector()
        self.assertEqual(code, 0)
        self.assertTrue(any(row['id'] == 'api' and row['status'] == 'missing' for row in report['contracts']))
        self.assertEqual(report['completion'], 'inspection_only')
        after = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.project.rglob('*') if p.is_file()}
        self.assertEqual(before, after)

    def test_separate_space_widgets_are_inspected_independently(self):
        self.initialize()
        vertical = 'lib/core/widgets/layout/vertical_space.dart'
        horizontal = 'lib/core/widgets/layout/horizontal_space.dart'
        self.write(vertical, 'class VerticalSpace {}')
        self.write(horizontal, 'class HorizontalSpace {}')
        code, report = self.run_inspector()
        self.assertEqual(code, 0)
        spaces = {row['id']: row for row in report['contracts']
                  if row['id'] in {'vertical_space', 'horizontal_space'}}
        self.assertEqual(set(spaces), {'vertical_space', 'horizontal_space'})
        for role, path in [('vertical_space', vertical), ('horizontal_space', horizontal)]:
            self.assertEqual(spaces[role]['status'], 'evidence_present_requires_review')
            self.assertEqual(spaces[role]['paths'], [path])
        (self.project / horizontal).unlink()
        _, report = self.run_inspector()
        spaces = {row['id']: row for row in report['contracts']
                  if row['id'] in {'vertical_space', 'horizontal_space'}}
        self.assertEqual(spaces['vertical_space']['status'], 'evidence_present_requires_review')
        self.assertEqual(spaces['horizontal_space']['status'], 'missing')
        self.assertFalse((self.project / 'lib/core/widgets/layout/space_widgets.dart').exists())

    def test_custom_contract_is_preserved_as_manual_mapping(self):
        self.initialize()
        config = yaml.safe_load((self.project / 'flutter-knowledge.yaml').read_text())
        config['project_contracts'] = {'api': 'lib/platform/gateway.dart'}
        self.write('flutter-knowledge.yaml', yaml.safe_dump(config))
        self.write('lib/platform/gateway.dart', 'abstract class CustomGateway {}')
        code, report = self.run_inspector()
        self.assertEqual(code, 0)
        api = next(row for row in report['contracts'] if row['id'] == 'api')
        self.assertEqual(api['status'], 'configured_contract_requires_review')
        self.assertEqual(api['paths'], ['lib/platform/gateway.dart'])
        self.assertFalse((self.project / 'lib/core/data/api/api_consumer.dart').exists())

    def test_secure_cache_reports_missing_and_partial_contracts_without_writes(self):
        self.initialize()
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['secure_preferences']['status'], 'missing')
        self.assertEqual(rows['secure_cache_keys']['status'], 'missing')
        self.write('lib/core/data/cache/secure_cache_helper.dart', 'sealed class SecureCacheHelper {}')
        _, report = self.run_inspector()
        row = next(row for row in report['contracts'] if row['id'] == 'secure_preferences')
        self.assertEqual(row['status'], 'incomplete_evidence')
        self.assertFalse(row['contract_checks']['save'])
        self.write('lib/core/data/cache/secure_cache_helper.dart',
                   'sealed class SecureCacheHelper { static Future<void> init() async {} '
                   'static String? get(String key) => null; '
                   'static Future<void> save(String key, String value) async {} '
                   'static Future<void> remove(String key) async {} '
                   'static Future<void> clear() async {} }')
        _, report = self.run_inspector()
        row = next(row for row in report['contracts'] if row['id'] == 'secure_preferences')
        self.assertEqual(row['status'], 'evidence_present_requires_review')
        config = yaml.safe_load((self.project / 'flutter-knowledge.yaml').read_text())
        config['packages']['secure_storage'] = 'none'
        self.write('flutter-knowledge.yaml', yaml.safe_dump(config))
        before = {str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        _, report = self.run_inspector()
        row = next(row for row in report['contracts'] if row['id'] == 'secure_preferences')
        self.assertEqual(row['status'], 'selection_requires_review')
        self.assertEqual(before, {str(path): path.read_bytes()
                                  for path in self.project.rglob('*') if path.is_file()})

    def test_secure_initialization_must_be_awaited_in_startup_order(self):
        self.initialize()
        for setup, expected in [
            ('await CacheHelper.init(); SecureCacheHelper.init(); registerAppDependencies();', False),
            ('await SecureCacheHelper.init(); await CacheHelper.init(); registerAppDependencies();', False),
            ('await CacheHelper.init(); registerAppDependencies(); await SecureCacheHelper.init();', False),
            ('await CacheHelper.init(); await SecureCacheHelper.init(); registerAppDependencies();', True),
        ]:
            with self.subTest(setup=setup):
                self.write('lib/main.dart', 'Future<void> main() async { ' + setup + ' }')
                _, report = self.run_inspector()
                main = next(row for row in report['contracts'] if row['id'] == 'main')
                checks = main['contract_checks']
                self.assertEqual(all(checks[key] for key in (
                    'secure_cache_init', 'cache_init_order', 'secure_before_registration')), expected)

    def test_shared_spacing_family_reports_missing_sliver_implementation(self):
        self.initialize()
        self.write('lib/core/widgets/layout/space_widgets.dart',
                   'class VerticalSpace {}\nclass HorizontalSpace {}\nclass SliverVerticalSpace {}')
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['vertical_space']['status'], 'evidence_present_requires_review')
        self.assertEqual(rows['sliver_vertical_space']['status'], 'evidence_present_requires_review')
        self.assertEqual(rows['sliver_horizontal_space']['status'], 'incomplete_evidence')

    def test_declarations_alone_do_not_supply_required_core_apis(self):
        self.initialize()
        examples = [
            ('router', 'lib/core/router/app_router.dart', 'class AppRouter {}',
             'class AppRouter { static String get initialRoute => root; }'),
            ('app_text_field', 'lib/core/widgets/inputs/app_text_field.dart',
             'class AppTextField { AppTextField({this.textInputAction}); }',
             'class AppTextField { AppTextField({required this.textInputAction}); }'),
            ('interceptor_logger', 'lib/core/data/api/app_interceptor_logger.dart',
             'class AppInterceptorLogger extends Interceptor {}',
             'class AppInterceptorLogger extends TalkerDioLogger {}'),
        ]
        for role, path, incomplete, aligned in examples:
            with self.subTest(role=role):
                self.write(path, incomplete)
                _, report = self.run_inspector()
                row = next(row for row in report['contracts'] if row['id'] == role)
                self.assertEqual(row['status'], 'incomplete_evidence')
                self.write(path, aligned)
                _, report = self.run_inspector()
                row = next(row for row in report['contracts'] if row['id'] == role)
                self.assertEqual(row['status'], 'evidence_present_requires_review')

    def test_root_and_direct_main_require_fixed_paths_and_real_startup(self):
        self.initialize()
        self.write('lib/core_app.dart', 'class MyApp {}')
        self.write('lib/main.dart', 'Future<void> main() async { await bootstrapApp(); runApp(CoreApp()); }')
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['app_root']['status'], 'missing')
        self.assertEqual(rows['main']['status'], 'incomplete_evidence')
        self.assertFalse(rows['main']['contract_checks']['binding'])
        self.assertFalse(rows['main']['contract_checks']['root'])
        self.write('lib/my_app.dart', ALIGNED_ROOT)
        command_block = (SCRIPT.parent.parent / 'references/main-command-block.dart.txt').read_text()
        self.write('lib/main.dart', 'Future<void> main() async { WidgetsFlutterBinding.ensureInitialized(); '
                   'await CacheHelper.init(); await SecureCacheHelper.init(); '
                   'registerAppDependencies(); await sl<SkinRegistry>().load(); '
                   'runApp(const MyApp()); }\n' + command_block)
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['app_root']['status'], 'evidence_present_requires_review')
        self.assertEqual(rows['main']['status'], 'evidence_present_requires_review')
        self.write('lib/app_bootstrap.dart', 'void bootstrapApp() {}')
        _, report = self.run_inspector()
        main = next(row for row in report['contracts'] if row['id'] == 'main')
        self.assertFalse(main['contract_checks']['no_bootstrap_file'])

    def test_global_get_it_contract_rejects_passed_containers_and_keeps_alternatives(self):
        self.initialize()
        self.write('lib/core/di/injection.dart',
                   'final GetIt sl = GetIt.instance; void registerCoreDependencies(GetIt sl) {}')
        self.write('lib/app_injection.dart',
                   'void registerAppDependencies(GetIt sl) { registerCoreDependencies(sl); }')
        self.write('lib/my_app.dart',
                   'class MyApp { const MyApp({super.key, required this.locator}); final GetIt locator; }')
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        for role in ('core_injection', 'app_injection', 'app_root'):
            self.assertEqual(rows[role]['status'], 'incomplete_evidence')
        self.assertFalse(rows['app_root']['contract_checks']['no_widget_locator'])
        self.write('lib/core/di/injection.dart',
                   ALIGNED_CORE_DI)
        self.write('lib/app_injection.dart',
                   'void registerAppDependencies() { registerCoreDependencies(); }')
        self.write('lib/my_app.dart', ALIGNED_ROOT)
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        for role in ('core_injection', 'app_injection', 'app_root'):
            self.assertEqual(rows[role]['status'], 'evidence_present_requires_review')
        config_path = self.project / 'flutter-knowledge.yaml'
        config = yaml.safe_load(config_path.read_text())
        config['packages']['dependency_injection'] = 'provider'
        config['packages']['state_management'] = 'provider'
        config['packages']['routing'] = 'go_router'
        config_path.write_text(yaml.safe_dump(config))
        self.write('lib/my_app.dart', 'class MyApp {}')
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['app_root']['status'], 'evidence_present_requires_review')
        self.assertNotIn('no_widget_locator', rows['app_root']['contract_checks'])
        self.assertNotIn('global_sl', rows['core_injection']['contract_checks'])

    def test_network_factory_provider_and_public_route_evidence_are_selected_and_read_only(self):
        self.initialize()
        self.write('lib/my_app.dart', ALIGNED_ROOT.replace(
            'BlocProvider<NetworkCubit>(create: (_) => sl<NetworkCubit>(), lazy: false)',
            'BlocProvider<NetworkCubit>.value(value: sl<NetworkCubit>())'))
        self.write('lib/core/di/injection.dart', ALIGNED_CORE_DI.replace(
            'registerFactory<NetworkCubit>', 'registerLazySingleton<NetworkCubit>'))
        self.write('lib/core/router/app_router.dart',
                   'class AppRouter { static String get _initialRoute => root; }')
        before = {str(path): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertEqual(rows['network_owner']['status'], 'missing')
        self.assertFalse(rows['app_root']['contract_checks']['network_provider_create'])
        self.assertFalse(rows['app_root']['contract_checks']['no_network_provider_value'])
        self.assertFalse(rows['core_injection']['contract_checks']['network_factory'])
        self.assertFalse(rows['core_injection']['contract_checks']['no_network_singleton'])
        self.assertFalse(rows['router']['contract_checks']['initial_route_getter'])
        self.assertEqual(before, {str(path): path.read_bytes()
                                  for path in self.project.rglob('*') if path.is_file()})
        self.write('lib/my_app.dart', ALIGNED_ROOT)
        self.write('lib/core/di/injection.dart', ALIGNED_CORE_DI)
        self.write('lib/core/router/app_router.dart',
                   'class AppRouter { static String get initialRoute => root; }')
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        for role in ('app_root', 'core_injection', 'router'):
            self.assertEqual(rows[role]['status'], 'evidence_present_requires_review')
        config_path = self.project / 'flutter-knowledge.yaml'
        config = yaml.safe_load(config_path.read_text())
        config['packages']['state_management'] = 'provider'
        config_path.write_text(yaml.safe_dump(config))
        _, report = self.run_inspector()
        rows = {row['id']: row for row in report['contracts']}
        self.assertNotIn('network_provider_create', rows['app_root']['contract_checks'])
        self.assertNotIn('network_factory', rows['core_injection']['contract_checks'])
        self.assertEqual(rows['network_owner']['status'], 'adaptation_requires_review')

    def test_empty_assets_need_typed_prefixes_and_getter_without_comment_evidence(self):
        self.initialize()
        path = 'lib/core/helpers/app_assets.dart'
        self.write(path, "sealed class AppAssets { static const translations = 'assets/translations'; }")
        _, report = self.run_inspector()
        assets = next(row for row in report['contracts'] if row['id'] == 'assets')
        self.assertEqual(assets['status'], 'incomplete_evidence')
        declarations = "\n".join("static const String _" + name + " = 'assets/" + name + "';"
                                  for name in ('images', 'icons', 'translations'))
        self.write(path, 'sealed class AppAssets {\n' + declarations +
                   '\nstatic String get translations => _translations;\n}')
        _, report = self.run_inspector()
        assets = next(row for row in report['contracts'] if row['id'] == 'assets')
        self.assertEqual(assets['status'], 'evidence_present_requires_review')
        self.write(path, 'sealed class AppAssets {\n/*' + declarations +
                   '*/\nstatic String get translations => _translations;\n}')
        _, report = self.run_inspector()
        assets = next(row for row in report['contracts'] if row['id'] == 'assets')
        self.assertFalse(assets['contract_checks']['images'])

    def test_partial_navigation_and_non_bloc_selection_are_reported_without_false_requirements(self):
        self.initialize()
        self.write('lib/core/helpers/extensions/router_extensions.dart',
                   'extension Navigation on BuildContext { void pop() {} }')
        _, report = self.run_inspector()
        navigation = next(row for row in report['contracts'] if row['id'] == 'navigation')
        self.assertEqual(navigation['status'], 'incomplete_evidence')
        self.assertFalse(navigation['contract_checks']['pushNamedAndRemoveUntil'])
        self.assertTrue(any(row['id'] == 'bloc_observer' for row in report['contracts']))
        config = yaml.safe_load((self.project / 'flutter-knowledge.yaml').read_text())
        config['packages']['state_management'] = 'provider'
        self.write('flutter-knowledge.yaml', yaml.safe_dump(config))
        _, report = self.run_inspector()
        self.assertFalse(any(row['id'] == 'bloc_observer' for row in report['contracts']))

    def test_supplied_packages_include_undeclared_and_existing_path_dependencies_without_writes(self):
        self.write('pubspec.yaml', 'name: new_app\nworkspace: [ui/*]\ndependencies:\n'
                   '  flutter:\n    sdk: flutter\n  expressive_sheet:\n    path: ui/sheets\n')
        self.write('ui/sheets/pubspec.yaml', 'name: expressive_sheet\n')
        self.write('ui/sheets/lib/expressive_sheet.dart', "export 'src/sheet.dart';")
        self.write('packages/expressive_loading_indicator/pubspec.yaml', 'name: expressive_loading_indicator\n')
        self.write('packages/unrelated/pubspec.yaml', 'name: unrelated_tool\n')
        self.initialize()
        before = (self.project / 'pubspec.yaml').read_bytes()
        _, report = self.run_inspector()
        packages = {row['name']: row for row in report['local_ui_packages']}
        self.assertEqual(set(packages), {'expressive_sheet', 'expressive_loading_indicator'})
        self.assertTrue(packages['expressive_sheet']['declared'])
        self.assertEqual(packages['expressive_sheet']['declaration'], {'path': 'ui/sheets'})
        self.assertEqual(len(packages['expressive_sheet']['exports']), 1)
        self.assertFalse(packages['expressive_loading_indicator']['declared'])
        self.assertEqual(before, (self.project / 'pubspec.yaml').read_bytes())

    def test_comments_and_literals_cannot_supply_a_contract_declaration(self):
        self.initialize()
        self.write('lib/core/data/api/api_consumer.dart', "final example = 'class ApiConsumer {}';\n")
        _, report = self.run_inspector()
        api = next(row for row in report['contracts'] if row['id'] == 'api')
        self.assertEqual(api['status'], 'incomplete_evidence')

    def test_alternative_mechanisms_require_adaptation_instead_of_default_generation(self):
        self.initialize()
        config = yaml.safe_load((self.project / 'flutter-knowledge.yaml').read_text())
        config['packages']['dependency_injection'] = 'provider'
        self.write('flutter-knowledge.yaml', yaml.safe_dump(config))
        _, report = self.run_inspector()
        di = next(row for row in report['contracts'] if row['id'] == 'core_injection')
        self.assertEqual(di['status'], 'adaptation_requires_review')
        self.assertEqual(di['selection'], 'provider')

    def test_invalid_config_does_not_fall_back_to_defaults(self):
        self.write('flutter-knowledge.yaml', 'schema_version: 1\npackages: [dio]\n')
        code, report = self.run_inspector()
        self.assertEqual(code, 2)
        self.assertEqual(report['completion'], 'could_not_inspect')

    def test_empty_existing_config_is_invalid_instead_of_absent(self):
        self.write('flutter-knowledge.yaml', '{}\n')
        code, report = self.run_inspector()
        self.assertEqual(code, 2)
        self.assertEqual(report['completion'], 'could_not_inspect')
        self.assertEqual((self.project / 'flutter-knowledge.yaml').read_text(), '{}\n')

    def test_unknown_package_keeps_selection_and_requires_adaptation_review(self):
        self.initialize()
        config = yaml.safe_load((self.project / 'flutter-knowledge.yaml').read_text())
        config['packages']['http_client'] = 'private_transport'
        self.write('flutter-knowledge.yaml', yaml.safe_dump(config))
        before = (self.project / 'flutter-knowledge.yaml').read_bytes()
        code, report = self.run_inspector()
        self.assertEqual(code, 0)
        self.assertEqual(report['configuration']['unknown_selected_packages'], ['http_client'])
        api = next(row for row in report['contracts'] if row['id'] == 'api')
        self.assertEqual(api['status'], 'adaptation_requires_review')
        self.assertEqual(api['selection'], 'private_transport')
        self.assertEqual((self.project / 'flutter-knowledge.yaml').read_bytes(), before)

    def test_rerun_retains_stable_startup_and_registration_evidence_without_writes(self):
        self.initialize()
        self.write('lib/main.dart', 'Future<void> main() async { runApp(existingApp); }')
        self.write('lib/platform/dependencies.dart',
                   'void registerCoreDependencies() {}\nFuture<void> registerAppDependencies() async {}')
        first = self.run_inspector()
        second = self.run_inspector()
        self.assertEqual(first, second)
        self.assertEqual(first[1]['startup_candidates'], ['lib/main.dart'])
        self.assertEqual(first[1]['registration_candidates'], ['lib/platform/dependencies.dart'])
        self.assertFalse((self.project / 'lib/core').exists())


if __name__ == '__main__':
    unittest.main()
