import json
import re
from pathlib import Path

from checks import finding
from dart_source import scan_dart


def placement_findings(relative, code):
    parts = relative.split('/')
    if len(parts) < 6 or parts[:2] != ['lib', 'feature'] or parts[3] != 'presentation':
        return []
    top = parts[4]
    if not (top.endswith('_screen') or top == 'widget'):
        return [finding('file_placement', 'review', 'presentation/ holds only <screen>_screen/ dirs and widget/ for widgets shared by screens of this feature; cross-feature widgets go in lib/core/widgets/<role>/.', relative)]
    if 'logic' not in parts:
        return []
    rest = parts[parts.index('logic') + 1:]
    if len(rest) == 1 and not rest[0].endswith(('_cubit.dart', '_state.dart')):
        return [finding('file_placement', 'review', 'logic/ holds only the cubit, its state and helpers/; move builders, formatters and constants to logic/helpers/ and data classes to data/model/.', relative)]
    if rest and rest[0] == 'helpers' and re.search(r'\bclass\s+\w+', code):
        match = re.search(r'^[ \t]+final\s+[\w<>?,. \t]+\s+\w+\s*;', code, re.MULTILINE)
        if match:
            return [finding('file_placement', 'review', 'A class with fields is an XModel in data/model/ or an XParams in data/model/params/, not a logic helper.', relative, code.count('\n', 0, match.start()) + 1)]
    return []


def source_findings(project, scope):
    hits = []
    for relative in scope:
        if not relative.startswith('lib/'):
            continue
        text = (project / relative).read_text(encoding='utf-8')
        code, strings = scan_dart(text)
        hits.extend(placement_findings(relative, code))
        if relative.endswith('_state.dart'):
            for getter in re.finditer(r'\bget\s+(?:props|hashCode)\s*(?:=>[^;]+;|\{[^}]*\})', code):
                for match in re.finditer(r'\bidentityHashCode\s*\(\s*this\s*\)', getter.group()):
                    hits.append(finding('state_identity_equality', 'blocking',
                                        'State equality must compare fields, not the state instance. Keep payload-free success variants value-equal and use operation-state transitions for repeated updates.',
                                        relative, code.count('\n', 0, getter.start() + match.start()) + 1))
        patterns = [
            ('directional_layout', r'\b(?:EdgeInsets|Alignment|Positioned|BorderRadius)\.(?:only|fromLTRB)\s*\([^;]*?\b(?:left|right|topLeft|topRight)\s*:', 'Check whether this physical coordinate should be directional; measured geometry/artwork may be intentional.'),
            ('success_payload', r'\bclass\s+\w+SuccessState\b[^{}]*\{[^{}]*\b(?:final|late|var)\s+\w+', 'Inspect this success-state field; response data belongs on the owner, with payload-free success states.'),
        ]
        if '/presentation/' in relative:
            patterns.extend([
                ('screen_provider', r'\b(?:BlocProvider|ChangeNotifierProvider|ProviderScope)(?:\s*<[^;{}]+?>)?\s*\(', 'Check provisioning ownership; screens consume route-owned state. Sharing an existing owner with .value is distinct.'),
                ('builder_effect', r'\bbuilder\s*:[^;]*\b(?:Navigator\s*\.|showDialog\s*\(|showModalBottomSheet\s*\(|showSnackBar\s*\()', 'Possible effect inside a render builder; verify callback nesting and move render-triggered effects to the Screen listener.'),
            ])
        for rule, pattern, message in patterns:
            for match in re.finditer(pattern, code):
                if rule == 'screen_provider' and not re.search(r'\bclass\s+\w+Screen\b', code):
                    continue
                if rule == 'success_payload' and re.match(r'class\s+ChangeTabSuccessState\b', match.group()):
                    continue
                hits.append(finding(rule, 'review', message, relative, code.count('\n', 0, match.start()) + 1))
        for match in re.finditer(r'\bclass\s+(\w+)\s+extends\s+(Cubit|Bloc|Notifier|AutoDisposeNotifier|ChangeNotifier)\b', code):
            name, base = match.groups()
            expected_file = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower() + '.dart'
            if not name.endswith('Cubit') or Path(relative).name != expected_file or base == 'Bloc':
                hits.append(finding('state_naming', 'review', 'Keep XCubit and x_cubit.dart naming for state owners; configured Bloc mechanics use Cubit, never event-based Bloc.', relative, code.count('\n', 0, match.start()) + 1))
            if 'await ' in code:
                hits.append(finding('async_lifecycle', 'review', 'Inspect every post-await update for disposal and stale-request protection; text scanning cannot prove control flow.', relative, code.count('\n', 0, match.start()) + 1))
        if re.search(r'\bclass\s+\w+Screen\b', code) and re.search(r'\bWidget\s+build\s*\(', code):
            if not re.search(r'\b\w+Body\s*\(', code):
                hits.append(finding('screen_body', 'review', 'Confirm a separate content-only ScreenBody; aliases or helper composition require manual inspection.', relative))
        if re.search(r'\b(?:TextEditingController|ScrollController|AnimationController|TabController)\s*\(', code):
            hits.append(finding('controller_lifecycle', 'review', 'Confirm controller ownership, prefill and cleanup; controllers must not be recreated in build.', relative))
        for literal in strings:
            if not literal.text.strip():
                continue
            prefix = code[max(0, literal.start - 160):literal.start]
            if re.search(r'\b(?:AppText|Text)\s*\(\s*$', prefix) or re.search(r'\b(?:text|labelText|hintText|tooltip|semanticLabel)\s*:\s*$', prefix):
                hits.append(finding('localized_text', 'review', 'Possible user-facing literal; use the configured localization accessor. Confirm the receiving API and whether this is a translation key.', relative, text.count('\n', 0, literal.start) + 1))
    return hits


def translation_findings(project, config, changes, all_files):
    if config['packages'].get('localization') != 'easy_localization':
        return [], 'manual: configured localization requires accessor/catalog inspection'
    paths = [project / 'assets/translations' / (locale + '.json') for locale in ('en', 'ar')]
    if not all_files and not any(path.relative_to(project).as_posix() in changes for path in paths):
        return [], 'skipped: translation catalogs unchanged'
    if not any(path.exists() for path in paths):
        return [], 'manual: default catalogs absent; inspect project localization locations'
    def keys(value, prefix=''):
        if not isinstance(value, dict):
            raise ValueError('Translation catalog must be a JSON object')
        result = set()
        for key, item in value.items():
            name = prefix + key
            result.update(keys(item, name + '.') if isinstance(item, dict) else {name})
        return result
    try:
        sets = [keys(json.loads(path.read_text(encoding='utf-8'))) for path in paths]
    except (OSError, ValueError) as error:
        return [finding('translation_keys', 'blocking', str(error), 'assets/translations')], 'failed'
    missing = sets[0] ^ sets[1]
    if missing:
        return [finding('translation_keys', 'blocking', 'English/Arabic key mismatch: ' + ', '.join(sorted(missing)), 'assets/translations')], 'failed'
    return [], 'passed: English/Arabic leaf keys match'


def package_findings(pubspec, config):
    catalog = json.loads((Path(__file__).resolve().parents[2] / 'flutter-init/package-catalog.json').read_text())
    declared = set(pubspec.get('dependencies') or {}) | set(pubspec.get('dev_dependencies') or {})
    hits = []
    for category, spec in catalog.items():
        selected = config['packages'].get(category)
        families = spec['families'] + spec.get('fallback_families', [])
        selected_family = next((set(family) for family in families if selected in family), {selected})
        other = sorted({name for family in families for name in family if name in declared and name not in selected_family})
        if other:
            hits.append(finding('package_selection', 'review', f'{category} selects {selected}; also declared: {", ".join(other)}. Inspect active imports and migration intent; do not change the selection automatically.', 'pubspec.yaml'))
    return hits
