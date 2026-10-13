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


if __name__ == '__main__':
    unittest.main()
