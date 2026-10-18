import re
import shutil
import subprocess
from pathlib import Path

from dart_source import scan_dart


STARTER_PACKAGES = {
    'dependencies': {'flutter', 'cupertino_icons'},
    'dev_dependencies': {'flutter_test', 'flutter_lints'},
}
BUILTINS = {'navigator', 'manual', 'none'}
SDK_PACKAGES = {'flutter_test', 'flutter_localizations'}


def source_signature(text):
    code, strings = scan_dart(text)
    return re.sub(r'\s+', '', code), [(literal.text, literal.interpolated) for literal in strings]


def render_starter(template, context):
    active, output = [True], []
    tags = re.split(r'(\{\{[^}]+\}\})', template)
    sections = []
    for part in tags:
        if not part.startswith('{{'):
            if active[-1]:
                output.append(part)
            continue
        name = part[2:-2]
        if name.startswith(('#', '^')):
            key = name[1:]
            if active[-1] and key not in context:
                return None
            enabled = bool(context.get(key))
            sections.append(key)
            active.append(active[-1] and (enabled if name[0] == '#' else not enabled))
        elif name.startswith('/'):
            if not sections or sections.pop() != name[1:]:
                return None
            active.pop()
        elif active[-1]:
            if name not in context:
                return None
            output.append(str(context[name]))
    return ''.join(output) if not sections else None


def matches_sdk_starter(path, template, context):
    if not template.is_file():
        return False
    rendered = render_starter(template.read_text(encoding='utf-8'), context)
    return rendered is not None and source_signature(path.read_text(encoding='utf-8')) == source_signature(rendered)


def starter_sources(project, pubspec, flutter):
    files = []
    for folder in ('lib', 'test'):
        directory = project / folder
        if directory.is_symlink():
            return False
        for path in directory.rglob('*'):
            if path.is_symlink():
                return False
            if path.is_file() and path.name not in {'.DS_Store', '.gitkeep'}:
                if path.suffix == '.dart' and source_signature(path.read_text(encoding='utf-8')) == ('', []):
                    continue
                files.append(path.relative_to(project).as_posix())
    if not files:
        return True
    if not set(files).issubset({'lib/main.dart', 'test/widget_test.dart'}):
        return False
    if not flutter:
        raise ValueError('Flutter is required to inspect starter templates and resolve packages; config was saved')
    templates = Path(flutter).resolve().parents[1] / 'packages/flutter_tools/templates'
    for empty in (True, False):
        context = {'withEmptyMain': empty, 'withPluginHook': False, 'withFfi': False,
                   'withPlatformChannelPluginHook': False, 'projectName': pubspec.get('name', '')}
        expected = {'lib/main.dart': templates / 'app/lib/main.dart.tmpl',
                    'test/widget_test.dart': templates / 'app_test_widget/test/widget_test.dart.tmpl'}
        if all(matches_sdk_starter(project / name, expected[name], context) for name in files):
            return True
    return False


def empty_starter(project, pubspec, flutter):
    if (project / 'pubspec_overrides.yaml').exists() or (project / 'pubspec_overrides.yaml').is_symlink():
        return False
    if any(pubspec.get(key) for key in ('workspace', 'resolution', 'dependency_overrides')):
        return False
    for section, allowed in STARTER_PACKAGES.items():
        if set(pubspec.get(section) or {}) - allowed:
            return False
    for section in ('dependencies', 'dev_dependencies'):
        for declaration in (pubspec.get(section) or {}).values():
            if isinstance(declaration, dict) and declaration != {'sdk': 'flutter'}:
                return False
    flutter_config = pubspec.get('flutter') or {}
    if not isinstance(flutter_config, dict) or set(flutter_config) - {'uses-material-design'}:
        return False
    return starter_sources(project, pubspec, flutter)


def package_arguments(config, catalog, declared):
    arguments = {}
    for category, choice in config['packages'].items():
        if not choice or choice in BUILTINS or choice in declared or choice in arguments:
            continue
        prefix = 'dev:' if catalog[category].get('dependency_section') == 'dev_dependencies' else ''
        descriptor = '@{sdk: flutter}' if choice in SDK_PACKAGES else ''
        arguments[choice] = prefix + choice + descriptor
    return list(arguments.values())


def run_pub_add(project, command):
    try:
        completed = subprocess.run(command, cwd=project, capture_output=True, text=True, timeout=180)
    except subprocess.TimeoutExpired as error:
        raise ValueError('Flutter package setup timed out; pubspec and lockfile restored') from error
    if completed.stdout:
        print(completed.stdout, end='')
    if completed.stderr:
        print(completed.stderr, end='')
    if completed.returncode:
        raise ValueError(f'Flutter package setup failed (exit {completed.returncode}); pubspec and lockfile restored')


def bootstrap_packages(project, pubspec, config, catalog):
    declared = set(pubspec.get('dependencies') or {}) | set(pubspec.get('dev_dependencies') or {})
    arguments = package_arguments(config, catalog, declared)
    if not arguments:
        return False
    flutter = shutil.which('flutter')
    if not empty_starter(project, pubspec, flutter):
        print('Pubspec unchanged: project is not a confirmed empty Flutter starter.')
        return False
    if not flutter:
        raise ValueError('Flutter is required to resolve packages for the empty project; config was saved')
    paths = [project / 'pubspec.yaml', project / 'pubspec.lock']
    if any(path.is_symlink() for path in paths):
        raise ValueError('Package setup requires regular project pubspec/lock files, not symlinks')
    originals = {path: path.read_bytes() if path.exists() else None for path in paths}
    command = [flutter, 'pub', 'add', '--no-precompile', '--no-example', *arguments]
    succeeded = False
    try:
        run_pub_add(project, command)
        succeeded = True
    finally:
        if not succeeded:
            for path, original in originals.items():
                if original is None:
                    path.unlink(missing_ok=True)
                else:
                    path.write_bytes(original)
    print('Empty starter dependencies resolved and added to pubspec.yaml.')
    return True
