import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/visual-verification/scripts/stage_usage.py'
SPEC = importlib.util.spec_from_file_location('stage_usage', SCRIPT)
USAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(USAGE)


class StageUsageTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.event = {'schema_version': 1, 'event_id': 'source-request-1', 'stage': 'source',
            'workload': {'task': 'login-update', 'fixture_sha256': 'a' * 64,
                         'source_sha256': 'b' * 64, 'coverage_sha256': 'c' * 64, 'renderer': 'fixture-renderer'},
            'agent': {'provider': 'fixture-provider', 'model': 'fixture-model', 'plugin': 'before'},
            'measurements': {'elapsed_seconds': 2.5, 'tool_calls': 2, 'captures': 1, 'correction_rounds': 0},
            'usage': {'availability': 'reported', 'origin': 'fixture provider request report',
                      'counter_id': 'request-1', 'input_tokens': 100, 'output_tokens': 20,
                      'cached_input_tokens': 80, 'total_tokens': 120}}

    def save(self, event, directory='events'):
        source = self.root / (directory + '-' + event['event_id'] + '.json')
        source.write_text(json.dumps(event))
        return USAGE.record(source, self.root / directory), source

    def test_reported_cache_is_not_added_to_usage_and_unknowns_stay_unknown(self):
        self.save(self.event)
        first = USAGE.summarize(self.root / 'events')['stages']['source']
        self.assertEqual(first['tokens']['total_tokens'], 120)
        self.assertEqual(first['tokens']['cached_input_tokens'], 80)
        second = copy.deepcopy(self.event)
        second['event_id'] = 'source-request-2'
        second['usage'] = {'availability': 'unavailable', 'reason': 'No provider stage counters'}
        second['measurements']['captures'] = None
        self.save(second)
        combined = USAGE.summarize(self.root / 'events')['stages']['source']
        self.assertIsNone(combined['tokens']['total_tokens'])
        self.assertIsNone(combined['measurements']['captures'])
        self.assertEqual(combined['usage_unavailable_events'], 1)

    def test_resume_is_idempotent_but_changed_or_tampered_events_are_rejected(self):
        target, source = self.save(self.event)
        original = target.read_bytes()
        self.assertEqual(USAGE.record(source, self.root / 'events'), target)
        self.assertEqual(target.read_bytes(), original)
        self.event['measurements']['captures'] = 2
        source.write_text(json.dumps(self.event))
        with self.assertRaises(ValueError):
            USAGE.record(source, self.root / 'events')
        with self.assertRaises(ValueError):
            USAGE.summarize(self.root / 'events')
        source.write_text(json.dumps({**self.event, 'measurements': {**self.event['measurements'], 'captures': 1}}))
        document = json.loads(target.read_text())
        document['measurement']['measurements']['captures'] = 99
        target.write_text(json.dumps(document))
        with self.assertRaises(ValueError):
            USAGE.summarize(self.root / 'events')

    def test_provider_counter_cannot_be_double_counted_and_task_total_stays_separate(self):
        self.save(self.event)
        second = copy.deepcopy(self.event)
        second['event_id'] = 'implementation-request-1'
        second['stage'] = 'implementation'
        self.save(second)
        with self.assertRaises(ValueError):
            USAGE.summarize(self.root / 'events')
        second['stage'] = 'task_total'
        target = self.root / 'events/implementation-request-1.json'
        target.unlink()
        self.save(second)
        summary = USAGE.summarize(self.root / 'events')
        self.assertEqual(summary['stages']['source']['tokens']['total_tokens'], 120)
        self.assertEqual(summary['stages']['task_total']['tokens']['total_tokens'], 120)
        self.assertNotIn('total_tokens', summary)
        duplicate = copy.deepcopy(second)
        duplicate['event_id'] = 'task-counter-duplicate'
        duplicate['usage']['counter_id'] = 'task-counter-new-snapshot'
        self.save(duplicate)
        with self.assertRaises(ValueError):
            USAGE.summarize(self.root / 'events')

    def test_comparison_requires_same_measured_workload_and_preserves_unknown_reductions(self):
        self.save(self.event, 'before')
        after = copy.deepcopy(self.event)
        after['agent']['plugin'] = 'after'
        after['usage']['input_tokens'] = 90
        after['usage']['total_tokens'] = 110
        self.save(after, 'after')
        report = USAGE.compare(self.root / 'before', self.root / 'after')
        self.assertEqual(report['deltas']['source']['tokens']['total_tokens']['change'], -10)
        after['usage'] = {'availability': 'unavailable', 'reason': 'No provider stage counters'}
        after_dir = self.root / 'unknown'
        self.save(after, 'unknown')
        report = USAGE.compare(self.root / 'before', after_dir)
        self.assertIsNone(report['deltas']['source']['tokens']['total_tokens']['reduction_percent'])
        for group, key in [('agent', 'model'), ('workload', 'coverage_sha256'), ('workload', 'renderer')]:
            with self.subTest(key=key):
                changed = copy.deepcopy(after)
                changed[group][key] = 'd' * 64 if key.endswith('sha256') else 'different'
                directory = 'mismatch-' + key
                self.save(changed, directory)
                with self.assertRaises(ValueError):
                    USAGE.compare(self.root / 'before', self.root / directory)

    def test_invalid_counters_never_produce_savings_or_zero_usage(self):
        for field, replacement in [('input_tokens', -1), ('total_tokens', 121),
                                   ('cached_input_tokens', 101), ('output_tokens', True)]:
            with self.subTest(field=field):
                event = copy.deepcopy(self.event)
                event['usage'][field] = replacement
                with self.assertRaises(ValueError):
                    USAGE.validate_measurement(event)
        event = copy.deepcopy(self.event)
        event['usage'] = {'availability': 'unavailable', 'reason': 'Unavailable', 'total_tokens': 0}
        with self.assertRaises(ValueError):
            USAGE.validate_measurement(event)
        event = copy.deepcopy(self.event)
        event['measurements']['elapsed_seconds'] = float('nan')
        with self.assertRaises(ValueError):
            USAGE.validate_measurement(event)

    def test_partial_token_components_constrain_reported_total_without_inventing_unknowns(self):
        cases = [(100, None, 80, 10), (None, 50, None, 10),
                 (None, None, 80, 10), (None, 50, 80, 100)]
        for inputs, outputs, cached, total in cases:
            with self.subTest(counters=(inputs, outputs, cached, total)):
                event = copy.deepcopy(self.event)
                event['usage'].update(input_tokens=inputs, output_tokens=outputs,
                                      cached_input_tokens=cached, total_tokens=total)
                with self.assertRaises(ValueError):
                    USAGE.validate_measurement(event)
        event = copy.deepcopy(self.event)
        event['usage']['output_tokens'] = None
        self.save(event)
        summary = USAGE.summarize(self.root / 'events')['stages']['source']['tokens']
        self.assertEqual(summary['total_tokens'], 120)
        self.assertIsNone(summary['output_tokens'])


if __name__ == '__main__':
    unittest.main()
