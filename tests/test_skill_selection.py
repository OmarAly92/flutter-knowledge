import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'benchmark/skill_selection.py'
SPEC = importlib.util.spec_from_file_location('skill_selection', SCRIPT)
SELECTION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SELECTION)


class SkillSelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.expected = {item['id']: item['expected'] for item in json.loads(SELECTION.CASES.read_text())}
        names = {name for name in self.expected.values() if name}
        for label in ('before', 'after'):
            for name in names:
                path = self.root / label / 'plugins/flutter-knowledge/skills' / name / 'SKILL.md'
                path.parent.mkdir(parents=True)
                path.write_text(f'---\nname: {name}\ndescription: Use for this task.\n---\n\nPreserved rules.\n')
            SELECTION.prepare(self.root / label, self.root / f'{label}-probe')
            self.save_decisions(label, self.expected)

    def save_decisions(self, label, decisions):
        path = self.root / f'{label}.json'
        path.write_text(json.dumps(decisions))
        return label, path

    def score(self):
        return SELECTION.score(self.root / 'before-probe', self.root / 'after-probe',
                               [(label, self.root / f'{label}.json') for label in ('before', 'after')])

    def test_preparation_hides_answers_and_accepts_multiline_yaml(self):
        path = self.root / 'before/plugins/flutter-knowledge/skills/flutter-init/SKILL.md'
        path.write_text('---\nname: flutter-init\ndescription: >-\n  Use when initializing\n  project configuration.\n---\n\nPreserved rules.\n')
        out = self.root / 'prepared'
        SELECTION.prepare(self.root / 'before', out)
        catalog = json.loads((out / 'catalog.json').read_text())
        self.assertEqual(next(item['description'] for item in catalog if item['name'] == 'flutter-init'),
                         'Use when initializing project configuration.')
        prompt = (out / 'prompt.txt').read_text()
        self.assertNotIn('"expected"', prompt)
        self.assertNotIn('Preserved rules.', prompt)
        self.assertIn('"negative-react"', prompt)

    def test_report_preserves_misses_size_and_body_changes(self):
        decisions = {**self.expected, 'html-update': 'flutter-core'}
        self.save_decisions('after', decisions)
        path = self.root / 'after/plugins/flutter-knowledge/skills/flutter-init/SKILL.md'
        path.write_text(path.read_text().replace('Use for this task.', 'Use for init.').replace('Preserved rules.', 'Changed rules.'))
        SELECTION.prepare(self.root / 'after', self.root / 'after-probe')
        report = self.score()
        self.assertEqual(report['selection']['before']['correct'], len(self.expected))
        self.assertEqual(report['selection']['after']['runs'][0]['misses'], ['html-update'])
        self.assertEqual(report['changed_cases'], [{'id': 'html-update', 'expected': 'html-to-widget',
                                                  'before_correct': 1, 'after_correct': 0}])
        self.assertEqual(report['changed_skill_bodies'], ['flutter-init'])
        self.assertLess(report['size']['after']['description_words'], report['size']['before']['description_words'])

    def test_incomplete_or_invalid_decisions_are_not_silently_scored(self):
        invalid = [dict(list(self.expected.items())[1:]), {**self.expected, 'unknown-id': None},
                   {**self.expected, 'html': 'invented-skill'}, {**self.expected, 'html': ['html-to-widget']}]
        for decisions in invalid:
            with self.subTest(decisions=decisions):
                self.save_decisions('after', decisions)
                with self.assertRaises(ValueError):
                    self.score()

    def test_changed_cases_or_skill_names_invalidate_comparison(self):
        path = self.root / 'after-probe/manifest.json'
        original = json.loads(path.read_text())
        for mutation in ('cases', 'skills'):
            with self.subTest(mutation=mutation):
                changed = json.loads(json.dumps(original))
                if mutation == 'cases':
                    changed['cases_sha256'] = 'stale'
                else:
                    changed['catalog'].pop()
                path.write_text(json.dumps(changed))
                with self.assertRaises(ValueError):
                    self.score()

    def test_duplicate_request_ids_are_rejected_before_scoring(self):
        path = self.root / 'after.json'
        raw = json.dumps(self.expected)
        path.write_text('{"html-update":"flutter-core",' + raw[1:])
        with self.assertRaisesRegex(ValueError, 'Duplicate decision id'):
            self.score()

    def test_cli_rejects_unpaired_or_duplicate_repetitions(self):
        common = [sys.executable, str(SCRIPT), 'score', '--before', str(self.root / 'before-probe'),
                  '--after', str(self.root / 'after-probe')]
        variants = [
            ['--result', f'before={self.root / "before.json"}'],
            ['--result', f'before={self.root / "before.json"}', '--result', f'after={self.root / "before.json"}'],
        ]
        for arguments in variants:
            with self.subTest(arguments=arguments):
                result = subprocess.run(common + arguments, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
