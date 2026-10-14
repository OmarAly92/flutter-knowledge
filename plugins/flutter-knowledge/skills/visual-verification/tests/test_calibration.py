import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/calibrate.py'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class CalibrationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = self.root / 'design.html'
        self.source.write_text('synthetic source for gate regression tests')
        self.core = self.root / 'core.dart'
        self.core.write_text('synthetic runtime binding; not Flutter proof')
        self.profile = {'viewport': {'width': 100, 'height': 80}, 'dpr': 2,
                        'crop': {'x': 0, 'y': 0, 'width': 100, 'height': 80},
                        'screen': 'component', 'state': 'idle', 'selector': '#field',
                        'skin': 'dark', 'locale': 'en', 'text_scale': 1,
                        'safe_area': dict.fromkeys(('top', 'right', 'bottom', 'left'), 0),
                        'data': {}, 'capture_adapter': 'synthetic-browser',
                        'runtime_adapter': 'synthetic-camera',
                        'screenutil_design_size': {'width': 100, 'height': 80}}
        self.expected = self.root / 'source.png'
        self.actual = self.root / 'actual.png'
        Image.new('RGB', (200, 160), 'black').save(self.expected)
        Image.new('RGB', (200, 160), 'black').save(self.actual)
        bounds = {'x': 10, 'y': 20, 'width': 60, 'height': 30}
        self.source_row = {'profile': self.profile, 'capture': self.binding(self.expected),
                           'facts': {'profile': {'skin': 'dark'}, 'viewport': {'width': 100, 'height': 80, 'dpr': 2},
                                     'nodes': [{'selector': '#field', 'box': bounds,
                                                'computed': {'font-size': '16px', 'font-weight': '400',
                                                             'line-height': '20px', 'letter-spacing': 'normal'}}]}}
        self.runtime_row = {'skin': 'dark', 'shadows_enabled': True, 'profile': self.profile, 'capture': self.binding(self.actual),
                            'viewport': {'width': 100, 'height': 80, 'dpr': 2, 'text_scale': 1, 'locale': 'en', 'safe_area': self.profile['safe_area']},
                            'screenutil': {'design_size': {'width': 100, 'height': 80},
                                           'scale_width': 1, 'scale_height': 1},
                            'typography': {'font_size': 16, 'font_weight': 400,
                                           'line_height': 20, 'letter_spacing': 0},
                            'painted_bounds': bounds, 'outer_bounds': {**bounds, 'height': 50}}
        self.source_export = self.root / 'source.json'
        self.runtime_export = self.root / 'runtime.json'
        self.manifest = self.root / 'manifest.json'
        (self.root / 'camera.log').write_text('Synthetic test camera log, not execution proof')
        self.plan = {'capture': {'command': ['synthetic-camera'], 'log': 'camera.log'},
                     'schema_version': 1, 'source_inputs': ['design.html'],
                     'runtime_inputs': ['core.dart'], 'inputs_complete': True,
                     'rows': [{'id': 'field', 'kind': 'field', 'profile': self.profile,
                               'selector': '#field', 'source_export': 'source.json',
                               'runtime_export': 'runtime.json'}]}
        self.persist()

    def binding(self, path):
        return {'path': str(path), 'sha256': digest(path)}

    def persist(self):
        self.manifest.write_text(json.dumps(self.plan))
        self.source_export.write_text(json.dumps({'bindings': [self.binding(self.source)], 'rows': {'field': self.source_row}}))
        self.runtime_export.write_text(json.dumps({'bindings': [self.binding(self.core)], 'rows': {'field': self.runtime_row}}))

    def run_gate(self, directory='attempt'):
        output = self.root / directory
        proc = subprocess.run([sys.executable, str(SCRIPT), 'run', '--manifest', str(self.manifest),
                               '--out', str(output)], capture_output=True, text=True)
        self.assertTrue((output / 'results.json').is_file(), proc.stderr + proc.stdout)
        return proc, json.loads((output / 'results.json').read_text())

    def check_gate(self, path):
        proc = subprocess.run([sys.executable, str(SCRIPT), 'check', '--manifest', str(self.manifest),
                               '--results', str(path)], capture_output=True, text=True)
        return proc, json.loads(proc.stdout)

    def reviewed_gate(self, accepted=True):
        proc, report = self.run_gate()
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        original = self.root / 'attempt/results.json'
        inspection = self.root / 'inspection.json'
        inspection.write_text(json.dumps({'fingerprint': report['fingerprint'], 'results_sha256': digest(original),
                                         'inspector': 'synthetic regression',
                                         'notes': 'Synthetic gate-only attestation, not Flutter evidence',
                                         'rows': {'field': {'accepted': accepted, 'notes': 'Synthetic comparison decision'}}}))
        proc = subprocess.run([sys.executable, str(SCRIPT), 'finalize', '--manifest', str(self.manifest),
                               '--results', str(original), '--inspection', str(inspection),
                               '--out', str(self.root / 'reviewed')], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0 if accepted else 1, proc.stderr + proc.stdout)
        reviewed = self.root / 'reviewed/results.json'
        checked, status = self.check_gate(reviewed)
        self.assertEqual(checked.returncode, 0, checked.stderr + checked.stdout)
        self.assertEqual(status['calibration_reusable'], accepted)
        self.assertFalse(status['screen_verified'])
        return report, reviewed

    def assert_reuse_rejected(self, path):
        proc, status = self.check_gate(path)
        self.assertEqual(proc.returncode, 1, proc.stderr + proc.stdout)
        self.assertFalse(status['calibration_reusable'])
        self.assertFalse(status['screen_verified'])

    def test_old_inspection_cannot_be_transplanted_to_changed_inputs(self):
        _, reviewed = self.reviewed_gate()
        retained_inspection = (self.root / 'inspection.json').read_bytes()
        self.core.write_text('changed input after inspection')
        self.persist()
        self.assert_reuse_rejected(reviewed)
        proc, fresh = self.run_gate('uninspected')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        report = json.loads(reviewed.read_text())
        report.update(identity=fresh['identity'], fingerprint=fresh['fingerprint'])
        reviewed.write_text(json.dumps(report))
        self.assert_reuse_rejected(reviewed)
        self.assertEqual((self.root / 'inspection.json').read_bytes(), retained_inspection)

    def test_every_inspected_artifact_is_required_despite_final_inventory_edits(self):
        original, reviewed = self.reviewed_gate()
        finalized = json.loads(reviewed.read_text())
        for artifact in original['artifacts']:
            path = Path(artifact['path'])
            retained = path.read_bytes()
            for mutation in ('deleted', 'deleted-and-omitted', 'modified-and-rebound', 'omitted'):
                with self.subTest(artifact=path.name, mutation=mutation):
                    report = copy.deepcopy(finalized)
                    try:
                        if mutation.startswith('deleted'):
                            path.unlink()
                        elif mutation == 'modified-and-rebound':
                            path.write_bytes(b'changed comparison evidence')
                            report['artifacts'] = [self.binding(path) if entry['path'] == str(path) else entry
                                                   for entry in report['artifacts']]
                        if mutation in ('deleted-and-omitted', 'omitted'):
                            report['artifacts'] = [entry for entry in report['artifacts'] if entry['path'] != str(path)]
                        reviewed.write_text(json.dumps(report))
                        self.assert_reuse_rejected(reviewed)
                    finally:
                        path.write_bytes(retained)
                        reviewed.write_text(json.dumps(finalized))
        proc, status = self.check_gate(reviewed)
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertTrue(status['calibration_reusable'])

    def test_final_report_must_be_exact_permitted_inspection_derivation(self):
        _, reviewed = self.reviewed_gate()
        finalized = json.loads(reviewed.read_text())
        extra = self.root / 'uninspected-proof.txt'
        extra.write_text('uninspected extra evidence')
        for mutation in ('extra-artifact', 'duplicate-artifact', 'missing-source-artifact', 'extra-metadata',
                         'schema', 'screen-verified', 'measurement', 'missing-row'):
            with self.subTest(mutation=mutation):
                report = copy.deepcopy(finalized)
                if mutation == 'extra-artifact':
                    report['artifacts'].append(self.binding(extra))
                elif mutation == 'duplicate-artifact':
                    report['artifacts'].append(report['artifacts'][0])
                elif mutation == 'missing-source-artifact':
                    report['artifacts'].remove(report['source_results'])
                elif mutation == 'extra-metadata':
                    report['uninspected_claim'] = True
                elif mutation == 'schema':
                    report['schema_version'] = 2
                elif mutation == 'screen-verified':
                    report['screen_verified'] = True
                elif mutation == 'measurement':
                    report['rows'][0]['checks'][0]['actual'] += 1
                elif mutation == 'missing-row':
                    report['rows'] = []
                reviewed.write_text(json.dumps(report))
                self.assert_reuse_rejected(reviewed)

    def test_rejected_inspection_stays_valid_but_cannot_be_relabelled(self):
        _, reviewed = self.reviewed_gate(accepted=False)
        report = json.loads(reviewed.read_text())
        self.assertEqual(report['rows'][0]['numeric_status'], 'PASS')
        self.assertEqual(report['rows'][0]['status'], 'DIFF')
        report['status'] = 'NOT VERIFIED'
        reviewed.write_text(json.dumps(report))
        self.assert_reuse_rejected(reviewed)

    def test_matching_uninspected_evidence_never_claims_calibrated(self):
        proc, report = self.run_gate()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(report['rows'][0]['numeric_status'], 'PASS')
        self.assertEqual(report['rows'][0]['status'], 'NOT VERIFIED')
        self.assertFalse(report['screen_verified'])

    def test_effective_tracking_and_field_paint_mismatch_fail_even_when_png_matches(self):
        for name, kind, mutation in (
            ('tracking', 'typography', {'typography': {**self.runtime_row['typography'], 'letter_spacing': 0.1}}),
            ('paint', 'field', {'painted_bounds': {**self.runtime_row['painted_bounds'], 'height': 24}}),
        ):
            with self.subTest(name=name):
                original = dict(self.runtime_row)
                self.plan['rows'][0]['kind'] = kind
                self.runtime_row.update(mutation)
                self.persist()
                proc, report = self.run_gate(name)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(report['rows'][0]['status'], 'DIFF')
                self.runtime_row = original

    def test_crop_cannot_change_layout_viewport_or_screenutil_scale(self):
        self.runtime_row['screenutil']['design_size'] = {'width': 100, 'height': 30}
        self.runtime_row['screenutil']['scale_height'] = 80 / 30
        self.persist()
        proc, report = self.run_gate()
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(report['rows'][0]['status'], 'DIFF')

    def test_missing_runtime_paint_and_unsupported_source_lineheight_are_not_verified(self):
        for name, kind in (('paint', 'field'), ('lineheight', 'typography')):
            with self.subTest(name=name):
                self.plan['rows'][0]['kind'] = kind
                self.runtime_row.pop('painted_bounds', None)
                self.source_row['facts']['nodes'][0]['computed']['line-height'] = 'normal'
                self.persist()
                proc, report = self.run_gate(name)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(report['rows'][0]['status'], 'NOT VERIFIED')

    def test_glow_enum_or_bounds_without_overlap_cannot_prove_composition(self):
        self.plan['rows'][0]['kind'] = 'glow'
        self.source_row['facts']['composition'] = {'visible': [{'selector': '#field', 'bounds': {'x': 10, 'y': 20, 'w': 60, 'h': 30}}]}
        self.runtime_row['glow_bounds'] = self.runtime_row['painted_bounds']
        self.runtime_row['glow_layer'] = 'over'
        self.persist()
        proc, report = self.run_gate()
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(report['rows'][0]['status'], 'NOT VERIFIED')

    def test_png_difference_uses_existing_comparator_defaults(self):
        Image.new('RGB', (200, 160), 'white').save(self.actual)
        self.runtime_row['capture'] = self.binding(self.actual)
        self.persist()
        proc, report = self.run_gate()
        self.assertEqual(proc.returncode, 1)
        compared = report['rows'][0]['comparison']
        self.assertEqual(compared['settings']['threshold'], 0.02)
        self.assertEqual(compared['settings']['shift'], 2)
        self.assertEqual(compared['overall_percent'], 100)
        self.assertFalse(compared['settings']['allow_resize'])

    def test_tampered_runtime_and_missing_dependency_inventory_are_not_verified(self):
        for name in ('binding', 'inventory'):
            with self.subTest(name=name):
                self.persist()
                if name == 'binding':
                    self.core.write_text('changed after export')
                else:
                    self.plan['inputs_complete'] = False
                    self.persist()
                proc, report = self.run_gate(name)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(report['status'], 'NOT VERIFIED')

    def test_fingerprint_hit_never_verifies_screen_and_changes_disable_reuse(self):
        proc, report = self.run_gate()
        args = [sys.executable, str(SCRIPT), 'check', '--manifest', str(self.manifest),
                '--results', str(self.root / 'attempt/results.json')]
        checked = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)
        status = json.loads(checked.stdout)
        self.assertFalse(status['screen_verified'])
        self.assertFalse(status['calibration_reusable'])
        self.core.write_text('different core')
        checked = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(checked.returncode, 1)
        self.assertFalse(json.loads(checked.stdout)['fingerprint_match'])

    def test_handwritten_status_cannot_promote_uninspected_calibration(self):
        proc, report = self.run_gate()
        report['status'] = 'CALIBRATED'
        report['rows'][0]['status'] = 'CALIBRATED'
        path = self.root / 'attempt/results.json'
        path.write_text(json.dumps(report))
        checked = subprocess.run([sys.executable, str(SCRIPT), 'check', '--manifest', str(self.manifest),
                                  '--results', str(path)], capture_output=True, text=True)
        self.assertFalse(json.loads(checked.stdout)['calibration_reusable'])

    def test_input_directory_addition_and_diff_tampering_invalidate_inspection(self):
        directory = self.root / 'fonts'
        directory.mkdir()
        (directory / 'font.bin').write_bytes(b'font')
        self.plan['source_inputs'].append('fonts')
        self.persist()
        exported = json.loads(self.source_export.read_text())
        exported['bindings'].append(self.binding(directory / 'font.bin'))
        self.source_export.write_text(json.dumps(exported))
        proc, report = self.run_gate()
        inspection = self.root / 'inspection.json'
        inspection.write_text(json.dumps({'fingerprint': report['fingerprint'], 'results_sha256': digest(self.root / 'attempt/results.json'),
                                         'inspector': 'synthetic regression',
                                         'notes': 'Synthetic gate test, not runtime certification',
                                         'rows': {'field': {'accepted': True, 'notes': 'Synthetic PNG and probe inspected'}}}))
        args = [sys.executable, str(SCRIPT), 'finalize', '--manifest', str(self.manifest),
                '--results', str(self.root / 'attempt/results.json'), '--inspection', str(inspection),
                '--out', str(self.root / 'reviewed')]
        finalized = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(finalized.returncode, 0, finalized.stderr + finalized.stdout)
        checked = subprocess.run([sys.executable, str(SCRIPT), 'check', '--manifest', str(self.manifest),
                                  '--results', str(self.root / 'reviewed/results.json')], capture_output=True, text=True)
        self.assertTrue(json.loads(checked.stdout)['calibration_reusable'])
        (directory / 'new.bin').write_bytes(b'new')
        rejected = subprocess.run(args[:-1] + [str(self.root / 'changed')], capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)
        (directory / 'new.bin').unlink()
        Path(report['rows'][0]['comparison']['artifacts']['diff']).write_bytes(b'tampered')
        rejected = subprocess.run(args[:-1] + [str(self.root / 'tampered')], capture_output=True, text=True)
        self.assertEqual(rejected.returncode, 2)


if __name__ == '__main__':
    unittest.main()
