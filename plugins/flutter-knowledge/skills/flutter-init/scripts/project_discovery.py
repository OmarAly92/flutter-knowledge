import re
from pathlib import PurePosixPath

from dart_source import project_sources

CONTRACTS = {
    'api': r'\bclass\s+ApiConsumer\b',
    'response': r'\bclass\s+GlobalResponse\b',
    'result': r'\b(?:class\s+Result|typedef\s+FutureResult)\b',
    'failure': r'\bclass\s+Failure\b',
    'theme': r'\bclass\s+AppTokens\b',
    'typography': r'\bclass\s+(?:AppTypography|AppTextStyle)\b',
    'router': r'\bclass\s+AppRouter\b',
    'assets': r'\bclass\s+(?:AppAsset|AppAssets)\b',
    'cache': r'\bclass\s+CacheHelper\b',
    'secure_cache': r'\bclass\s+SecureCacheHelper\b',
}


STATE_MARKERS = {
    'flutter_bloc': r'\bextends\s+(?:Cubit|Bloc)\b',
    'riverpod': r'\b(?:NotifierProvider|AsyncNotifierProvider|StateNotifierProvider|FutureProvider|StreamProvider|StateProvider|ProviderContainer)\b|\bextends\s+(?:AutoDispose)?(?:Async)?Notifier\b|\bextends\s+StateNotifier\b|@(?:riverpod|Riverpod)\b',
    'provider': r'\b(?:ChangeNotifierProvider|ListenableProvider|MultiProvider|Selector)\s*[<(]',
    'get': r'\b(?:GetxController|GetBuilder|Obx)\b',
    'mobx': r'\b(?:Store|Observable|Observer)\b|@(?:observable|action)\b',
    'signals': r'\b(?:signal|computed|Watch)\s*[<(]',
}


def imported_packages(code, strings):
    imports = []
    for literal in strings:
        if not re.search(r'\b(?:import|export)\s*$', code[:literal.start]):
            continue
        package = re.match(r'^package:([a-z][a-z0-9_]*)/', literal.text)
        if package:
            imports.append(package[1])
    return imports


def widget_location(relative):
    parts = PurePosixPath(relative).parts
    for folder in ('widgets', 'components'):
        if folder in parts:
            return '/'.join(parts[:parts.index(folder) + 1])
    return None


def asset_locations(pubspec):
    flutter = pubspec.get('flutter') or {}
    if not isinstance(flutter, dict):
        return []
    entries = flutter.get('assets') or []
    if not isinstance(entries, list):
        return []
    paths = [entry if isinstance(entry, str) else entry.get('path')
             for entry in entries if isinstance(entry, (str, dict))]
    return sorted({path for path in paths if isinstance(path, str)})


def inspect_project(project, pubspec):
    usage, state_usage, contracts, widgets = {}, {}, {key: [] for key in CONTRACTS}, set()
    suffixes, prefixes, import_styles = {'Screen': 0, 'Page': 0}, {'App': 0, 'other': 0}, {'package': 0, 'relative': 0}
    for relative, code, strings in project_sources(project):
        for package in imported_packages(code, strings):
            usage.setdefault(package, set()).add(relative)
        for key, pattern in CONTRACTS.items():
            if re.search(pattern, code):
                contracts[key].append(relative)
        for backend, pattern in STATE_MARKERS.items():
            if re.search(pattern, code):
                state_usage.setdefault(backend, []).append(relative)
        location = widget_location(relative)
        if location:
            widgets.add(location)
        for name in re.findall(r'\bclass\s+(\w+)\s+extends\s+\w*Widget\b', code):
            prefixes['App' if name.startswith('App') else 'other'] += 1
            for suffix in suffixes:
                suffixes[suffix] += name.endswith(suffix)
        for literal in strings:
            if re.search(r'\bimport\s*$', code[:literal.start]):
                import_styles['package' if literal.text.startswith('package:') else 'relative'] += 1
    metadata = {
        'shared_widget_locations': sorted(widgets),
        'contracts': {key: paths for key, paths in contracts.items() if paths},
        'routed_widget_suffixes': suffixes,
        'widget_prefix_counts': prefixes,
        'import_style_counts': import_styles,
        'assets': asset_locations(pubspec),
        'state_backend_evidence': state_usage,
    }
    return {'imports': {package: sorted(paths) for package, paths in usage.items()}, 'state': state_usage}, metadata


def observed_family_candidates(category, rule, declared, usage):
    families = rule['families']
    if not any(package in declared for family in families for package in family):
        families = rule.get('fallback_families', [])
    candidates = []
    imports = usage['imports']
    for family in families:
        observed = any(package in imports for package in family)
        if category == 'state_management':
            observed = observed and any(package in usage['state'] for package in family)
        if any(package in declared for package in family) and observed:
            candidates.append(next(package for package in family if package in declared))
    return candidates


def usage_evidence(choice, rule, usage):
    family = next((family for family in rule['families'] + rule.get('fallback_families', []) if choice in family), [])
    return sorted({path for package in family for path in usage['imports'].get(package, [])})


def add_discovery(config, metadata):
    existing = config.get('project_contracts', {})
    if not isinstance(existing, dict):
        raise ValueError('project_contracts must be a mapping')
    contracts = dict(existing)
    for key, paths in metadata['contracts'].items():
        if len(paths) == 1:
            contracts.setdefault(key, paths[0])
    merged = {**config, 'discovery': metadata}
    if contracts:
        merged['project_contracts'] = contracts
    return merged
