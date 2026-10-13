import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/layout-tree'
SCRIPT = ROOT / 'plugins/flutter-knowledge/skills/html-to-widget/scripts/layout-tree.js'


class LayoutTreeBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        node = shutil.which('node')
        chrome = os.environ.get('CHROME_EXECUTABLE') or next((str(path) for path in (
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path(shutil.which('google-chrome') or '/missing'),
            Path(shutil.which('chromium') or '/missing'),
        ) if path.is_file()), None)
        if not node or not chrome:
            raise unittest.SkipTest('Requires installed Node and Chrome; no browser is downloaded')
        env = dict(os.environ)
        if shutil.which('npm'):
            modules = subprocess.run(['npm', 'root', '-g'], capture_output=True, text=True, check=True).stdout.strip()
            env['NODE_PATH'] = os.pathsep.join(filter(None, [env.get('NODE_PATH'), modules]))
        dependency = subprocess.run([node, '-e', "require('playwright')"], env=env, capture_output=True, text=True)
        if dependency.returncode:
            raise unittest.SkipTest('Requires installed Playwright Node package; no package is installed')
        result = subprocess.run([node, str(FIXTURES / 'browser.cjs'), chrome,
                                 str(FIXTURES / 'composition.html'), str(SCRIPT)],
                                env=env, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr)
        cls.facts = json.loads(result.stdout)

    def composition(self, name='shell'):
        value = self.facts[name]
        self.assertIsNotNone(value, 'captureComposition must return capture and outside-screen facts')
        return value

    def test_chat_subtree_retains_legacy_geometry_and_finds_shell_handle(self):
        legacy = self.facts['legacy']
        self.assertEqual((legacy['tag'], legacy['x'], legacy['y'], legacy['w'], legacy['h']),
                         ('main', 0, 0, 360, 600))
        facts = self.composition()
        self.assertEqual(facts['screen']['tree'], legacy)
        outside = {item['selector']: item for item in facts['outsideScreen']}
        self.assertIn('#drawer-handle', outside)
        self.assertTrue(outside['#drawer-handle']['control'])
        self.assertTrue(outside['#drawer-handle']['inCapture'])
        self.assertEqual(outside['#drawer-handle']['bounds'], {'x': 12, 'y': 8, 'w': 40, 'h': 24})
        self.assertIn('#nav', outside)
        self.assertEqual(facts['capture']['selector'], '.sa-appwrap')
        self.assertEqual(facts['capture']['bounds'], {'x': 0, 'y': 0, 'w': 360, 'h': 640})
        self.assertEqual(facts['viewport']['dpr'], 2)

    def test_narrow_capture_reports_pixels_lost_above_screen_and_outside_shell(self):
        facts = self.composition('narrow')
        self.assertIn('#drawer-handle', facts['capture']['omittedSelectors'])
        self.assertTrue(facts['capture']['hasOutsideScreenOmissions'])
        self.assertIn('#external', self.composition()['capture']['omittedSelectors'])
        self.assertFalse(self.composition('viewport')['capture']['hasOutsideScreenOmissions'])

    def test_overlay_and_visibility_follow_current_browser_state(self):
        facts = self.composition()
        visible = {item['selector']: item for item in facts['visible']}
        self.assertEqual(visible['#overlay']['role'], 'dialog')
        self.assertTrue(visible['#overlay-action']['control'])
        for selector in ('#display-none', '#offscreen', '#transparent-child', '#clipped', '#hidden'):
            with self.subTest(selector=selector):
                self.assertNotIn(selector, visible)
        self.assertIn('#visibility-override', visible)
        self.assertEqual(visible['#partial']['visibleBounds']['h'], 10)
        closed = {item['selector'] for item in self.composition('closed')['visible']}
        self.assertNotIn('#overlay', closed)
        self.assertNotIn('#overlay-action', closed)

    def test_generated_decoration_is_recorded_even_when_host_has_no_box(self):
        decoration = next((item for item in self.composition()['outsideScreen']
                           if item['selector'] == '#decoration::before'), None)
        self.assertIsNotNone(decoration)
        self.assertFalse(decoration['control'])
        self.assertEqual(decoration['bounds'], {'x': 404, 'y': 70, 'w': 8, 'h': 40})
        self.assertFalse(decoration['inCapture'])
        self.assertNotIn('#invisible-decoration::before',
                         {item['selector'] for item in self.composition()['visible']})

    def test_missing_capture_boundary_fails_instead_of_extracting_other_pixels(self):
        self.assertIn('nothing matches #missing', self.facts['invalid'] or '')

    def test_paint_containment_and_fixed_containing_blocks_clip_visible_composition(self):
        visible = {item['selector'] for item in self.composition()['visible']}
        self.assertNotIn('#paint-clipped', visible)
        self.assertNotIn('#fixed-clipped', visible)
        self.assertIn('#fixed-escape', visible)

    def test_nonfixed_decoration_is_reported_for_manual_geometry_inspection(self):
        unresolved = {item['selector']: item for item in self.composition()['unresolvedDecorations']}
        self.assertEqual(unresolved['#unresolved-decoration::after']['geometry'], 'unresolved')
        self.assertEqual(unresolved['#unresolved-decoration::after']['relation'], 'outside')


if __name__ == '__main__':
    unittest.main()
