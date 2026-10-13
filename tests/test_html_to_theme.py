import base64
import copy
import hashlib
import importlib.util
import http.server
import io
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'plugins/flutter-knowledge/skills/set-theme-from-html'
FIXTURE = ROOT / 'tests/fixtures/html-to-theme'
SPEC = importlib.util.spec_from_file_location('import_assets', SKILL / 'scripts/import_assets.py')
IMPORTER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(IMPORTER)


def font_bytes(codepoints=(32, 65), axes=(), weight=400):
    builder = FontBuilder(1000, isTTF=True)
    glyphs = ['.notdef', *[f'g{code}' for code in codepoints]]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({code: f'g{code}' for code in codepoints})
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.lineTo((500, 700))
    pen.lineTo((900, 0))
    pen.closePath()
    builder.setupGlyf({name: pen.glyph() for name in glyphs})
    builder.setupHorizontalMetrics({name: (1000, 0) for name in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({'familyName': 'Orchard', 'styleName': 'Regular', 'uniqueFontIdentifier': 'OrchardTest',
                            'fullName': 'Orchard Regular', 'psName': 'Orchard-Regular'})
    builder.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200, usWeightClass=weight)
    builder.setupPost()
    if axes:
        builder.setupFvar(axes, [])
    builder.font['head'].created = 2082844800
    builder.font['head'].modified = 2082844800
    builder.font.recalcTimestamp = False
    stream = io.BytesIO()
    builder.save(stream)
    return stream.getvalue()


def png_bytes():
    stream = io.BytesIO()
    Image.new('RGB', (8, 5), '#496b58').save(stream, format='PNG')
    return stream.getvalue()


class AssetImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.project = self.root / 'app'
        self.project.mkdir()
        self.source = self.root / 'source with spaces'
        shutil.copytree(FIXTURE, self.source)
        (self.source / 'assets/hero.png').write_bytes(png_bytes())
        (self.source / 'assets/body.ttf').write_bytes(font_bytes())

    def asset(self, identity, kind, url, **extra):
        return {'id': identity, 'kind': kind, 'name': identity, 'url': url, **extra}

    def run_import(self, assets):
        return IMPORTER.import_manifest({'assets': assets}, self.project)

    def test_real_local_data_font_svg_imports_resolve_css_bases_and_rerun_without_duplicates(self):
        assets = [self.asset('hero', 'images', '../assets/hero.png?variant=1', base=(self.source / 'css/app.css').as_uri()),
                  self.asset('sameHero', 'images', 'data:image/png;base64,' + base64.b64encode(png_bytes()).decode()),
                  self.asset('pattern', 'icons', 'assets/pattern.svg', base=(self.source / 'index.html').as_uri()),
                  self.asset('body', 'fonts', 'assets/body.ttf', base=(self.source / 'index.html').as_uri(), text='A '),
                  self.asset('sameBody', 'fonts', 'data:font/ttf;base64,' + base64.b64encode(font_bytes()).decode(), text='A')]
        report = self.run_import(assets)
        self.assertEqual(report['errors'], 0)
        rows = report['assets']
        self.assertEqual(rows[0]['path'], rows[1]['path'])
        self.assertEqual(rows[3]['path'], rows[4]['path'])
        self.assertEqual(rows[3]['family'], 'Orchard')
        self.assertEqual(rows[2]['references'], ['#paint'])
        before = {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob('*') if path.is_file()}
        repeated = self.run_import(assets)
        self.assertTrue(all(row['status'] == 'reused' for row in repeated['assets']))
        self.assertEqual(before, {path.relative_to(self.project): path.read_bytes() for path in self.project.rglob('*') if path.is_file()})

    def test_colliding_name_preserves_unrelated_asset_and_reuses_hash_destination(self):
        folder = self.project / 'assets/images'
        folder.mkdir(parents=True)
        original = folder / 'hero.png'
        original.write_bytes(b'unrelated original')
        asset = self.asset('hero', 'images', (self.source / 'assets/hero.png').as_uri())
        imported = self.run_import([asset])['assets'][0]
        self.assertNotEqual(imported['path'], 'assets/images/hero.png')
        self.assertEqual(original.read_bytes(), b'unrelated original')
        self.assertEqual(self.run_import([asset])['assets'][0]['path'], imported['path'])

    def test_broken_resources_fonts_and_svg_dependencies_remain_explicit_errors(self):
        cases = [self.asset('missing', 'images', (self.source / 'absent.png').as_uri()),
                 self.asset('badImage', 'images', 'data:image/png;base64,YmFk'),
                 self.asset('badFont', 'fonts', 'data:font/ttf;base64,YmFk'),
                 self.asset('missingGlyph', 'fonts', (self.source / 'assets/body.ttf').as_uri(), text='ب'),
                 self.asset('svgMissing', 'icons', 'data:image/svg+xml,' + '<svg xmlns="http://www.w3.org/2000/svg"><use href="#missing"/></svg>'),
                 self.asset('svgExternal', 'icons', 'data:image/svg+xml,' + '<svg xmlns="http://www.w3.org/2000/svg"><image href="other.png"/></svg>'),
                 self.asset('relative', 'images', 'assets/hero.png'),
                 self.asset('credentials', 'images', 'https://secret:password@example.com/photo.png')]
        report = self.run_import(cases)
        self.assertEqual(report['errors'], len(cases))
        self.assertFalse(list(self.project.rglob('*')))
        self.assertNotIn('secret', json.dumps(report))
        self.assertIn('U+0628', report['assets'][3]['error'])

    def test_inline_svg_retains_defs_currentcolor_and_bytes(self):
        svg = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" style="color:#496b58"><defs><path id="shape" d="M0 0h24v24z"/></defs><use href="#shape" fill="currentColor"/></svg>'
        for name, payload in [('symbol', svg), ('symbolBom', b'\xef\xbb\xbf' + svg)]:
            with self.subTest(name=name):
                asset = self.asset(name, 'icons', 'data:image/svg+xml;base64,' + base64.b64encode(payload).decode())
                report = self.run_import([asset])
                row = report['assets'][0]
                self.assertEqual(row['status'], 'created')
                self.assertTrue(row['currentColor'])
                self.assertEqual(row['references'], ['#shape'])
                self.assertEqual((self.project / row['path']).read_bytes(), payload)

    def test_font_format_controls_do_not_hide_missing_painted_glyphs(self):
        url = (self.source / 'assets/body.ttf').as_uri()
        report = self.run_import([
            self.asset('formatControls', 'fonts', url, text='A\u200d\x85 '),
            self.asset('paintedGlyph', 'fonts', url, text='A\u25cc'),
        ])
        self.assertEqual(report['errors'], 1)
        self.assertEqual(report['assets'][0]['status'], 'created')
        self.assertEqual((self.project / report['assets'][0]['path']).read_bytes(), font_bytes())
        self.assertEqual(report['assets'][1]['status'], 'error')
        self.assertIn('U+25CC', report['assets'][1]['error'])

    def test_remote_get_imports_original_bytes_and_rejects_redirect_escape(self):
        class AssetServer(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/escape':
                    self.send_response(302)
                    self.send_header('Location', 'file:///unrelated-source.png')
                    self.end_headers()
                else:
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png')
                    self.end_headers()
                    self.wfile.write(png_bytes())

            def log_message(self, format, *args):
                pass

        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), AssetServer)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            base = f'http://127.0.0.1:{server.server_port}'
            report = self.run_import([self.asset('remote', 'images', base + '/hero.png'),
                                      self.asset('redirect', 'images', base + '/escape')])
            self.assertEqual(report['errors'], 1)
            self.assertEqual((self.project / report['assets'][0]['path']).read_bytes(), png_bytes())
            self.assertEqual(report['assets'][1]['status'], 'error')
            self.assertNotIn('unrelated-source', json.dumps(report))
        finally:
            server.shutdown()
            server.server_close()
            worker.join()

    def test_directory_symlink_cannot_write_outside_project(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.project / 'assets').symlink_to(outside, target_is_directory=True)
        report = self.run_import([self.asset('hero', 'images', (self.source / 'assets/hero.png').as_uri())])
        self.assertEqual(report['errors'], 1)
        self.assertEqual(list(outside.iterdir()), [])


class FoundationBrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chrome = os.environ.get('CHROME_EXECUTABLE') or next((str(path) for path in (
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path(shutil.which('google-chrome') or '/missing'),
            Path(shutil.which('chromium') or '/missing'),
        ) if path.is_file()), None)
        node = shutil.which('node')
        if not chrome or not node:
            raise unittest.SkipTest('Requires installed Chrome and Node; no downloads')
        env = dict(os.environ)
        if shutil.which('npm'):
            modules = subprocess.run(['npm', 'root', '-g'], check=True, capture_output=True, text=True).stdout.strip()
            env['NODE_PATH'] = os.pathsep.join(filter(None, [env.get('NODE_PATH'), modules]))
        dependency = subprocess.run([node, '-e', "require('playwright')"], env=env, capture_output=True)
        if dependency.returncode:
            raise unittest.SkipTest('Requires installed Playwright; no downloads')
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / 'source'
            shutil.copytree(FIXTURE, source)
            (source / 'assets/hero.png').write_bytes(png_bytes())
            (source / 'assets/body.ttf').write_bytes(font_bytes())
            run = subprocess.run([node, str(FIXTURE / 'browser.cjs'), chrome, (source / 'index.html').as_uri(),
                                  str(ROOT / 'plugins/flutter-knowledge/skills/html-to-widget/scripts/layout-tree.js'),
                                  str(SKILL / 'scripts/foundation-snapshot.js')],
                                 env=env, capture_output=True, text=True, timeout=60)
            if run.returncode:
                raise RuntimeError(run.stderr)
            cls.snapshots = json.loads(run.stdout)

    def test_supplied_modes_states_fonts_and_resources_are_measured_in_actual_browser(self):
        light = self.snapshots['light']
        dark = self.snapshots['dark']
        self.assertEqual(light['rootVariables']['--background'], '#f4f0e7')
        self.assertEqual(dark['rootVariables']['--background'], '#172329')
        card = next(node for node in light['nodes'] if 'card' in node['selector'] or node['tag'] == 'section')
        self.assertEqual(card['computed']['gap'], '14px')
        self.assertEqual(card['computed']['border-radius'], '18px')
        self.assertEqual(card['computed']['box-shadow'], 'rgba(36, 51, 75, 0.15) 0px 5px 13px 2px')
        selected = {node['selector']: node for node in self.snapshots['selected']['nodes']}
        self.assertEqual(selected['#save']['state']['pressed'], 'true')
        self.assertTrue(selected['#collection']['state']['focus'])
        self.assertTrue(any(node['state']['disabled'] for node in light['nodes']))
        self.assertTrue(any(face['status'] == 'loaded' and 'Orchard' in face['family'] for face in light['fonts']['faces']))
        self.assertTrue(any(resource.get('loaded') for resource in light['resources']))
        font = next(resource for resource in light['resources'] if resource['url'] == '../assets/body.ttf')
        self.assertTrue(font['base'].endswith('/css/app.css'))
        self.assertTrue(any(resource['url'].endswith('/assets/pattern.svg') or resource['url'] == '../assets/pattern.svg' for resource in dark['resources']))
        self.assertTrue(any(rule['type'] == 'CSSKeyframesRule' and '970ms' not in rule['css'] for rule in dark['rules']))
        loading = next(node for node in dark['nodes'] if 'polygon' in node['computed']['clip-path'])
        self.assertIn('0.97s', loading['computed']['animation'])
        self.assertEqual(self.snapshots['sheet']['layout']['id'], 'sheet')
        unresolved = self.snapshots['unresolved']['inlineSvg']
        self.assertIn('#outside-symbol', next(svg for svg in unresolved if svg['selector'] == '#unresolved')['unresolved'])
        self.assertTrue(next(svg for svg in light['inlineSvg'] if svg['selector'] == '#bookmark')['currentColor'])

    def test_fractional_rich_typography_effect_composition_and_icon_geometry_survive_snapshot(self):
        nodes = {node['selector']: node for node in self.snapshots['light']['nodes']}
        self.assertEqual(nodes['#legal']['computed']['font-size'], '12.25px')
        self.assertEqual(nodes['#legal']['computed']['max-width'], '237px')
        self.assertEqual(nodes['#legal-span']['computed']['font-weight'], '700')
        self.assertEqual(nodes['#legal-span']['computed']['font-style'], 'italic')
        self.assertEqual(nodes['#legal-span']['textRuns'][0]['text'], 'terms')
        self.assertEqual(nodes['#legal']['pseudo']['::before']['textRuns'][0]['text'], 'Source ')
        self.assertFalse(nodes['#legal']['pseudo']['::before']['unresolvedText'])
        self.assertEqual(nodes['#shell-glow']['relation'], 'outside')
        self.assertIn('radial-gradient', nodes['#shell-glow']['computed']['background-image'])
        ambient = nodes['#ambient']['computed']
        self.assertEqual(ambient['z-index'], '2')
        self.assertEqual(ambient['mix-blend-mode'], 'multiply')
        self.assertIn('at 25% 40%', ambient['background-image'])
        self.assertIn('inset', ambient['box-shadow'])
        action = nodes['#icon-action']
        self.assertEqual(action['computed']['padding-top'], '8.25px')
        self.assertEqual(action['computed']['min-height'], '43px')
        self.assertEqual(action['computed']['align-items'], 'center')
        self.assertGreater(action['box']['height'], 0)
        self.assertAlmostEqual(action['box']['height'] - action['content']['height'], 18.5)
        face = next(rule['face'] for rule in self.snapshots['light']['rules'] if rule.get('face'))
        self.assertEqual(face['font-weight'], '400')
        self.assertIn('body.ttf', face['src'])

    def test_inaccessible_cssom_is_disclosed_with_computed_values_retained(self):
        unavailable = self.snapshots['unavailable']
        self.assertEqual(unavailable['rootVariables']['--foreign-rule'], '1')
        self.assertTrue(any(sheet['error'] == 'SecurityError' and sheet['base'].endswith('cross.css')
                            for sheet in unavailable['unavailableSheets']))

    def test_native_values_placeholder_style_and_password_uncertainty_are_captured(self):
        snapshot = self.snapshots['controls']
        nodes = {node['selector']: node for node in snapshot['nodes']}
        for selector, text in (('#native-value', 'I'), ('#native-area', 'A'), ('#native-select', 'I')):
            with self.subTest(selector=selector):
                self.assertEqual(''.join(run['text'] for run in nodes[selector]['textRuns']), text)
        placeholder = nodes['#native-placeholder']['pseudo']['::placeholder']
        self.assertEqual(placeholder['textRuns'][0]['text'], 'I')
        self.assertEqual(placeholder['font-size'], '11px')
        self.assertEqual(placeholder['font-style'], 'italic')
        self.assertEqual(nodes['#native-value']['computed']['font-size'], '16px')
        self.assertEqual(nodes['#native-value']['computed']['line-height'], '19.2px')
        self.assertTrue(nodes['#native-password']['unresolvedText'])
        self.assertEqual(nodes['#native-password']['textRuns'], [])
        self.assertTrue(nodes['#native-css-mask']['unresolvedText'])
        self.assertEqual(nodes['#native-css-mask']['textRuns'], [])
        self.assertEqual(nodes['#native-empty-password']['pseudo']['::placeholder']['textRuns'][0]['text'], 'I')
        self.assertNotIn('private-never-export', json.dumps(snapshot))
        self.assertNotIn('value', snapshot['layout']['children'][4])

    def test_native_visible_usage_uses_owner_ancestor_clip_and_capture_bounds(self):
        nodes = {node['selector']: node for node in self.snapshots['controls']['nodes']}
        for selector in ('#native-transparent', '#native-clipped', '#native-offscreen', '#native-outside'):
            with self.subTest(selector=selector):
                self.assertNotIn(selector, nodes)
        partial = nodes['#native-partial']
        self.assertGreater(partial['visibility']['captureBounds']['w'], 0)
        self.assertLess(partial['visibility']['captureBounds']['w'], partial['box']['width'])
        self.assertTrue(partial['textVisibilityUncertain'])

    def native_font_fixture(self):
        fonts = FontRegistrationTests()
        fonts.setUp()
        self.addCleanup(fonts.doCleanups)
        fonts.snapshot = copy.deepcopy(self.snapshots['controls'])
        payload = font_bytes()
        imported = IMPORTER.import_manifest({'assets': [{'id': 'native', 'kind': 'fonts', 'name': 'native',
            'url': 'data:font/ttf;base64,' + base64.b64encode(payload).decode()}]}, fonts.project)
        self.assertEqual(imported['errors'], 0)
        fonts.imports['assets'].extend(imported['assets'])
        index = next(index for index, rule in enumerate(fonts.snapshot['rules']) if rule.get('face'))
        fonts.faces = [{'id': 'native', 'asset_id': 'native', 'rule': index,
                        'css': {'family': 'Orchard', 'weight': '400', 'style': 'normal', 'unicode_range': 'U+0-10FFFF'}}]
        fonts.write_snapshot()
        fonts.register('native', weight=400)
        fonts.use.update(profile=fonts.snapshot['profile'], source_families=['Orchard'], weight=400, axes={}, text='I')
        fonts.use['source']['selector'] = '#native-value'
        fonts.use['selection'][0]['face_id'] = 'native'
        return fonts

    def test_actual_browser_input_text_and_selected_option_require_selected_font_coverage(self):
        fonts = self.native_font_fixture()
        for selector, text, status in (('#native-value', 'I', 'NOT VERIFIED'),
                                       ('#native-area', 'A', 'PASS'), ('#native-select', 'I', 'NOT VERIFIED')):
            with self.subTest(selector=selector):
                fonts.use['text'] = text
                fonts.use['source']['selector'] = selector
                report = fonts.audit()
                self.assertEqual(report['status'], status)
                if status != 'PASS':
                    self.assertIn('U+0049', report['uses'][0]['error'])

    def test_actual_browser_masked_and_partially_clipped_text_cannot_certify_glyphs(self):
        fonts = self.native_font_fixture()
        for selector in ('#native-partial', '#native-password', '#native-css-mask'):
            with self.subTest(selector=selector):
                fonts.use['source']['selector'] = selector
                self.assertIn('rendered glyph evidence', fonts.audit()['uses'][0]['error'])
        coverage = GATE.font_usage_coverage(fonts.plan(), {'native': fonts.snapshot}, {'native': identity(fonts.snapshot_path)})
        missing = {(entry['selector'], entry['pseudo']) for entry in coverage}
        self.assertIn(('#native-placeholder', '::placeholder'), missing)
        self.assertIn(('#native-password', None), missing)
        self.assertIn(('#native-partial', None), missing)
        self.assertNotIn(('#native-transparent', None), missing)
        role = {'snapshot': 'native', 'selector': '#native-value',
                'properties': {'font-size': {'source': '16px', 'api': 'input.fontSize', 'expected': 16}}}
        with self.assertRaisesRegex(ValueError, 'omits measured typography'):
            GATE.observed_role(role, {'native': fonts.snapshot})

    def test_actual_browser_placeholder_style_binds_source_and_requires_complete_role(self):
        fonts = self.native_font_fixture()
        observed = next(node for node in fonts.snapshot['nodes'] if node['selector'] == '#native-placeholder')['pseudo']['::placeholder']
        names = GATE.required_properties(observed, observed)
        role = {'snapshot': 'native', 'selector': '#native-placeholder', 'pseudo': '::placeholder',
                'properties': {name: {'source': observed[name], 'api': 'placeholder.' + name,
                                      'expected': float(observed[name][:-2]) if observed[name].endswith('px') else
                                      float(observed[name]) if name == 'font-weight' else observed[name]} for name in names}}
        GATE.observed_role(role, {'native': fonts.snapshot})
        del role['properties']['font-style']
        with self.assertRaisesRegex(ValueError, 'font-style'):
            GATE.observed_role(role, {'native': fonts.snapshot})
        fonts.use.update(weight=500, style='italic')
        fonts.use['source'].update(selector='#native-placeholder', pseudo='::placeholder')
        with self.assertRaisesRegex(ValueError, 'source snapshot'):
            FONT_AUDIT.source_usage(fonts.project.resolve(), {**fonts.plan()['uses'][0], 'style': 'normal'})
        FONT_AUDIT.source_usage(fonts.project.resolve(), fonts.plan()['uses'][0])


FONT_SPEC = importlib.util.spec_from_file_location('audit_fonts', SKILL / 'scripts/audit_fonts.py')
FONT_AUDIT = importlib.util.module_from_spec(FONT_SPEC)
FONT_SPEC.loader.exec_module(FONT_AUDIT)
GATE_SPEC = importlib.util.spec_from_file_location('audit_handoff', SKILL / 'scripts/audit_handoff.py')
GATE = importlib.util.module_from_spec(GATE_SPEC)
GATE_SPEC.loader.exec_module(GATE)


def identity(path):
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


class FontRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.project = Path(self.temporary.name)
        self.snapshot = {'profile': {'skin': 'light', 'locale': 'en'},
                         'nodes': [{'selector': '#label', 'locale': 'en', 'textRuns': [{'text': 'AI'}],
                                    'computed': {'font-family': 'Orchard, Arabic', 'font-weight': '500', 'font-style': 'normal'}}],
                         'rules': []}
        self.imports = {'assets': []}
        self.faces = []
        self.add_face('segment', (65,), [("wght", 100, 400, 900, "Weight")])
        self.add_face('latin', (65, 73), [("wght", 100, 400, 900, "Weight")])
        self.add_face('arabic', (0x628,), family='Arabic')
        self.snapshot_path = self.project / 'snapshot.json'
        self.write_snapshot()
        self.app_fonts = self.project / 'app_fonts.dart'
        self.app_fonts.write_text("abstract final class AppFonts { static const body = 'BodyAlias'; }")
        self.consumer = self.project / 'typography.dart'
        self.consumer.write_text('final style = TextStyle(fontFamily: AppFonts.body);')
        self.use = {'id': 'label', 'profile': self.snapshot['profile'], 'locale': 'en', 'text': 'AI',
                    'source_families': ['Orchard', 'Arabic'], 'weight': 500, 'style': 'normal',
                    'alias': 'BodyAlias', 'fallback_aliases': [], 'axes': {'wght': 500},
                    'selection': [{'alias': 'BodyAlias', 'face_id': 'segment'}],
                    'app_fonts': {**identity(self.app_fonts), 'symbol': 'body'},
                    'consumer': {**identity(self.consumer), 'expression': 'AppFonts.body'},
                    'source': {**identity(self.snapshot_path), 'selector': '#label'}}
        self.register('segment')

    def add_face(self, name, codes, axes=(), family='Orchard', weight=500):
        payload = font_bytes(codes, axes, weight=weight)
        report = IMPORTER.import_manifest({'assets': [{'id': name, 'kind': 'fonts', 'name': name,
                  'url': 'data:font/ttf;base64,' + base64.b64encode(payload).decode()}]}, self.project)
        self.assertEqual(report['errors'], 0)
        self.imports['assets'].extend(report['assets'])
        css = {'family': family, 'weight': '100 900' if axes else '500', 'style': 'normal', 'unicode_range': 'U+0-10FFFF'}
        index = len(self.snapshot['rules'])
        url = 'data:font/ttf;base64,' + base64.b64encode(payload).decode()
        self.snapshot['rules'].append({'base': 'file:///source/design.html', 'face': {'src': 'url("' + url + '")', 'font-family': family, 'font-weight': css['weight'],
                                              'font-style': 'normal', 'unicode-range': css['unicode_range']}})
        self.faces.append({'id': name, 'asset_id': name, 'css': css, 'rule': index})

    def write_snapshot(self):
        self.snapshot_path = self.project / 'snapshot.json'
        self.snapshot_path.write_text(json.dumps(self.snapshot))

    def plan(self):
        faces = [{**face, 'declaration': {**identity(self.snapshot_path), 'rule': face['rule']}} for face in self.faces]
        use = {**self.use, 'source': {**self.use['source'], **identity(self.snapshot_path)}}
        return {'schema_version': 1, 'faces': faces, 'uses': [use]}

    def register(self, name, weight=None, fallback=False):
        path = next(row['path'] for row in self.imports['assets'] if row['id'] == name)
        text = f"flutter:\n  fonts:\n    - family: BodyAlias\n      fonts:\n        - asset: {path}\n"
        if weight is not None:
            text += f"          weight: {weight}\n"
        if fallback:
            path = next(row['path'] for row in self.imports['assets'] if row['id'] == 'arabic')
            text += f"    - family: ArabicAlias\n      fonts:\n        - asset: {path}\n          weight: 500\n"
        (self.project / 'pubspec.yaml').write_text(text)

    def audit(self):
        return FONT_AUDIT.audit(self.plan(), self.imports, self.project)

    def test_segmented_selected_face_missing_i_is_not_rescued_by_unused_full_latin(self):
        failed = self.audit()
        self.assertEqual(failed['status'], 'NOT VERIFIED')
        self.assertIn('U+0049', failed['uses'][0]['error'])
        self.register('latin')
        self.use['selection'][0]['face_id'] = 'latin'
        self.assertEqual(self.audit()['status'], 'PASS')
        self.faces[1]['css']['unicode_range'] = 'U+0041'
        self.snapshot['rules'][1]['face']['unicode-range'] = 'U+0041'
        self.write_snapshot()
        self.assertIn('U+0049', self.audit()['uses'][0]['error'])

    def test_variable_registration_pin_and_requested_axis_must_cover_actual_usage(self):
        self.register('latin', weight=600)
        self.use['selection'][0]['face_id'] = 'latin'
        self.assertIn('pins a different', self.audit()['uses'][0]['error'])
        self.register('latin')
        self.assertEqual(self.audit()['status'], 'PASS')
        self.use['axes']['wdth'] = 80
        self.assertIn('wdth', self.audit()['uses'][0]['error'])
        self.use['axes'] = {'wght': 500}
        self.faces[1]['css']['weight'] = '100 1000'
        self.snapshot['rules'][1]['face']['font-weight'] = '100 1000'
        self.write_snapshot()
        self.assertTrue(any('variable axes' in row['error'] for row in self.audit()['errors']))

    def test_same_original_variable_asset_multiple_weights_selects_requested_registration(self):
        self.register('latin', weight=400)
        self.use['selection'][0]['face_id'] = 'latin'
        path = self.project / 'pubspec.yaml'
        font_path = self.imports['assets'][1]['path']
        path.write_text(path.read_text() + f"        - asset: {font_path}\n          weight: 500\n")
        self.assertEqual(self.audit()['status'], 'PASS')
        self.use['weight'] = 400
        self.use['axes']['wght'] = 400
        self.snapshot['nodes'][0]['computed']['font-weight'] = '400'
        self.write_snapshot()
        self.assertEqual(self.audit()['status'], 'PASS')

    def test_css_and_pubspec_static_descriptors_can_override_original_weight_metadata(self):
        self.add_face('static', (65, 73), weight=400)
        self.write_snapshot()
        self.register('static', weight=500)
        self.use['selection'][0]['face_id'] = 'static'
        self.use['axes'] = {}
        report = self.audit()
        self.assertEqual(report['status'], 'PASS', report)
        self.assertEqual(report['uses'][0]['original_metadata'][0]['weight'], 400)
        self.faces[-1]['css']['weight'] = '400'
        self.snapshot['rules'][-1]['face']['font-weight'] = '400'
        self.write_snapshot()
        self.assertIn('synthesis is unsupported', self.audit()['uses'][0]['error'])

    def test_arabic_requires_explicit_selected_original_fallback_not_an_unused_import(self):
        self.register('latin')
        self.use['selection'][0]['face_id'] = 'latin'
        self.use.update(text='AIب', locale='ar')
        self.snapshot['nodes'][0].update(locale='ar', textRuns=[{'text': 'AIب'}])
        self.write_snapshot()
        self.assertIn('U+0628', self.audit()['uses'][0]['error'])
        self.register('latin', fallback=True)
        self.use['selection'].append({'alias': 'ArabicAlias', 'face_id': 'arabic'})
        self.use['fallback_aliases'] = ['ArabicAlias']
        self.use['fallback_bindings'] = [{'alias': 'ArabicAlias', 'symbol': 'arabic', 'expression': 'AppFonts.arabic'}]
        self.app_fonts.write_text(self.app_fonts.read_text() + " static const arabic = 'ArabicAlias';")
        self.consumer.write_text('final style = TextStyle(fontFamily: AppFonts.body, fontFamilyFallback: [AppFonts.arabic]);')
        self.use['app_fonts'] = {**identity(self.app_fonts), 'symbol': 'body'}
        self.use['consumer'] = {**identity(self.consumer), 'expression': 'AppFonts.body'}
        self.use['axes'] = {}
        self.assertEqual(self.audit()['status'], 'PASS')
        self.consumer.write_text('final style = TextStyle(fontFamily: AppFonts.body);')
        self.use['consumer'] = {**identity(self.consumer), 'expression': 'AppFonts.body'}
        self.assertIn('fallback expression', self.audit()['uses'][0]['error'])

    def test_same_alias_segment_registration_needs_bound_actual_selection_evidence(self):
        self.register('latin')
        self.use['selection'][0]['face_id'] = 'latin'
        path = self.project / 'pubspec.yaml'
        segment = self.imports['assets'][0]['path']
        path.write_text(path.read_text() + f"        - asset: {segment}\n")
        self.assertIn('ambiguous subset', self.audit()['uses'][0]['error'])
        selected = self.imports['assets'][1]
        proof = self.project / 'selection.json'
        proof.write_text(json.dumps({'selections': [{'use_id': 'label', 'alias': 'BodyAlias',
            'path': selected['path'], 'sha256': selected['sha256'], 'weight': 500,
            'style': 'normal', 'profile': self.use['profile']}]}))
        self.use['selection'][0]['selection_evidence'] = identity(proof)
        self.assertEqual(self.audit()['status'], 'PASS')
        proof.write_text('{"selections": []}')
        self.use['selection'][0]['selection_evidence'] = identity(proof)
        self.assertIn('does not identify', self.audit()['uses'][0]['error'])

    def test_actual_appfonts_and_original_asset_hash_changes_block_coverage_claim(self):
        self.register('latin')
        self.use['selection'][0]['face_id'] = 'latin'
        self.app_fonts.write_text("static const body = 'WrongAlias';")
        self.use['app_fonts'] = {**identity(self.app_fonts), 'symbol': 'body'}
        self.assertIn('does not resolve', self.audit()['uses'][0]['error'])
        font = self.project / self.imports['assets'][1]['path']
        font.write_bytes(b'changed original')
        self.assertTrue(any('changed font' in row['error'] for row in self.audit()['errors']))


class ThemeHandoffTests(unittest.TestCase):
    def setUp(self):
        from test_verification_runner import VerificationRunnerTests
        self.camera = VerificationRunnerTests()
        self.camera.setUp()
        self.addCleanup(self.camera.doCleanups)
        self.fonts = FontRegistrationTests()
        self.fonts.setUp()
        self.addCleanup(self.fonts.doCleanups)
        self.fonts.register('latin')
        self.fonts.use['selection'][0]['face_id'] = 'latin'
        self.fonts.snapshot['profile'] = self.camera.profile_data
        self.fonts.use['profile'] = self.camera.profile_data
        node = self.fonts.snapshot['nodes'][0]
        node['computed']['font-size'] = '11.5px'
        node['computed']['max-width'] = '260px'
        node['pseudo'] = {}
        self.fonts.write_snapshot()
        self.camera.fresh_cache(facts_payload=self.fonts.snapshot_path.read_text())
        self.attempt, _, self.results = self.camera.run_attempt()
        self.inspection = self.camera.inspection(self.attempt, self.results)
        self.runtime = self.camera.root / 'runtime.json'
        self.wrapper = self.fonts.project / 'lib/core/widgets/app_text.dart'
        self.wrapper.parent.mkdir(parents=True)
        self.wrapper.write_text('class AppText extends StatelessWidget { final style = tokens.text.legal; }')
        self.consumer = {'file': 'lib/core/widgets/app_text.dart', 'symbol': 'AppText'}
        self.properties = {'font-size': {'source': '11.5px', 'api': 'tokens.text.legal.fontSize', 'expected': 11.5},
                           'max-width': {'source': '260px', 'api': 'tokens.space.legalWidth', 'expected': 260},
                           'font-family': {'source': 'Orchard, Arabic', 'api': 'tokens.text.legal.fontFamily', 'expected': 'BodyAlias'},
                           'font-weight': {'source': '500', 'api': 'tokens.text.legal.fontWeight', 'expected': 500},
                           'font-style': {'source': 'normal', 'api': 'tokens.text.legal.fontStyle', 'expected': 'normal'}}
        self.write_runtime()
        plan = self.camera.root / 'font-plan.json'
        imports = self.camera.root / 'imports.json'
        plan.write_text(json.dumps(self.fonts.plan()))
        imports.write_text(json.dumps(self.fonts.imports))
        self.ledger = {'schema_version': 1, 'stage': 'theme-before-feature', 'source': identity(self.camera.source),
                       'snapshots': [{**identity(self.fonts.snapshot_path), 'id': 'source'}],
                       'fonts': {'plan': identity(plan), 'imports': identity(imports)},
                       'visual': {'results': identity(self.attempt / 'results.json'), 'inspection': identity(self.inspection)},
                       'roles': [{'id': 'legal', 'snapshot': 'source', 'selector': '#label',
                                  'profile': self.camera.profile_data, 'properties': self.properties,
                                  'application': {'files': [{**identity(self.fonts.consumer), 'path': 'typography.dart'},
                                                            {**identity(self.wrapper), 'path': 'lib/core/widgets/app_text.dart'}],
                                                  'consumer': self.consumer, 'runtime': identity(self.runtime)},
                                  'visual_rows': ['login']}]}

    def write_runtime(self, size=11.5):
        properties = {name: {'api': mapping['api'], 'value': mapping['expected']}
                      for name, mapping in self.properties.items()}
        properties['font-size']['value'] = size
        self.runtime.write_text(json.dumps({'roles': [{'id': 'legal', 'profile': self.camera.profile_data,
                'consumer': self.consumer, 'properties': properties}]}))

    def audit(self):
        return GATE.audit(self.ledger, self.camera.root, self.fonts.project)

    def test_exact_runtime_role_and_actual_source_evidence_can_complete_scoped_handoff(self):
        report = self.audit()
        self.assertEqual(report['status'], 'VERIFIED', report)
        self.assertEqual(report['roles'][0]['state'], 'visually checked')
        self.write_runtime(size=11)
        self.ledger['roles'][0]['application']['runtime'] = identity(self.runtime)
        report = self.audit()
        self.assertEqual(report['status'], 'NOT VERIFIED')
        self.assertIn('font-size', report['roles'][0]['gap'])
        self.assertEqual(report['roles'][0]['state'], 'extracted')
        self.properties['font-size']['expected'] = 11
        report = self.audit()
        self.assertIn('rounded', report['roles'][0]['gap'])
        self.assertEqual(report['roles'][0]['state'], 'missing')

    def test_omitted_observed_effect_and_missing_consumer_block_false_completion(self):
        self.fonts.snapshot['nodes'].append({'selector': '#ambient', 'computed': {'background-image': 'radial-gradient(red, transparent)'}, 'pseudo': {}})
        self.fonts.write_snapshot()
        self.ledger['snapshots'][0] = {**identity(self.fonts.snapshot_path), 'id': 'source'}
        report = self.audit()
        self.assertEqual(report['status'], 'NOT VERIFIED')
        self.assertEqual(report['unassigned_nodes'][0]['selector'], '#ambient')
        self.ledger['roles'][0]['application']['consumer']['symbol'] = 'absentAmbientConsumer'
        report = self.audit()
        self.assertIn('consumer symbol', report['roles'][0]['gap'])

    def test_partial_typography_and_paint_ledger_cannot_approve_measured_role(self):
        node = self.fonts.snapshot['nodes'][0]
        additional = {'line-height': ('17.25px', 1.5), 'letter-spacing': ('0.25px', 0.25),
                      'font-feature-settings': ('"liga" 0', ['liga', 0]),
                      'box-shadow': ('rgba(0, 0, 0, 0.2) 0px 2px 8px 0px', {'blur': 8, 'dy': 2}),
                      'background-image': ('radial-gradient(red, transparent)', {'type': 'radial'}),
                      'width': ('260px', 260), 'height': ('24px', 24),
                      'opacity': ('0.5', 0.5), 'background-position': ('40% 60%', [0.4, 0.6])}
        for name, (source, expected) in additional.items():
            node['computed'][name] = source
            self.properties[name] = {'source': source, 'api': 'core.legal.' + name, 'expected': expected}
        self.properties['line-height']['conversion'] = 'line-height-ratio'
        self.fonts.write_snapshot()
        self.camera.fresh_cache(facts_payload=self.fonts.snapshot_path.read_text())
        attempt, _, results = self.camera.run_attempt()
        inspection = self.camera.inspection(attempt, results)
        self.ledger['visual'] = {'results': identity(attempt / 'results.json'), 'inspection': identity(inspection)}
        self.ledger['snapshots'][0] = {**identity(self.fonts.snapshot_path), 'id': 'source'}
        plan = Path(self.ledger['fonts']['plan']['path'])
        plan.write_text(json.dumps(self.fonts.plan()))
        self.ledger['fonts']['plan'] = identity(plan)
        self.write_runtime()
        self.ledger['roles'][0]['application']['runtime'] = identity(self.runtime)
        self.assertEqual(self.audit()['status'], 'VERIFIED')
        for name in ('font-family', 'font-style', *additional):
            with self.subTest(omitted=name):
                mapping = self.properties.pop(name)
                report = self.audit()
                self.assertEqual(report['status'], 'NOT VERIFIED')
                self.assertIn(name, report['roles'][0]['gap'])
                self.assertEqual(report['roles'][0]['state'], 'missing')
                self.properties[name] = mapping

    def test_numeric_pass_uninspected_profile_changed_and_failed_children_stay_unverified(self):
        variants = [('uninspected', lambda review: review['rows'][0].update(inspected=False)),
                    ('rejected', lambda review: review['rows'][0].update(outcome='rejected'))]
        original = json.loads(self.inspection.read_text())
        for label, change in variants:
            with self.subTest(label=label):
                review = copy.deepcopy(original)
                change(review)
                self.inspection.write_text(json.dumps(review))
                self.ledger['visual']['inspection'] = identity(self.inspection)
                self.assertEqual(self.audit()['status'], 'NOT VERIFIED')
        self.inspection.write_text(json.dumps(original))
        self.ledger['visual']['inspection'] = identity(self.inspection)
        self.ledger['roles'][0]['profile'] = {**self.camera.profile_data, 'skin': 'light'}
        self.assertEqual(self.audit()['status'], 'NOT VERIFIED')
        self.ledger['roles'][0]['profile'] = self.camera.profile_data
        self.ledger['roles'][0]['visual_rows'].append('missing-child')
        self.ledger['roles'][0]['status'] = 'VERIFIED'
        self.assertEqual(self.audit()['status'], 'NOT VERIFIED')

    def test_composite_pass_cannot_approve_an_actual_failing_child_comparison(self):
        main = copy.deepcopy(self.camera.row)
        child = copy.deepcopy(main)
        child.update(id='shadow-child', label='shadow child', reference={'path': 'white-reference.png'})
        Image.new('RGB', (32, 24), 'white').save(self.camera.root / 'white-reference.png')
        attempt, _, results = self.camera.run_attempt([main, child])
        self.assertEqual(results['rows'][0]['comparison']['status'], 'PASS')
        self.assertEqual(results['rows'][1]['comparison']['status'], 'DIFF')
        inspection = self.camera.inspection(attempt, results)
        self.ledger['visual'] = {'results': identity(attempt / 'results.json'), 'inspection': identity(inspection)}
        self.ledger['roles'][0]['visual_rows'] = ['login', 'shadow-child']
        self.ledger['roles'][0]['status'] = 'VERIFIED'
        report = self.audit()
        self.assertEqual(report['status'], 'NOT VERIFIED')
        self.assertIn('shadow-child', report['roles'][0]['gap'])

    def test_changed_artifacts_loosened_comparison_and_later_repairs_cannot_approve_frozen_stage(self):
        results = copy.deepcopy(self.results)
        results['rows'][0]['comparison']['settings']['threshold'] = 1
        path = self.attempt / 'results.json'
        path.write_text(json.dumps(results))
        inspection = self.camera.inspection(self.attempt, results)
        self.ledger['visual'] = {'results': identity(path), 'inspection': identity(inspection)}
        report = self.audit()
        self.assertEqual(report['status'], 'NOT VERIFIED')
        self.assertIn('default settings', report['roles'][0]['gap'])
        self.fonts.consumer.write_text('final repaired = TextStyle(fontFamily: AppFonts.body);')
        self.assertIn('changed evidence', self.audit()['roles'][0]['gap'])
        ledger_path = self.camera.root / 'ledger.json'
        ledger_path.write_text(json.dumps(self.ledger))
        output = self.camera.root / 'frozen-stage'
        command = ['python3', str(SKILL / 'scripts/audit_handoff.py'), '--ledger', str(ledger_path),
                   '--project', str(self.fonts.project), '--out', str(output)]
        first = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(first.returncode, 1, first.stderr)
        frozen = (output / 'audit.json').read_bytes()
        second = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)
        self.assertEqual((output / 'audit.json').read_bytes(), frozen)


if __name__ == '__main__':
    unittest.main()
