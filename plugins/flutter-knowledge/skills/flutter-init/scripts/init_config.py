import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print('Install the helper dependency: python3 -m pip install PyYAML', file=sys.stderr)
    raise SystemExit(2)

from project_discovery import add_discovery, inspect_project, observed_family_candidates, usage_evidence
from empty_project import BUILTINS, bootstrap_packages

CATALOG = Path(__file__).resolve().parents[1] / 'package-catalog.json'
PACKAGE_NAME = re.compile(r'^[a-z][a-z0-9_]*$')


class ConfigError(ValueError):
    pass


class UniqueLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            if key_node.tag == 'tag:yaml.org,2002:merge':
                continue
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise ConfigError('YAML mapping keys must be strings')
            if key in keys:
                raise ConfigError(f'Duplicate YAML key: {key}')
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def read_mapping(path):
    parsed = yaml.load(path.read_text(encoding='utf-8'), Loader=UniqueLoader)
    if not isinstance(parsed, dict):
        raise ConfigError(f'{path.name} must contain a YAML mapping')
    return parsed


def declared_packages(pubspec):
    declarations = {}
    for section in ('dependencies', 'dev_dependencies'):
        entries = pubspec.get(section, {})
        if entries is None:
            entries = {}
        if not isinstance(entries, dict):
            raise ConfigError(f'{section} must be a mapping')
        for name, constraint in entries.items():
            if not PACKAGE_NAME.fullmatch(name):
                raise ConfigError(f'Invalid dependency name: {name}')
            if constraint is not None and not isinstance(constraint, (str, dict)):
                raise ConfigError(f'Invalid dependency declaration: {name}')
            declarations[name] = section
    if 'flutter' not in (pubspec.get('dependencies') or {}):
        raise ConfigError('Expected a Flutter project with flutter in dependencies')
    return declarations


def config_choices(config, catalog):
    if type(config.get('schema_version')) is not int or config['schema_version'] != 1:
        raise ConfigError('Expected schema_version: 1')
    choices = config.get('packages', {})
    if not isinstance(choices, dict):
        raise ConfigError('packages must be a mapping')
    for category, choice in choices.items():
        if category not in catalog:
            raise ConfigError(f'Unknown package category: {category}')
        if choice == 'navigator' and category != 'routing':
            raise ConfigError(f'packages.{category} cannot use navigator')
        if choice == 'manual' and category != 'serialization':
            raise ConfigError(f'packages.{category} cannot use manual')
        if choice is not None and (not isinstance(choice, str) or not PACKAGE_NAME.fullmatch(choice)):
            raise ConfigError(f'packages.{category} must be a package name, builtin choice or null')
    return choices


def family_candidates(families, declared):
    return [next(package for package in family if package in declared)
            for family in families if any(package in declared for package in family)]


def detected_choice(category, rule, declared, selected):
    if category == 'state_testing':
        state = selected.get('state_management')
        if state is None:
            return None, []
        if state not in ('flutter_bloc', 'bloc'):
            return 'flutter_test', []
    candidates = family_candidates(rule['families'], declared)
    if not candidates:
        candidates = family_candidates(rule.get('fallback_families', []), declared)
    if len(candidates) > 1:
        return None, candidates
    return (candidates[0] if candidates else rule['default']), candidates


def resolution_for(choice, rule, declared, candidates):
    if choice is None:
        return {'source': 'ambiguous', 'declared': False, 'candidates': candidates}
    if choice in declared:
        return {'source': 'pubspec', 'declared': True, 'section': declared[choice]}
    if choice in BUILTINS:
        return {'source': 'builtin', 'declared': False}
    source = 'recommended' if choice in (rule['default'], 'flutter_test') else 'configured'
    return {'source': source, 'declared': False}


def resolve_config(existing, declared, catalog, usage):
    choices = dict(config_choices(existing, catalog))
    resolution = {}
    for category, rule in catalog.items():
        detected, candidates = detected_choice(category, rule, declared, choices)
        observed = observed_family_candidates(category, rule, declared, usage)
        if len(observed) == 1 and category != 'state_testing':
            detected = observed[0]
        if category not in choices or choices[category] is None:
            choices[category] = detected
        resolution[category] = resolution_for(choices[category], rule, declared, candidates)
        evidence = usage_evidence(choices[category], rule, usage)
        if evidence:
            resolution[category]['used_in'] = evidence
    return {**existing, 'packages': choices, 'resolution': resolution}


def findings(config, declared, catalog):
    problems = []
    for category, record in config['resolution'].items():
        if record['source'] == 'ambiguous':
            choices = ', '.join(record['candidates']) or 'resolve state_management first'
            problems.append(f'Choose packages.{category}: {choices}')
        choice = config['packages'][category]
        recognized = {package for group in catalog[category]['families'] for package in group}
        recognized.update(package for group in catalog[category].get('fallback_families', []) for package in group)
        if choice and choice not in recognized | BUILTINS and choice != 'flutter_test':
            print(f'Verify custom package guidance for {category}: {choice}')
    if config['packages']['state_testing'] == 'bloc_test' and config['packages']['state_management'] not in ('flutter_bloc', 'bloc'):
        problems.append('bloc_test requires a Bloc/Cubit state implementation; resolve state_testing')
    pending = [f'{key}={choice}' for key, choice in config['packages'].items()
               if choice and choice not in declared and choice not in BUILTINS]
    if pending:
        print('Not declared in pubspec: ' + ', '.join(pending))
    return problems


def write_config(path, config):
    rendered = yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
    if path.exists() and path.read_text(encoding='utf-8') == rendered:
        return
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(rendered)
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def run(project, check, bootstrap_empty=False):
    if check and bootstrap_empty:
        raise ConfigError('--check cannot be combined with --bootstrap-empty')
    pubspec = read_mapping(project / 'pubspec.yaml')
    declared = declared_packages(pubspec)
    usage, discovery = inspect_project(project, pubspec)
    path = project / 'flutter-knowledge.yaml'
    if path.is_symlink():
        raise ConfigError('flutter-knowledge.yaml must be a regular project file, not a symlink')
    if check and not path.exists():
        raise ConfigError('No flutter-knowledge.yaml; run flutter-init first')
    existing = read_mapping(path) if path.exists() else {'schema_version': 1, 'packages': {}}
    catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
    resolved = add_discovery(resolve_config(existing, declared, catalog, usage), discovery)
    problems = findings(resolved, declared, catalog)
    if check:
        missing = sorted(set(catalog) - set(existing.get('packages', {})))
        problems.extend(f'Missing packages.{category}; rerun flutter-init' for category in missing)
        for category, choice in existing.get('packages', {}).items():
            if choice is None and resolved['packages'].get(category) is not None:
                problems.append(f'Unresolved packages.{category}; rerun flutter-init to refresh detection')
    else:
        write_config(path, resolved)
        print(f'Config ready: {path}')
        if bootstrap_empty and not problems and bootstrap_packages(project, pubspec, resolved, catalog):
            pubspec = read_mapping(project / 'pubspec.yaml')
            declared = declared_packages(pubspec)
            usage, discovery = inspect_project(project, pubspec)
            resolved = add_discovery(resolve_config(resolved, declared, catalog, usage), discovery)
            write_config(path, resolved)
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


def main():
    parser = argparse.ArgumentParser(description='Detect Flutter package choices and write flutter-knowledge.yaml.')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--check', action='store_true', help='Validate choices without writing files')
    parser.add_argument('--bootstrap-empty', action='store_true',
                        help='Also resolve/add selected packages for a confirmed empty Flutter starter')
    args = parser.parse_args()
    try:
        return run(args.project.resolve(), args.check, args.bootstrap_empty)
    except (ValueError, OSError, UnicodeError, yaml.YAMLError, json.JSONDecodeError) as error:
        print(f'error: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
