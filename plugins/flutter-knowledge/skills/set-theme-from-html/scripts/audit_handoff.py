import argparse
import hashlib
import importlib.util
import json
import math
import re
import sys
import tempfile
from pathlib import Path


OWNER = Path(__file__).resolve().parents[2] / 'visual-verification/scripts/run_verification.py'
SPEC = importlib.util.spec_from_file_location('theme_visual_runner', OWNER)
RUNNER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RUNNER)
FONT_SPEC = importlib.util.spec_from_file_location('theme_font_audit', Path(__file__).with_name('audit_fonts.py'))
FONTS = importlib.util.module_from_spec(FONT_SPEC)
FONT_SPEC.loader.exec_module(FONTS)


def evidence(record, base):
    path = (base / record['path']).resolve()
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']:
        raise ValueError('missing/changed evidence: ' + record['path'])
    return path


def json_evidence(record, base):
    return json.loads(evidence(record, base).read_text())


def observed_role(role, snapshots):
    snapshot = snapshots[role['snapshot']]
    node = next((node for node in snapshot['nodes'] if node['selector'] == role['selector']), None)
    if node is None:
        raise ValueError('observed selector is absent from bound snapshot')
    observed = node['pseudo'][role['pseudo']] if role.get('pseudo') else node['computed']
    if not role.get('properties'):
        raise ValueError('source role has no measured properties')
    occurrence = node['pseudo'][role['pseudo']] if role.get('pseudo') else node
    if occurrence.get('unresolvedText') or (occurrence.get('textVisibilityUncertain') and occurrence.get('textRuns')):
        raise ValueError('masked/native or partially visible source text needs rendered glyph evidence')
    required = required_properties(occurrence, observed)
    missing = sorted(required - role['properties'].keys())
    if missing:
        raise ValueError('observed role omits measured typography/paint properties: ' + ', '.join(missing))
    for name, mapping in role['properties'].items():
        if name not in observed or mapping['source'] != observed[name]:
            raise ValueError('source property disagrees with bound snapshot: ' + name)
        exact_length(name, mapping, observed)
    return snapshot


def required_properties(occurrence, observed):
    required = set()
    if any(run['text'].strip() for run in occurrence.get('textRuns', [])):
        required.update({'color', 'font-family', 'font-size', 'font-weight', 'font-style',
                         'font-stretch', 'line-height', 'letter-spacing', 'font-feature-settings',
                         'font-variation-settings', 'font-optical-sizing', 'text-transform'} & observed.keys())
    effects = {name for name in ('background-image', 'box-shadow')
               if observed.get(name, 'none') != 'none'}
    if effects:
        required.update(effects)
        required.update({'width', 'height', 'border-radius', 'opacity', 'background-color',
                         'background-size', 'background-position', 'background-origin', 'background-clip',
                         'clip-path', 'overflow', 'filter', 'transform', 'transform-origin',
                         'mix-blend-mode', 'background-blend-mode', 'position', 'inset', 'z-index',
                         'isolation'} & observed.keys())
    return required



def exact_length(name, mapping, observed):
    source = mapping['source']
    expected_value = mapping.get('expected')
    if isinstance(expected_value, (int, float)) and not math.isfinite(expected_value):
        raise ValueError('runtime representation must be finite: ' + name)
    match = re.fullmatch(r'(-?[0-9]+(?:\.[0-9]+)?)px', source)
    numeric = name in {'font-size', 'width', 'height', 'min-width', 'min-height', 'max-width', 'max-height',
                       'row-gap', 'column-gap', 'letter-spacing', 'padding-top', 'padding-right',
                       'padding-bottom', 'padding-left', 'outline-offset', 'border-top-width'}
    if numeric and match and mapping.get('expected') != float(match.group(1)):
        raise ValueError('exact source length was rounded or converted without support: ' + name)
    if name == 'line-height' and match:
        size = float(observed['font-size'].removesuffix('px'))
        expected = float(match.group(1)) / size if mapping.get('conversion') == 'line-height-ratio' else float(match.group(1))
        if abs(mapping.get('expected', float('inf')) - expected) > 1e-9:
            raise ValueError('line-height conversion differs from measured source')
    if name in {'font-weight', 'opacity'} and re.fullmatch(r'[0-9]+(?:\.[0-9]+)?', source):
        if mapping.get('expected') != float(source):
            raise ValueError('numeric source property differs from intended application: ' + name)


def applied_role(role, base, project):
    application = role['application']
    for binding in application['files']:
        if not (project / binding['path']).resolve().is_relative_to(project):
            raise ValueError('application file escapes current project')
        evidence(binding, project)
    consumer = application['consumer']
    if not consumer.get('symbol') or consumer['file'] not in [entry['path'] for entry in application['files']]:
        raise ValueError('actual consumer file/symbol is not bound')
    source = (project / consumer['file']).read_text()
    if consumer['symbol'] not in source:
        raise ValueError('consumer symbol is absent from current project file')
    declaration = r'\bclass\s+' + re.escape(consumer['symbol']) + r'\s+extends\s+(StatelessWidget|StatefulWidget|CustomPainter)\b'
    if not consumer['file'].startswith('lib/core/') or not re.search(declaration, source):
        raise ValueError('consumer must be an actual core wrapper/painter; token declarations are not consumers')
    probe = json_evidence(application['runtime'], base)
    measured = next((entry for entry in probe['roles'] if entry['id'] == role['id']), None)
    if not measured or measured['consumer'] != consumer or measured['profile'] != role['profile']:
        raise ValueError('runtime role/profile/consumer evidence is missing or differs')
    for name, mapping in role['properties'].items():
        if not mapping.get('api') or 'expected' not in mapping:
            raise ValueError('source property lacks token/API or explicit Flutter conversion: ' + name)
        actual = measured['properties'].get(name)
        if not actual or actual['api'] != mapping['api'] or actual['value'] != mapping['expected']:
            raise ValueError('actual runtime property differs or is missing: ' + name)
    return application


def visual_evidence(binding, base):
    results_path = evidence(binding['results'], base)
    inspection_path = evidence(binding['inspection'], base)
    document = json.loads(results_path.read_text())
    inspection = RUNNER.validate_inspection(results_path, inspection_path, document)
    reviews = {review['id']: review for review in inspection['rows']}
    rows = {row['id']: row for row in document['rows']}
    checked = {}
    for identity, row in rows.items():
        status = RUNNER.final_status(row, reviews[identity])[0]
        if status == 'VERIFIED':
            validate_comparison(row)
        checked[identity] = {'row': row, 'status': status}
    return checked


def validate_comparison(row):
    actual = Path(row['artifacts']['actual']['path'])
    reference = Path(row['artifacts']['reference']['path'])
    if row['capture']['exit_code'] != 0 or RUNNER.dimension_error(actual, row['profile']):
        raise ValueError('capture failed or dimensions disagree with profile')
    if RUNNER.load_profile(Path(row['inputs']['profile']['path'])) != row['profile']:
        raise ValueError('visual profile differs from bound profile file')
    with tempfile.TemporaryDirectory() as temporary:
        current, command, _ = RUNNER.compare_row(actual, reference, Path(temporary) / 'diff.png')
    original = row['comparison']
    current.pop('artifacts', None)
    recorded = {key: value for key, value in original.items() if key != 'artifacts'}
    if command.returncode != 0 or current != recorded:
        raise ValueError('comparison differs at owning runner default settings')


def checked_role(role, snapshot_binding, verified, source_identity):
    snapshot, snapshot_identity = snapshot_binding
    ids = role.get('visual_rows', [])
    if not ids:
        raise ValueError('no actual-wrapper source-backed visual evidence')
    for identity in ids:
        checked = verified[identity]
        row = checked['row']
        if checked['status'] != 'VERIFIED' or row['kind'] != 'source':
            raise ValueError('visual child is failing or unavailable: ' + identity)
        if row['inputs'].get('cache_facts', {}).get('sha256') != snapshot_identity['sha256']:
            raise ValueError('source snapshot is not bound to owning capture cache facts')
        if row['inputs']['source']['sha256'] != source_identity['sha256']:
            raise ValueError('visual evidence belongs to a different original source')
        if row['profile'] != role['profile'] or snapshot['profile'] != role['profile']:
            raise ValueError('source/runtime/visual profile disagrees: ' + identity)
    return ids


def snapshot_coverage(ledger, snapshots):
    addressed = {(role['snapshot'], role['selector'], role.get('pseudo')) for role in ledger['roles']}
    exclusions = ledger.get('exclusions', [])
    for exclusion in exclusions:
        if not exclusion.get('reason'):
            raise ValueError('excluded observed node requires an explicit reason')
        addressed.add((exclusion['snapshot'], exclusion['selector'], exclusion.get('pseudo')))
    missing = []
    for identity, snapshot in snapshots.items():
        for node in snapshot['nodes']:
            for pseudo in [None, *node.get('pseudo', {})]:
                if (identity, node['selector'], pseudo) not in addressed:
                    missing.append({'snapshot': identity, 'selector': node['selector'], 'pseudo': pseudo})
    return missing



def font_usage_coverage(plan, snapshots, identities):
    addressed = {(use['source']['sha256'], use['source']['selector'], use['source'].get('pseudo')) for use in plan['uses']}
    missing = []
    for identity, snapshot in snapshots.items():
        for node in snapshot['nodes']:
            occurrences = [(None, node), *node.get('pseudo', {}).items()]
            for pseudo, observed in occurrences:
                has_text = any(run['text'].strip() for run in observed.get('textRuns', []))
                bound = (identities[identity]['sha256'], node['selector'], pseudo) in addressed
                if observed.get('unresolvedText') or (has_text and (not bound or observed.get('textVisibilityUncertain'))):
                    missing.append({'snapshot': identity, 'selector': node['selector'], 'pseudo': pseudo})
    return missing


def audit(ledger, base, project):
    base, project = base.resolve(), project.resolve()
    if ledger.get('schema_version') != 1 or not ledger.get('stage'):
        raise ValueError('ledger requires schema_version 1 and an immutable stage identity')
    evidence(ledger['source'], base)
    font_binding = ledger['fonts']
    font_plan = json_evidence(font_binding['plan'], base)
    font_report = FONTS.audit(font_plan, json_evidence(font_binding['imports'], base), project)
    if len({entry['id'] for entry in ledger['snapshots']}) != len(ledger['snapshots']):
        raise ValueError('snapshot ids must be unique')
    snapshot_identities = {entry['id']: entry for entry in ledger['snapshots']}
    snapshots = {identity: json_evidence(entry, base) for identity, entry in snapshot_identities.items()}
    missing = snapshot_coverage(ledger, snapshots)
    missing_fonts = font_usage_coverage(font_plan, snapshots, snapshot_identities)
    verified, visual_error = {}, None
    try:
        verified = visual_evidence(ledger['visual'], base)
    except (ValueError, KeyError, OSError, TypeError) as error:
        visual_error = str(error)
    rows = []
    if len({role['id'] for role in ledger['roles']}) != len(ledger['roles']):
        raise ValueError('role ids must be unique')
    for role in ledger['roles']:
        row = {'id': role['id'], 'state': 'missing'}
        try:
            snapshot = observed_role(role, snapshots)
            row['state'] = 'extracted'
            if role.get('status') in ('provisional', 'unsupported', 'unchanged', 'unverified'):
                raise ValueError(role['status'] + ': ' + role.get('reason', 'no reason recorded'))
            applied_role(role, base, project)
            row['state'] = 'applied'
            if visual_error:
                raise ValueError(visual_error)
            checked_role(role, (snapshot, snapshot_identities[role['snapshot']]), verified, ledger['source'])
            row['state'] = 'visually checked'
        except (ValueError, KeyError, OSError, TypeError, StopIteration) as error:
            row['gap'] = str(error)
        rows.append(row)
    complete = font_report['status'] == 'PASS' and not missing_fonts and rows and not missing and all(row['state'] == 'visually checked' for row in rows)
    return {'schema_version': 1, 'stage': ledger['stage'], 'roles': rows, 'unassigned_nodes': missing, 'fonts': font_report, 'unaddressed_text_runs': missing_fonts,
            'status': 'VERIFIED' if complete else 'NOT VERIFIED',
            'limitations': ['runtime probe and visual inspection are attestations; inspect their capture code and PNGs',
                            'node accounting cannot infer semantic roles or prove unvisited states were supplied']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('stage proof directory already exists; retain it and use a new attempt')
        payload = args.ledger.read_bytes()
        report = audit(json.loads(payload), args.ledger.resolve().parent, args.project.resolve())
        report['ledger_sha256'] = hashlib.sha256(payload).hexdigest()
        args.out.mkdir(parents=True)
        (args.out / 'ledger.json').write_bytes(payload)
        (args.out / 'audit.json').write_text(json.dumps(report, indent=2) + '\n')
        return 0 if report['status'] == 'VERIFIED' else 1
    except (ValueError, KeyError, OSError, TypeError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
