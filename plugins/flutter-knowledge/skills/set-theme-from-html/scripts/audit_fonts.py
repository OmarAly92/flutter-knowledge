import argparse
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

from fontTools.ttLib import TTFont, TTLibError
import yaml


def file_identity(project, record):
    path = (project / record['path']).resolve()
    if not path.is_relative_to(project) or not path.is_file():
        raise ValueError('missing or escaping project font/evidence: ' + record['path'])
    payload = path.read_bytes()
    if hashlib.sha256(payload).hexdigest() != record['sha256']:
        raise ValueError('changed font/evidence: ' + record['path'])
    return payload


def weight_range(weight):
    if weight in ('normal', None):
        return (400, 400)
    if weight == 'bold':
        return (700, 700)
    parts = str(weight).split()
    if len(parts) not in (1, 2):
        raise ValueError('invalid CSS weight/range')
    bounds = [float(part) for part in parts]
    if len(bounds) == 1:
        bounds *= 2
    if not 1 <= bounds[0] <= bounds[1] <= 1000:
        raise ValueError('invalid CSS weight/range')
    return tuple(bounds)


def unicode_ranges(declaration):
    ranges = []
    for part in declaration.split(','):
        match = re.fullmatch(r'\s*U\+([0-9A-F?]{1,6})(?:-([0-9A-F]{1,6}))?\s*', part, re.I)
        if not match:
            raise ValueError('invalid CSS unicode-range')
        start, end = match.groups()
        lower = int(start.replace('?', '0'), 16)
        upper = int(end or start.replace('?', 'F'), 16)
        if lower > upper or upper > 0x10FFFF:
            raise ValueError('invalid CSS unicode-range bounds')
        ranges.append((lower, upper))
    return ranges


def face_record(project, face, imports):
    imported = imports[face['asset_id']]
    if imported.get('kind') != 'fonts' or imported.get('status') not in ('created', 'reused'):
        raise ValueError('face requires a successful original font import')
    payload = file_identity(project, imported)
    with TTFont(io.BytesIO(payload)) as font:
        axes = {axis.axisTag: (axis.minValue, axis.maxValue) for axis in font['fvar'].axes} if 'fvar' in font else {}
        metadata = {'family': font['name'].getDebugName(1), 'style': font['name'].getDebugName(2),
                    'weight': font['OS/2'].usWeightClass if 'OS/2' in font else None,
                    'italic': bool(font['head'].macStyle & 2 or ('OS/2' in font and font['OS/2'].fsSelection & 1))}
        codes = set((font.getBestCmap() or {}).keys())
    css = face['css']
    rule = json.loads(file_identity(project, face['declaration']))['rules'][face['declaration']['rule']]
    declaration = rule['face']
    urls = re.findall(r'''url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)''', declaration['src'])
    source_url = next(part for part in urls[face.get('source_url_index', 0)] if part).strip()
    reference = urllib.parse.urljoin(rule['base'], source_url)
    if hashlib.sha256(reference.encode()).hexdigest() != imported.get('reference_sha256'):
        raise ValueError('imported font reference differs from original CSS face source')
    for key, property_name in {'family': 'font-family', 'weight': 'font-weight', 'style': 'font-style',
                               'unicode_range': 'unicode-range'}.items():
        defaults = {'weight': 'normal', 'style': 'normal', 'unicode_range': 'U+0-10FFFF'}
        expected = declaration.get(property_name) or defaults.get(key, '')
        if key == 'family':
            expected = expected.strip('\"\'')
        if css.get(key, '') != expected:
            raise ValueError('CSS face disagrees with bound source declaration: ' + key)
    bounds = weight_range(css['weight'])
    if bounds[0] != bounds[1] and ('wght' not in axes or bounds[0] < axes['wght'][0] or bounds[1] > axes['wght'][1]):
        raise ValueError('CSS weight range is unsupported by original variable axes')
    subsets = unicode_ranges(css.get('unicode_range', 'U+0-10FFFF'))
    coverage = {code for code in codes if any(low <= code <= high for low, high in subsets)}
    return {'path': imported['path'], 'css': css, 'weights': bounds, 'axes': axes,
            'coverage': coverage, 'metadata': metadata, 'sha256': imported['sha256']}


def registrations(project):
    pubspec = yaml.safe_load((project / 'pubspec.yaml').read_text())
    families = pubspec.get('flutter', {}).get('fonts', [])
    if len({family['family'] for family in families}) != len(families):
        raise ValueError('duplicate pubspec aliases are ambiguous')
    return {family['family']: family['fonts'] for family in families}


def selected_face(project, selection, use, context):
    face = context['faces'][selection['face_id']]
    alias = selection['alias']
    candidates = context['registrations'].get(alias, [])
    same_asset = [entry for entry in candidates if entry['asset'] == face['path']]
    matches = [entry for entry in same_asset if entry.get('style', 'normal') == use['style']]
    exact = [entry for entry in matches if entry.get('weight', 400) == use['weight']]
    unpinned = [entry for entry in matches if 'weight' not in entry and 'wght' in face['axes']]
    registration = next(iter(exact or unpinned or matches or same_asset), None)
    if not registration:
        raise ValueError('selected original face is absent from actual pubspec alias ' + alias)
    style = registration.get('style', 'normal')
    if style != use['style'] or face['css']['style'] != use['style']:
        raise ValueError('selected style disagrees with source usage or pubspec')
    weight = use['weight']
    if not face['weights'][0] <= weight <= face['weights'][1]:
        raise ValueError('selected face CSS weight does not cover source usage; source synthesis is unsupported')
    if 'wght' not in face['axes'] and registration.get('weight', 400) != weight:
        raise ValueError('static registration cannot claim the requested original weight')
    if 'wght' in face['axes'] and 'weight' in registration and registration['weight'] != weight:
        raise ValueError('variable registration pins a different requested weight')
    if face['css']['family'] not in use['source_families']:
        raise ValueError('selected source family is outside the observed fallback chain')
    for tag, axis in use.get('axes', {}).items():
        if tag not in face['axes'] or not face['axes'][tag][0] <= axis <= face['axes'][tag][1]:
            raise ValueError('requested variable axis is unsupported: ' + tag)
    if sum(entry.get('style', 'normal') == style and entry.get('weight', 400) == registration.get('weight', 400)
           for entry in candidates) > 1 and not selection.get('selection_evidence'):
        raise ValueError('ambiguous subset registrations require actual selection evidence')
    if selection.get('selection_evidence'):
        selected = json.loads(file_identity(project, selection['selection_evidence']))['selections']
        expected = {'use_id': use['id'], 'alias': alias, 'path': face['path'], 'sha256': face['sha256'],
                    'weight': use['weight'], 'style': use['style'], 'profile': use['profile']}
        if expected not in selected:
            raise ValueError('runtime selection evidence does not identify the selected original face/use')
    return face


def source_usage(project, use):
    snapshot = json.loads(file_identity(project, use['source']))
    node = next(entry for entry in snapshot['nodes'] if entry['selector'] == use['source']['selector'])
    if use['source'].get('pseudo'):
        generated = node['pseudo'][use['source']['pseudo']]
        if generated.get('unresolvedText'):
            raise ValueError('generated CSS text needs supported source decoding')
        node = {'computed': generated, 'textRuns': generated['textRuns'], 'locale': node['locale']}
        if generated.get('textVisibilityUncertain'):
            raise ValueError('partially visible or clipped source text needs rendered glyph evidence')
    if node.get('unresolvedText') or node.get('textVisibilityUncertain'):
        raise ValueError('masked/native or partially visible source text needs rendered glyph evidence')
    families = [family.strip().strip('\"\'') for family in node['computed']['font-family'].split(',')]
    if families != use['source_families'] or node['computed']['font-weight'] != str(use['weight']) or node['computed']['font-style'] != use['style']:
        raise ValueError('usage family/style/weight disagrees with source snapshot')
    variation = node['computed'].get('font-variation-settings', 'normal')
    declared_axes = {tag: float(axis) for tag, axis in re.findall(r'''["'](.{4})["']\s+(-?[0-9]+(?:\.[0-9]+)?)''', variation)}
    expected_axes = {'wght': use['weight'], **declared_axes}
    if any(use.get('axes', {}).get(tag) != axis for tag, axis in declared_axes.items()):
        raise ValueError('source variation axis is absent or differs in planned selection')
    if any(expected_axes.get(tag) != axis for tag, axis in use.get('axes', {}).items()):
        raise ValueError('requested variable axis disagrees with source: ' + ', '.join(use['axes']))
    if use['text'] != ''.join(run['text'] for run in node['textRuns']) or use['locale'] != node['locale'] or use['profile'] != snapshot['profile']:
        raise ValueError('visible text/locale/profile disagrees with source snapshot')
    if not use.get('locale') or not use.get('profile') or not use.get('text'):
        raise ValueError('usage requires profile, locale and visible text')


def font_consumer_bindings(project, use, context):
    app_fonts = file_identity(project, use['app_fonts']).decode()
    symbol = use['app_fonts']['symbol']
    match = re.search(r'\b' + re.escape(symbol) + r'''\s*=\s*(['"])(.*?)\1\s*;''', app_fonts)
    if not match or match.group(2) != use['alias']:
        raise ValueError('AppFonts symbol does not resolve to effective alias; complex expressions need a supported runtime export')
    consumer = file_identity(project, use['consumer']).decode()
    if use['consumer']['expression'] not in consumer:
        raise ValueError('effective font expression is absent from actual consumer')
    declared = {alias for alias in context['registrations']}
    if use['alias'] not in declared or not use['consumer']['expression'].endswith('.' + symbol):
        raise ValueError('effective alias/symbol is absent from pubspec or actual AppFonts consumer')
    fallbacks = use.get('fallback_aliases', [])
    bindings = use.get('fallback_bindings', [])
    if [binding['alias'] for binding in bindings] != fallbacks:
        raise ValueError('fallback aliases require actual AppFonts consumer bindings')
    if fallbacks:
        bracket = re.search(r'fontFamilyFallback\s*:\s*(?:const\s*)?\[([^]]*)\]', consumer)
        expressions = [part.strip() for part in bracket.group(1).split(',') if part.strip()] if bracket else []
        if expressions != [binding['expression'] for binding in bindings]:
            raise ValueError('actual consumer fallback expression differs from selected chain')
        for binding in bindings:
            constant = re.search(r'\b' + re.escape(binding['symbol']) + r'''\s*=\s*(['"])(.*?)\1\s*;''', app_fonts)
            if not constant or constant.group(2) != binding['alias'] or not binding['expression'].endswith('.' + binding['symbol']):
                raise ValueError('fallback AppFonts symbol does not resolve to selected alias')


def audit_use(project, use, context):
    source_usage(project, use)
    font_consumer_bindings(project, use, context)
    chain = use['selection']
    if not chain or chain[0]['alias'] != use['alias']:
        raise ValueError('selection must begin with actual effective alias')
    if [entry['alias'] for entry in chain[1:]] != use.get('fallback_aliases', []):
        raise ValueError('selected fallbacks disagree with actual fallback aliases')
    faces = [selected_face(project, selection, use, context) for selection in chain]
    required = {ord(char) for char in use['text'] if unicodedata.category(char) not in {'Cc', 'Cf'}}
    missing = sorted(required - set().union(*(face['coverage'] for face in faces)))
    if missing:
        raise ValueError('selected registration misses ' + ', '.join(f'U+{code:04X}' for code in missing))
    return {'id': use['id'], 'status': 'COVERED', 'selected_paths': [face['path'] for face in faces],
            'original_metadata': [{'path': face['path'], **face['metadata']} for face in faces],
            'limitations': ['cmap and CSS subset coverage only; shaping and runtime fallback need visual evidence']}


def audit(plan, imports, project):
    project = project.resolve()
    if plan.get('schema_version') != 1:
        raise ValueError('font plan schema_version must be 1')
    imported = {entry['id']: entry for entry in imports['assets']}
    faces = {}
    errors = []
    for face in plan['faces']:
        try:
            if face['id'] in faces:
                raise ValueError('duplicate face id')
            faces[face['id']] = face_record(project, face, imported)
        except (ValueError, KeyError, OSError, IndexError, StopIteration, TTLibError) as error:
            errors.append({'id': face.get('id'), 'error': str(error)})
    context = {'faces': faces, 'registrations': registrations(project)}
    if len({use['id'] for use in plan['uses']}) != len(plan['uses']):
        raise ValueError('font usage ids must be unique')
    uses = []
    for use in plan['uses']:
        try:
            uses.append(audit_use(project, use, context))
        except (ValueError, KeyError, OSError, StopIteration) as error:
            uses.append({'id': use.get('id'), 'status': 'NOT VERIFIED', 'error': str(error)})
    if not uses:
        errors.append({'error': 'no visible font usages declared'})
    return {'schema_version': 1, 'uses': uses, 'errors': errors,
            'status': 'PASS' if uses and not errors and all(row['status'] == 'COVERED' for row in uses) else 'NOT VERIFIED'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--imports', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        report = audit(json.loads(args.plan.read_text()), json.loads(args.imports.read_text()), args.project)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        return 0 if report['status'] == 'PASS' else 1
    except (ValueError, KeyError, OSError, TypeError, yaml.YAMLError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
