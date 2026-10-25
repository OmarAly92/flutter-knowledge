import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BenchmarkPackageTests(unittest.TestCase):
    def test_mocking_imports_respect_selection_and_dependencies(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            fixture = out / 'fixture-app'
            fixture.mkdir()
            translations = fixture / 'assets/translations'
            translations.mkdir(parents=True)
            for locale in ['en', 'ar']:
                (translations / f'{locale}.json').write_text('{}')
            cases = [(package, package, declared) for package in ['mockito', 'mocktail']
                     for declared in [True, False]] + [('mockito', 'mocktail', True), ('mockito', None, True)]
            for package, selected, declared in cases:
                with self.subTest(package=package, selected=selected, declared=declared):
                    run = out / 'runs' / 'branch-forced-t1-r1'
                    if run.exists():
                        shutil.rmtree(run)
                    run.mkdir(parents=True)
                    (fixture / 'pubspec.yaml').write_text('name: app\n')
                    dependencies = f'  {package}: any\n' if declared else ''
                    (run / 'pubspec.yaml').write_text(
                        'name: app\ndev_dependencies:\n  flutter_test:\n    sdk: flutter\n'
                        '  bloc_test: any\n' + dependencies)
                    if selected is not None:
                        (run / 'flutter-knowledge.yaml').write_text(
                            f'schema_version: 1\npackages:\n  mocking: {selected}\n')
                    (run / 'SKILLS_READ.txt').write_text('flutter-testing/SKILL.md\n')
                    test = run / 'test/feature/trips/data/repository/trips_repository_test.dart'
                    test.parent.mkdir(parents=True)
                    test.write_text(f"import 'package:{package}/{package}.dart';\n"
                                    "import 'package:flutter_test/flutter_test.dart';\n"
                                    'class MockRepository extends Mock {}\nvoid main() {}\n')
                    result = subprocess.run(
                        [sys.executable, str(ROOT / 'benchmark/grade.py'), str(out)],
                        capture_output=True, text=True)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    violations = json.loads((out / 'grades.json').read_text())[
                        'branch-forced-t1-r1']['violations']
                    self.assertNotIn('tests_use_mockito', violations)
                    self.assertEqual(violations.get('test_mocking_package_mismatch', 0),
                                     int(selected is not None and selected != package))
                    self.assertEqual(violations.get('test_deps_missing', 0), int(not declared))

    def grade_translations(self, fixture_en, run_en, run_ar, usage):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            fixture = out / 'fixture-app'
            run = out / 'runs' / 'branch-forced-t1-r1'
            for root, en, ar in ((fixture, fixture_en, fixture_en), (run, run_en, run_ar)):
                translations = root / 'assets/translations'
                translations.mkdir(parents=True)
                (translations / 'en.json').write_text(json.dumps(en))
                (translations / 'ar.json').write_text(json.dumps(ar, ensure_ascii=False))
                (root / 'pubspec.yaml').write_text('name: app\n')
            (run / 'SKILLS_READ.txt').write_text('flutter-testing/SKILL.md\n')
            screen = run / 'lib/feature/trip_details/presentation/trip_details_screen/ui/trip_details_screen.dart'
            screen.parent.mkdir(parents=True)
            screen.write_text(f"Widget build(BuildContext context) => AppText({usage}.tr());\n")
            result = subprocess.run([sys.executable, str(ROOT / 'benchmark/grade.py'), str(out)],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads((out / 'grades.json').read_text())['branch-forced-t1-r1']

    def test_nested_translation_keys_resolve_through_generated_accessors(self):
        fixture = {'common': {'save': 'Save'}, 'trips': {'title': 'Trips'}}
        grade = self.grade_translations(
            fixture,
            {**fixture, 'tripDetails': {'delete': 'Delete'}, 'stray': 'Stray', 'orders': {'x': 'X'}},
            {**fixture, 'tripDetails': {'delete': 'حذف'}, 'stray': 'شارد', 'orders': {'x': 'س'}},
            'LocaleKeys.tripDetails_delete')
        violations = grade['violations']
        self.assertNotIn('locale_key_missing_from_json', violations)
        self.assertNotIn('en_ar_key_mismatch', violations)
        self.assertEqual(violations['translation_key_outside_feature_group'], 2)
        self.assertEqual(grade['info']['ar_real'], 3)
        missing = self.grade_translations(fixture, fixture, fixture, 'LocaleKeys.tripDetails_delete')
        self.assertEqual(missing['violations']['locale_key_missing_from_json'], 1)

    def test_flat_catalog_new_keys_stay_flat(self):
        fixture = {'save': 'Save', 'trips': 'Trips'}
        grade = self.grade_translations(
            fixture,
            {**fixture, 'deleteTrip': 'Delete', 'tripDetails': {'title': 'Trip'}},
            {**fixture, 'deleteTrip': 'حذف', 'tripDetails': {'title': 'رحلة'}},
            'LocaleKeys.deleteTrip')
        violations = grade['violations']
        self.assertNotIn('locale_key_missing_from_json', violations)
        self.assertEqual(violations['translation_key_nested_in_flat_catalog'], 1)
        self.assertNotIn('translation_key_outside_feature_group', violations)


if __name__ == '__main__':
    unittest.main()
