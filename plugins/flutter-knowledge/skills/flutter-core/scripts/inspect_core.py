import argparse
import json
import re
import sys
from pathlib import Path

import yaml

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / 'flutter-init/scripts'))
from dart_source import project_sources


REQUIRED_SELECTIONS = ('state_management', 'dependency_injection', 'routing', 'http_client',
                       'localization', 'equality', 'logging', 'preferences', 'secure_storage',
                       'network_status')


def read_mapping(path):
    value = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict):
        raise ValueError(str(path) + ' must contain a mapping')
    return value


def declarations(code):
    types = re.findall(r'\b(?:class|enum|mixin|typedef|extension)\s+(\w+)', code)
    functions = re.findall(r'\b(?:void|Future\s*<[^;{}]+>)\s+(\w+)\s*\(', code)
    return set(types + functions)


def local_ui_packages(project, pubspec, responsibilities):
    dependencies = pubspec.get('dependencies') or {}
    locations = set((project / 'packages').glob('*/pubspec.yaml'))
    workspace = pubspec.get('workspace') or []
    if isinstance(workspace, list):
        for member in workspace:
            if isinstance(member, str):
                locations.update(project.glob(member.rstrip('/') + '/pubspec.yaml'))
    for declaration in dependencies.values():
        if isinstance(declaration, dict) and isinstance(declaration.get('path'), str):
            locations.add(project / declaration['path'] / 'pubspec.yaml')
    rows = []
    for path in sorted({item.resolve() for item in locations}):
        if not path.is_file():
            continue
        package = read_mapping(path)
        name = package.get('name')
        if name not in responsibilities:
            continue
        rows.append({'name': name, 'responsibility': responsibilities[name],
                     'pubspec': str(path.resolve()), 'declared': name in dependencies,
                     'declaration': dependencies.get(name),
                     'exports': [str(item.resolve()) for item in sorted((path.parent / 'lib').glob('*.dart'))],
                     'status': 'supplied_requires_api_and_integration_review'})
    return rows


def inspect(project):
    pubspec = read_mapping(project / 'pubspec.yaml')
    config_path = project / 'flutter-knowledge.yaml'
    config = read_mapping(config_path) if config_path.is_file() else {}
    packages = config.get('packages', {})
    if not isinstance(packages, dict):
        raise ValueError('packages must contain a mapping')
    if config_path.is_file() and config.get('schema_version') != 1:
        raise ValueError('Unsupported configuration schema_version')
    if any(value is not None and not isinstance(value, str) for value in packages.values()):
        raise ValueError('Package selections must be strings or null')
    custom = config.get('project_contracts', {})
    if not isinstance(custom, dict) or any(not isinstance(value, str) for value in custom.values()):
        raise ValueError('project_contracts must map contract names to paths')
    catalog = json.loads((SKILLS / 'flutter-init/package-catalog.json').read_text())
    unresolved = [key for key in REQUIRED_SELECTIONS if packages.get(key) is None]
    unknown = []
    for key, selection in packages.items():
        if key not in catalog:
            raise ValueError('Unknown package category: ' + key)
        recognized = {catalog[key]['default'], 'none'}
        for family in catalog[key]['families'] + catalog[key].get('fallback_families', []):
            recognized.update(family)
        if selection is not None and selection not in recognized:
            unknown.append(key)
    sources = {}
    for path, code, strings in project_sources(project):
        raw = (project / path).read_text(encoding='utf-8')
        literals = list(code)
        for literal in strings:
            literals[literal.start:literal.end] = raw[literal.start:literal.end]
        sources[path] = {'code': code, 'with_literals': ''.join(literals),
                         'raw': raw, 'symbols': declarations(code)}
    inventory = json.loads((Path(__file__).resolve().parents[1] / 'references/core-contracts.json').read_text())
    roles = inventory['contracts']
    rows = []
    for role in roles:
        if any(packages.get(key) not in allowed
               for key, allowed in role.get('only_when', {}).items()):
            continue
        category = role.get('category')
        selection = packages.get(category) if category else None
        mapped = custom.get(role.get('contract_key'))
        paths = [mapped] if mapped else role['paths']
        candidates = [path for path in paths if path in sources]
        if not candidates and not mapped and not role.get('fixed_path') and role['symbols']:
            candidates = [path for path, source in sources.items()
                          if set(role['symbols']).issubset(source['symbols'])]
        found = set().union(*(sources[path]['symbols'] for path in candidates)) if candidates else set()
        missing = sorted(set(role['symbols']) - found)
        checks = {name: any(re.search(pattern, sources[path]['code']) for path in candidates)
                  for name, pattern in role.get('checks', {}).items()}
        checks.update({name: any(any(sources[path]['code'][match.start():match.end()].strip()
                                    for match in re.finditer(pattern, sources[path]['with_literals']))
                                for path in candidates)
                       for name, pattern in role.get('literal_checks', {}).items()})
        if packages.get('dependency_injection') == 'get_it':
            checks.update({name: any(re.search(pattern, sources[path]['code']) for path in candidates)
                           for name, pattern in role.get('get_it_checks', {}).items()})
            checks.update({name: not any(re.search(pattern, sources[path]['code']) for path in candidates)
                           for name, pattern in role.get('get_it_absent_checks', {}).items()})
        for conditional in role.get('conditional_checks', []):
            if any(packages.get(key) not in allowed
                   for key, allowed in conditional['only_when'].items()):
                continue
            checks.update({name: any(re.search(pattern, sources[path]['code']) for path in candidates)
                           for name, pattern in conditional.get('checks', {}).items()})
            checks.update({name: not any(re.search(pattern, sources[path]['code']) for path in candidates)
                           for name, pattern in conditional.get('absent_checks', {}).items()})
        if role.get('command_block'):
            command_block = (Path(__file__).resolve().parents[1] /
                             'references/main-command-block.dart.txt').read_text().strip()
            checks['command_block'] = any(sources[path]['raw'].rstrip().endswith(command_block)
                                          for path in candidates)
            checks['no_bootstrap_file'] = not (project / 'lib/app_bootstrap.dart').exists()
        default = catalog.get(category, {}).get('default')
        if category and selection == 'none':
            status = 'selection_requires_review'
        elif category and selection is not None and selection != default:
            status = 'adaptation_requires_review'
        elif mapped:
            status = 'configured_contract_requires_review' if candidates else 'configured_path_missing'
        elif not candidates:
            status = 'missing'
        elif missing or not all(checks.values()):
            status = 'incomplete_evidence'
        elif len(candidates) > 1:
            status = 'multiple_candidates_require_review'
        else:
            status = 'evidence_present_requires_review'
        rows.append({'id': role['id'], 'status': status, 'paths': candidates,
                     'conventional_paths': role['paths'], 'configured_path': mapped,
                     'symbols_not_found': missing, 'category': category, 'selection': selection,
                     'contract_checks': checks})
    status = 'init_required' if not config else 'unresolved_selections' if unresolved else 'ready_for_inspection'
    report = {'project': str(project), 'package_name': pubspec.get('name'),
              'configuration': {'status': status, 'unresolved': unresolved,
                                'unknown_selected_packages': unknown, 'packages': packages},
              'contracts': rows, 'completion': 'inspection_only',
              'local_ui_packages': local_ui_packages(project, pubspec, inventory['local_ui_packages']),
              'startup_candidates': [path for path, source in sources.items()
                                     if 'main' in source['symbols'] or
                                     re.search(r'\brunApp\s*\(', source['code'])],
              'registration_candidates': [path for path, source in sources.items()
                                          if {'registerCoreDependencies', 'registerAppDependencies'} & source['symbols']],
              'manual_checks': ['Read actual implementations/callers and preserve existing contracts.',
                                'Verify complete registrations, startup order and selected package APIs.',
                                'Verify sensitive values use secure cache, preferences remain non-sensitive and migration preserves data.',
                                'Inspect iOS/Android configuration, permissions and entitlements; separate builds from native runtime evidence.',
                                'Verify NetworkCubit factory/provider disposal and public router entry policy where selected.',
                                'Presence is not a completeness or runtime certificate.']}
    return report, 1 if status != 'ready_for_inspection' else 0


def main():
    parser = argparse.ArgumentParser(description='Read-only evidence for Flutter core setup.')
    parser.add_argument('--project', type=Path, default=Path.cwd())
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        report, code = inspect(args.project.resolve())
    except (OSError, ValueError, yaml.YAMLError) as error:
        report, code = {'completion': 'could_not_inspect', 'error': str(error)}, 2
    if args.json:
        print(json.dumps(report, indent=2))
    elif code == 2:
        print(report['error'])
    else:
        print('Configuration: ' + report['configuration']['status'])
        for row in report['contracts']:
            print(row['id'] + ': ' + row['status'] + ' ' + ', '.join(row['paths']))
        print('Inspection only; implementations, registrations and startup require review.')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
