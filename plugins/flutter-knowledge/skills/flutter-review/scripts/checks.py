import re
import sys
from pathlib import Path, PurePosixPath

SKILLS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SKILLS / 'flutter-init/scripts'))
sys.path.insert(0, str(SKILLS / 'flutter-app-theme/scripts'))
from dart_source import authored_dart, scan_dart
from token_audit import audit_text


def finding(rule, severity, message, path=None, line=None):
    entry = {'rule': rule, 'severity': severity, 'message': message}
    if path is not None:
        entry['path'] = path
    if line is not None:
        entry['line'] = line
    return entry


def has_tokens(project):
    if (project / 'lib/core/theme/app_tokens.dart').is_file():
        return True
    for path in (project / 'lib').rglob('*.dart'):
        if authored_dart(path):
            code, _ = scan_dart(path.read_text(encoding='utf-8'))
            if re.search(r'\bclass\s+AppTokens\b', code):
                return True
    return False


def print_findings(relative, code):
    if relative.startswith('test/'):
        return []
    hits = []
    for match in re.finditer(r'(?<![\w.])(?:print|debugPrint)\s*\(', code):
        rule = 'debug_print' if match[0].startswith('debug') else 'print'
        severity = 'review' if rule == 'debug_print' else 'blocking'
        hits.append(finding(rule, severity, 'Use the configured logger in production code.', relative,
                            code.count('\n', 0, match.start()) + 1))
    return hits


def token_findings(relative, text, tokens):
    if '/presentation/' not in relative and not relative.startswith('lib/core/widgets/'):
        return []
    hits = []
    for line, snippet in audit_text(text):
        definite = re.match(r'(?:Color|Colors\.|EdgeInsets|BorderRadius|Radius|VerticalSpace|HorizontalSpace|TextStyle|Theme\.of)', snippet)
        severity = 'blocking' if tokens and definite else 'review'
        hits.append(finding('token', severity, 'Check the theme-token contract: ' + snippet, relative, line))
    return hits


def metadata_list(mapping, key, label):
    entries = mapping.get(key)
    if entries is None:
        entries = []
    if not isinstance(entries, list):
        raise ValueError(f'{label} must be a list')
    return entries


def declared_assets(pubspec):
    flutter = pubspec.get('flutter')
    if flutter is None:
        flutter = {}
    if not isinstance(flutter, dict):
        raise ValueError('pubspec flutter section must be a mapping')
    declarations = []
    for entry in metadata_list(flutter, 'assets', 'flutter.assets'):
        path = entry if isinstance(entry, str) else entry.get('path') if isinstance(entry, dict) else None
        if not isinstance(path, str):
            raise ValueError('Each flutter.assets entry must have a path')
        declarations.append(path)
    for family in metadata_list(flutter, 'fonts', 'flutter.fonts'):
        if not isinstance(family, dict):
            raise ValueError('Each font family must be a mapping')
        for font in metadata_list(family, 'fonts', 'font-family fonts'):
            if not isinstance(font, dict) or not isinstance(font.get('asset'), str):
                raise ValueError('Each font must declare an asset path')
            declarations.append(font['asset'])
    return declarations


def asset_exists(project, literal):
    path = project / literal
    if path.is_file():
        return True
    if not path.parent.is_dir():
        return False
    return any(re.fullmatch(r'\d+(?:\.\d+)?x', variant.name) and (variant / path.name).is_file()
               for variant in path.parent.iterdir() if variant.is_dir())


def asset_declared(literal, declarations):
    parent = str(PurePosixPath(literal).parent)
    variant = re.fullmatch(r'\d+(?:\.\d+)?x', PurePosixPath(parent).name)
    directory = str(PurePosixPath(parent).parent) if variant else parent
    return any(literal == declaration or (declaration.endswith('/') and directory == declaration.rstrip('/'))
               for declaration in declarations)


def asset_findings(project, relative, text, strings, declarations):
    if relative.startswith('test/'):
        return []
    hits = []
    for literal in strings:
        if not literal.text.startswith('assets/'):
            continue
        line = text.count('\n', 0, literal.start) + 1
        directory_constant = ((project / literal.text).is_dir() and
                              re.search(r'\bconst\s+(?:String\s+)?[A-Za-z_]\w*\s*=\s*$', text[max(0, literal.start - 160):literal.start]))
        if literal.text.endswith('/') or directory_constant:
            hits.append(finding('asset_prefix', 'review', 'Resolve composed asset paths from this directory prefix.', relative, line))
        elif literal.interpolated or '\\' in literal.text:
            hits.append(finding('asset_dynamic', 'review', 'Resolve dynamic asset paths against real assets and declarations.', relative, line))
        elif not asset_exists(project, literal.text):
            hits.append(finding('asset_missing', 'blocking', 'Missing literal asset: ' + literal.text, relative, line))
        elif not asset_declared(literal.text, declarations):
            hits.append(finding('asset_undeclared', 'blocking', 'Asset is not declared in pubspec: ' + literal.text, relative, line))
    return hits


def duplicate_widgets(project, scope):
    owners = {}
    for path in (project / 'lib').rglob('*.dart'):
        if authored_dart(path):
            code, _ = scan_dart(path.read_text(encoding='utf-8'))
            for name in re.findall(r'\bclass\s+(\w+)\s+extends\s+\w*Widget\b', code):
                owners.setdefault(name, []).append(path.relative_to(project).as_posix())
    return [finding('duplicate_widget', 'review', f'Review duplicate widget {name}: ' + ', '.join(paths))
            for name, paths in owners.items() if len(paths) > 1 and any(path in scope for path in paths)]


def inspect_scope(project, scope, pubspec):
    tokens = has_tokens(project)
    assets = declared_assets(pubspec)
    hits = []
    for relative in scope:
        text = (project / relative).read_text(encoding='utf-8')
        code, strings = scan_dart(text)
        hits.extend(print_findings(relative, code))
        hits.extend(token_findings(relative, text, tokens))
        hits.extend(asset_findings(project, relative, text, strings, assets))
    hits.extend(duplicate_widgets(project, scope))
    return hits
