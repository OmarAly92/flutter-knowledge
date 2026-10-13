import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/visual-verification/scripts/design_cache.py'


class DesignCacheTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'design.html'
        self.source.write_text('<html><body>Login</body></html>')
        self.font = self.root / 'font.woff'
        self.font.write_bytes(b'font-v1')
        self.profile = self.root / 'profile.json'
        self.profile_data = {
            'viewport': {'width': 16, 'height': 12}, 'dpr': 2,
            'screen': 'Login', 'state': 'loaded', 'selector': '.login',
            'skin': 'dark', 'locale': 'en', 'text_scale': 1,
            'capture_adapter': 'fixture-browser-v1',
            'safe_area': {'top': 0, 'right': 0, 'bottom': 0, 'left': 0},
            'data': {'email': 'demo@example.invalid'},
        }
        self.profile.write_text(json.dumps(self.profile_data))
        self.inputs = self.root / 'inputs.json'
        self.inputs.write_text(json.dumps({'complete': True, 'files': ['font.woff'], 'external_resources': []}))
        self.facts = self.root / 'layout.json'
        self.facts.write_text(json.dumps({'tag': 'div', 'w': 16, 'h': 12}))
        self.reference = self.root / 'reference.png'
        Image.new('RGB', (32, 24), 'black').save(self.reference)
        self.cache = self.root / 'cache.json'

    def call(self, action, *extra):
        args = [sys.executable, str(SCRIPT), action, '--source', str(self.source),
                '--profile', str(self.profile), '--inputs-manifest', str(self.inputs), '--cache', str(self.cache)]
        if action == 'record':
            args.extend(['--facts', str(self.facts)])
        proc = subprocess.run(args + list(extra), capture_output=True, text=True)
        return proc, json.loads(proc.stdout) if proc.stdout else {}

    def snapshot(self):
        return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.root.iterdir() if p.is_file()}

    def test_warm_cache_reuses_facts_without_writes(self):
        proc, recorded = self.call('record')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        before = self.snapshot()
        proc, result = self.call('check')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(result['facts_reusable'])
        self.assertEqual(result['fingerprint'], recorded['fingerprint'])
        self.assertFalse(result['reference_reusable'])
        self.assertEqual(before, self.snapshot())

    def test_missing_cache_is_a_read_only_miss(self):
        before = self.snapshot()
        proc, result = self.call('check')
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(result['status'], 'miss')
        self.assertEqual(before, self.snapshot())

    def test_source_asset_profile_and_fact_changes_invalidate_cache(self):
        mutations = [
            lambda: self.source.write_text('<html>changed</html>'),
            lambda: self.font.write_bytes(b'font-v2'),
            lambda: self.facts.write_text('{"tag":"div","w":20,"h":12}'),
        ]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.call('record')
                mutate()
                before = self.snapshot()
                proc, result = self.call('check')
                self.assertEqual(proc.returncode, 1)
                self.assertFalse(result['facts_reusable'])
                self.assertEqual(before, self.snapshot())
        for field, value in [('state', 'error'), ('skin', 'light'), ('locale', 'ar'), ('text_scale', 2), ('dpr', 3), ('data', {'email': 'other'})]:
            with self.subTest(field=field):
                self.profile.write_text(json.dumps(self.profile_data))
                self.call('record')
                self.profile.write_text(json.dumps({**self.profile_data, field: value}))
                proc, result = self.call('check')
                self.assertEqual(proc.returncode, 1)
                self.assertFalse(result['facts_reusable'])

    def test_unknown_dependencies_and_raw_remote_urls_cannot_be_cached(self):
        for manifest in [{'complete': False, 'files': [], 'external_resources': []},
                         {'complete': True, 'files': [], 'external_resources': ['https://example.invalid/font.woff']}]:
            with self.subTest(manifest=manifest):
                self.inputs.write_text(json.dumps(manifest))
                proc, result = self.call('record')
                self.assertEqual(proc.returncode, 2)
                self.assertFalse(self.cache.exists())

    def test_archived_reference_is_never_promoted_by_a_cache_hit(self):
        proc, _ = self.call('record', '--reference', str(self.reference), '--reference-status', 'archived')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc, result = self.call('check')
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(result['reference_status'], 'archived')
        self.assertFalse(result['reference_reusable'])

    def test_fresh_capture_requires_matching_provenance_and_dimensions(self):
        proc, initial = self.call('record')
        metadata = self.root / 'capture.json'
        metadata.write_text(json.dumps({'fingerprint': initial.get('fingerprint'), 'tool': self.profile_data['capture_adapter'], 'captured_at': '2026-10-10T00:00:00Z', 'reference_sha256': hashlib.sha256(self.reference.read_bytes()).hexdigest()}))
        extra = ['--reference', str(self.reference), '--reference-status', 'fresh', '--capture-metadata', str(metadata)]
        proc, result = self.call('record', *extra)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        proc, result = self.call('check')
        self.assertTrue(result['reference_reusable'])
        self.font.write_bytes(b'changed-font')
        proc, result = self.call('check')
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(result['reference_reusable'])
        metadata.write_text(json.dumps({'fingerprint': 'wrong', 'tool': self.profile_data['capture_adapter'], 'captured_at': '2026-10-10T00:00:00Z', 'reference_sha256': hashlib.sha256(self.reference.read_bytes()).hexdigest()}))
        proc, result = self.call('record', *extra)
        self.assertEqual(proc.returncode, 2)
        self.call('record')
        proc, latest = self.call('check')
        metadata.write_text(json.dumps({'fingerprint': latest['fingerprint'], 'tool': self.profile_data['capture_adapter'], 'captured_at': '2026-10-10T00:00:00Z', 'reference_sha256': hashlib.sha256(self.reference.read_bytes()).hexdigest()}))
        Image.new('RGB', (20, 20), 'black').save(self.reference)
        proc, result = self.call('record', *extra)
        self.assertEqual(proc.returncode, 2)

    def test_missing_capture_provenance_and_unmeasured_facts_are_rejected(self):
        proc, initial = self.call('record')
        proc, _ = self.call('record', '--reference', str(self.reference), '--reference-status', 'fresh')
        self.assertEqual(proc.returncode, 2)
        for value in (None, 0, True):
            with self.subTest(timestamp=value):
                metadata = self.root / 'capture.json'
                metadata.write_text(json.dumps({'fingerprint': initial['fingerprint'], 'tool': self.profile_data['capture_adapter'], 'captured_at': value}))
                proc, result = self.call('record', '--reference', str(self.reference), '--reference-status', 'fresh', '--capture-metadata', str(metadata))
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(result['status'], 'error')
        self.facts.write_text('{"tag":"div","w":0,"h":0,"hidden":true}')
        proc, _ = self.call('record')
        self.assertEqual(proc.returncode, 2)

    def test_record_cannot_overwrite_source_or_extraction_inputs(self):
        for path in (self.source, self.facts, self.profile, self.inputs, self.font):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                self.cache = path
                proc, result = self.call('record')
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(path.read_bytes(), original)

    def test_renderer_identity_is_required_and_invalidates_reuse(self):
        self.profile.write_text(json.dumps({key: value for key, value in self.profile_data.items() if key != 'capture_adapter'}))
        proc, result = self.call('record')
        self.assertEqual(proc.returncode, 2)
        self.profile.write_text(json.dumps(self.profile_data))
        self.call('record')
        self.profile.write_text(json.dumps({**self.profile_data, 'capture_adapter': 'fixture-browser-v2'}))
        proc, result = self.call('check')
        self.assertEqual(proc.returncode, 1)
        self.assertFalse(result['facts_reusable'])

    def test_current_metadata_cannot_promote_a_different_same_size_image(self):
        proc, initial = self.call('record')
        metadata = self.root / 'capture.json'
        metadata.write_text(json.dumps({
            'fingerprint': initial['fingerprint'], 'tool': self.profile_data['capture_adapter'],
            'captured_at': '2026-10-10T00:00:00Z',
            'reference_sha256': hashlib.sha256(self.reference.read_bytes()).hexdigest(),
        }))
        wrong = self.root / 'archived.png'
        Image.new('RGB', (32, 24), 'red').save(wrong)
        proc, result = self.call('record', '--reference', str(wrong), '--reference-status', 'fresh', '--capture-metadata', str(metadata))
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(result['status'], 'error')
        proc, result = self.call('check')
        self.assertFalse(result['reference_reusable'])

    def test_reference_with_a_bad_png_checksum_is_a_structured_error(self):
        data = bytearray(self.reference.read_bytes())
        data[data.index(b'IDAT') + 4] ^= 1
        self.reference.write_bytes(data)
        proc, result = self.call('record', '--reference', str(self.reference), '--reference-status', 'archived')
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(result['status'], 'error')
        self.assertFalse(result['reference_reusable'])

    def test_deleted_input_corrupt_cache_and_corrupt_reference_are_not_hits(self):
        self.call('record')
        self.font.unlink()
        proc, _ = self.call('check')
        self.assertEqual(proc.returncode, 1)
        self.font.write_bytes(b'font')
        self.call('record')
        self.cache.write_text('broken')
        proc, _ = self.call('check')
        self.assertEqual(proc.returncode, 1)
        self.reference.write_bytes(b'not a PNG')
        proc, _ = self.call('record', '--reference', str(self.reference), '--reference-status', 'archived')
        self.assertEqual(proc.returncode, 2)


if __name__ == '__main__':
    unittest.main()
