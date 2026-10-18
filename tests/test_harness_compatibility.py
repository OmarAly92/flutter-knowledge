import json
import os
import shlex
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / 'plugins/flutter-knowledge'
SKILLS = PLUGIN / 'skills'
NODE = shutil.which('node')


def read_json(path):
    return json.loads(path.read_text())


def skill_files(directory):
    return {path.resolve() for path in directory.glob('*/SKILL.md')}


def map_body():
    return (SKILLS / 'flutter-knowledge/SKILL.md').read_text().split('---', 2)[2].strip()


class HarnessDiscoveryTests(unittest.TestCase):
    def test_skill_catalog_has_names_descriptions_and_implicit_invocation(self):
        files = skill_files(SKILLS)
        self.assertEqual(len(files), 22)
        for path in sorted(files):
            with self.subTest(skill=path.parent.name):
                text = path.read_text()
                self.assertTrue(text.startswith('---\n'))
                fields = dict(line.split(':', 1) for line in text.split('---', 2)[1].splitlines() if ':' in line)
                self.assertEqual(fields['name'].strip(), path.parent.name)
                self.assertTrue(fields['description'].strip())
                self.assertNotIn(fields.get('disable-model-invocation', '').strip().lower(), ('true', 'yes', 'on'))

    def test_marketplaces_and_manifests_resolve_the_shared_catalog(self):
        claude = read_json(ROOT / '.claude-plugin/marketplace.json')['plugins']
        codex = read_json(ROOT / '.agents/plugins/marketplace.json')['plugins']
        claude_entry, = [entry for entry in claude if entry['name'] == 'flutter-knowledge']
        codex_entry, = [entry for entry in codex if entry['name'] == 'flutter-knowledge']
        claude_root = ROOT / claude_entry['source']
        codex_root = ROOT / codex_entry['source']['path']
        self.assertEqual(codex_entry['source']['source'], 'local')
        manifests = [
            ('Claude Code', claude_root, claude_root / '.claude-plugin/plugin.json', './skills'),
            ('Codex', codex_root, codex_root / '.codex-plugin/plugin.json', None),
            ('Cursor', ROOT, ROOT / '.cursor-plugin/plugin.json', None),
            ('Kimi', ROOT, ROOT / '.kimi-plugin/plugin.json', None),
        ]
        for harness, base, manifest_path, implicit_path in manifests:
            with self.subTest(harness=harness):
                manifest = read_json(manifest_path)
                self.assertEqual(manifest['name'], 'flutter-knowledge')
                directory = base / (implicit_path or manifest['skills'])
                self.assertEqual(directory.resolve(), SKILLS.resolve())
                self.assertEqual(skill_files(directory), skill_files(SKILLS))

    def test_gemini_context_includes_every_skill_and_existing_references(self):
        manifest = read_json(ROOT / 'gemini-extension.json')
        context = ROOT / manifest['contextFileName']
        includes = [ROOT / line[1:] for line in context.read_text().splitlines() if line.startswith('@')]
        self.assertTrue(includes)
        self.assertTrue(all(path.is_file() for path in includes))
        skills = [path.resolve() for path in includes if path.name == 'SKILL.md']
        self.assertEqual(len(skills), len(set(skills)))
        self.assertEqual(set(skills), skill_files(SKILLS))

    def test_pi_package_and_opencode_entry_points_exist(self):
        package = read_json(ROOT / 'package.json')
        self.assertEqual(package['type'], 'module')
        self.assertTrue((ROOT / package['main']).is_file())
        self.assertEqual((ROOT / package['main']).resolve(), (ROOT / '.opencode/plugins/flutter-knowledge.js').resolve())
        extensions = [ROOT / item for item in package['pi']['extensions']]
        self.assertIn((ROOT / '.pi/extensions/flutter-knowledge.ts').resolve(), [path.resolve() for path in extensions])
        self.assertTrue(all(path.is_file() for path in extensions))
        registered = set().union(*(skill_files(ROOT / item) for item in package['pi']['skills']))
        self.assertEqual(registered, skill_files(SKILLS))

    @unittest.skipUnless(shutil.which('bash'), 'bash unavailable: installer execution skipped')
    def test_installer_links_the_catalog_in_an_isolated_target_and_is_repeatable(self):
        with tempfile.TemporaryDirectory(prefix='harness-install-') as temp:
            target = Path(temp) / 'agent skills'
            env = {**os.environ, 'CLAUDE_SKILLS_DIR': str(target)}
            for attempt in range(2):
                with self.subTest(attempt=attempt):
                    result = subprocess.run(['bash', str(ROOT / 'install.sh')], env=env, text=True, capture_output=True, timeout=20)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual({path.name for path in target.iterdir()}, {path.parent.name for path in skill_files(SKILLS)})
                    for link in target.iterdir():
                        self.assertTrue(link.is_symlink())
                        self.assertEqual(link.resolve(), (SKILLS / link.name).resolve())


@unittest.skipUnless(NODE, 'Node unavailable: hook/module execution skipped; static discovery checks remain')
class HarnessRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='harness-runtime-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.flutter = self.root / 'flutter'
        self.nested = self.flutter / 'lib/feature/login'
        self.nested.mkdir(parents=True)
        (self.flutter / 'pubspec.yaml').write_text('name: compatibility_fixture\n')
        self.plain = self.root / 'plain'
        self.plain.mkdir()

    def node_json(self, script, *args, flags=()):
        result = subprocess.run([NODE, *flags, '--input-type=module', '-e', script, *map(str, args)],
                                cwd=self.plain, text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def assert_registered_catalog(self, paths):
        registered = set().union(*(skill_files(Path(path)) for path in paths))
        self.assertEqual(registered, skill_files(SKILLS))

    def test_declared_session_hooks_inject_nested_flutter_and_silence_other_projects(self):
        hooks = {
            'Claude Code': read_json(PLUGIN / 'hooks/hooks.json')['hooks'],
            'Codex': read_json(PLUGIN / '.codex-plugin/plugin.json')['hooks'],
        }
        scenarios = [
            ('nested input cwd', json.dumps({'cwd': str(self.nested)}), self.plain, True),
            ('non-Flutter input cwd', json.dumps({'cwd': str(self.plain)}), self.nested, False),
            ('malformed fallback', '{broken', self.nested, True),
            ('empty non-Flutter fallback', '', self.plain, False),
        ]
        for harness, events in hooks.items():
            commands = [hook['command'] for group in events['SessionStart'] for hook in group['hooks'] if hook['type'] == 'command']
            self.assertTrue(commands)
            for command in commands:
                expanded = command.replace('${CLAUDE_PLUGIN_ROOT}', str(PLUGIN)).replace('${PLUGIN_ROOT}', str(PLUGIN))
                argv = shlex.split(expanded)
                self.assertEqual(argv[0], 'node')
                for scenario, payload, cwd, inject in scenarios:
                    with self.subTest(harness=harness, scenario=scenario):
                        result = subprocess.run([NODE, *argv[1:]], input=payload, cwd=cwd,
                                                text=True, capture_output=True, timeout=20)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(result.stderr, '')
                        if inject:
                            output = json.loads(result.stdout)['hookSpecificOutput']
                            self.assertEqual(output['hookEventName'], 'SessionStart')
                            self.assertTrue(output['additionalContext'].endswith(map_body()))
                        else:
                            self.assertEqual(result.stdout, '')

    def test_opencode_registers_once_preserves_config_and_injects_only_flutter(self):
        script = '''
const { FlutterKnowledgePlugin } = await import(process.argv[1]);
const results = [];
for (const ctx of [{directory: process.argv[2]}, {worktree: process.argv[2]}, {directory: process.argv[3]}]) {
  const hooks = await FlutterKnowledgePlugin(ctx);
  const config = {skills: {paths: ['existing-skills'], urls: ['https://example.invalid/skills']}, other: 7};
  await hooks.config(config);
  await hooks.config(config);
  const output = {system: ['host context']};
  await hooks['experimental.chat.system.transform']({}, output);
  results.push({config, output});
}
const emptyConfig = {};
await (await FlutterKnowledgePlugin({directory: process.argv[3]})).config(emptyConfig);
console.log(JSON.stringify({results, emptyConfig}));
'''
        package = read_json(ROOT / 'package.json')
        output = self.node_json(script, (ROOT / package['main']).as_uri(), self.nested, self.plain)
        for index, result in enumerate(output['results']):
            with self.subTest(context=index):
                self.assertEqual(result['config']['other'], 7)
                skills = result['config']['skills']
                self.assertEqual(skills['urls'], ['https://example.invalid/skills'])
                self.assertEqual(skills['paths'][0], 'existing-skills')
                self.assertEqual(skills['paths'].count(str(SKILLS)), 1)
                self.assert_registered_catalog(skills['paths'][1:])
                self.assertEqual(result['output']['system'], ['host context', map_body()] if index < 2 else ['host context'])
        self.assert_registered_catalog(output['emptyConfig']['skills']['paths'])

    def test_pi_native_typescript_discovers_resources_and_resets_between_sessions(self):
        extension = ROOT / '.pi/extensions/flutter-knowledge.ts'
        probe = subprocess.run([NODE, '--experimental-strip-types', '--input-type=module', '-e',
                                'await import(process.argv[1])', extension.as_uri()],
                               text=True, capture_output=True, timeout=20)
        if probe.returncode and ('bad option' in probe.stderr or 'ERR_UNKNOWN_FILE_EXTENSION' in probe.stderr):
            self.skipTest('Installed Node lacks native TypeScript stripping; Pi runtime skipped, package discovery checked separately')
        self.assertEqual(probe.returncode, 0, probe.stderr)
        script = '''
const {default: extension} = await import(process.argv[1]);
const handlers = new Map();
extension({on: (event, handler) => handlers.set(event, handler)});
const resources = await handlers.get('resources_discover')({}, {});
const sessions = [];
for (const cwd of [process.argv[3], process.argv[2], process.argv[3]]) {
  await handlers.get('session_start')({}, {cwd});
  sessions.push(await handlers.get('before_agent_start')({systemPrompt: 'host context'}, {cwd}) ?? null);
}
console.log(JSON.stringify({events: [...handlers.keys()], resources, sessions}));
'''
        output = self.node_json(script, extension.as_uri(), self.nested, self.plain, flags=('--experimental-strip-types',))
        self.assertEqual(set(output['events']), {'resources_discover', 'session_start', 'before_agent_start'})
        self.assert_registered_catalog(output['resources']['skillPaths'])
        self.assertEqual(output['sessions'], [None, {'systemPrompt': 'host context\n\n' + map_body()}, None])


if __name__ == '__main__':
    unittest.main()
