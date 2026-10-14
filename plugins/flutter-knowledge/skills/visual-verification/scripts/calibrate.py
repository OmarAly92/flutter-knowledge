import argparse
import copy
import hashlib
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from PIL import Image

from design_cache import file_identity, positive_number, read_json, validate_profile

DIRECTORY = Path(__file__).resolve().parent
EXTRACTOR = DIRECTORY.parent.parent / 'html-to-widget/scripts/layout-tree.js'
FOUNDATIONS = DIRECTORY.parent.parent / 'set-theme-from-html/scripts/foundation-snapshot.js'


def resolved(base, name):
    return (base / name).resolve()


def expanded_files(base, names):
    paths = set()
    for name in names:
        path = resolved(base, name)
        if path.is_dir():
            paths.update(child.resolve() for child in path.rglob('*') if child.is_file())
        else:
            paths.add(path)
    if not paths:
        raise ValueError('An empty input inventory cannot bind calibration')
    return [file_identity(path) for path in sorted(paths)]


def bound_export(base, name, required):
    path = resolved(base, name)
    export = read_json(path)
    bindings = export['bindings']
    current = [file_identity(resolved(path.parent, entry['path'])) for entry in bindings]
    declared = [{'path': str(resolved(path.parent, entry['path'])), 'sha256': entry['sha256']} for entry in bindings]
    if current != declared or any(entry not in current for entry in required):
        raise ValueError('Export does not bind every current source/probe/core/camera input: ' + str(path))
    return export, path, current


def capture_identity(export_path, row):
    declared = row['capture']
    current = file_identity(resolved(export_path.parent, declared['path']))
    if current['sha256'] != declared['sha256']:
        raise ValueError('Capture PNG changed after export')
    return current


def row_inputs(base, row, inventories):
    source, source_path, source_bindings = bound_export(base, row['source_export'], inventories['source'])
    runtime, runtime_path, runtime_bindings = bound_export(base, row['runtime_export'], inventories['runtime'])
    source_row, runtime_row = source['rows'][row['id']], runtime['rows'][row['id']]
    profile = validate_profile(row['profile'])
    if not isinstance(profile.get('runtime_adapter'), str) or profile['runtime_adapter'].strip().lower() in ('', 'unknown', 'unavailable'):
        raise ValueError('Actual runtime camera/SDK identity is required')
    for axis in ('width', 'height'):
        positive_number(profile['screenutil_design_size'][axis], 'ScreenUtil design.' + axis)
    if source_row['profile'] != profile or runtime_row['profile'] != profile:
        raise ValueError('Export profiles differ from the requested layout/crop profile')
    captures = [capture_identity(source_path, source_row), capture_identity(runtime_path, runtime_row)]
    artifacts = [file_identity(source_path), file_identity(runtime_path)] + source_bindings + runtime_bindings + captures
    return {'source': source_row, 'runtime': runtime_row, 'captures': captures, 'artifacts': artifacts}


def manifest_identity(manifest_path):
    plan = read_json(manifest_path)
    if plan['schema_version'] != 1 or plan.get('inputs_complete') is not True:
        raise ValueError('Calibration requires an inspected complete input inventory')
    base = manifest_path.parent
    inventories = {role: expanded_files(base, plan[role + '_inputs']) for role in ('source', 'runtime')}
    ids = [row['id'] for row in plan['rows']]
    if not ids or len(ids) != len(set(ids)) or any(not re.fullmatch(r'[a-z0-9._-]+', name) for name in ids):
        raise ValueError('Calibration rows need unique lowercase slug ids')
    camera = plan['capture']
    if not isinstance(camera['command'], list) or not camera['command'] or any(not isinstance(argument, str) for argument in camera['command']):
        raise ValueError('Retain the exact camera argv and complete log')
    log = resolved(base, camera['log'])
    if not log.read_text().strip():
        raise ValueError('Camera log is empty')
    artifacts = expanded_files(DIRECTORY, ['calibrate.py', 'calibration_probe.dart', 'design_cache.py', 'compare.py', str(EXTRACTOR), str(FOUNDATIONS)])
    observations = [row_inputs(base, row, inventories) for row in plan['rows']]
    artifacts += inventories['source'] + inventories['runtime'] + [file_identity(log)]
    for observation in observations:
        artifacts += observation['artifacts']
    identity = {'plan': plan, 'artifacts': sorted({entry['path']: entry for entry in artifacts}.values(), key=lambda entry: entry['path'])}
    encoded = json.dumps(identity, sort_keys=True, allow_nan=False).encode()
    return plan, observations, identity, hashlib.sha256(encoded).hexdigest()


def finite_number(number):
    if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
        raise ValueError('Missing or unsupported numeric observation')
    return number


def measurement(label, expected, actual, tolerance):
    difference = abs(finite_number(actual) - finite_number(expected))
    return {'check': label, 'expected': expected, 'actual': actual, 'tolerance': tolerance, 'pass': difference <= tolerance + 1e-9}


def rectangle_checks(label, expected, actual, tolerance):
    return [measurement(label + '.' + axis, expected[axis], actual[axis], tolerance) for axis in ('x', 'y', 'width', 'height')]


def viewport_checks(row, observed):
    profile = row['profile']
    expected = {**profile['viewport'], 'dpr': profile['dpr']}
    checks = [measurement('source viewport.' + key, number, observed['source']['facts']['viewport'][key], 0) for key, number in expected.items()]
    expected['text_scale'] = profile['text_scale']
    checks += [measurement('runtime viewport.' + key, number, observed['runtime']['viewport'][key], 0) for key, number in expected.items()]
    runtime = observed['runtime']
    if runtime['skin'] != profile['skin'] or runtime['viewport']['locale'] != profile['locale']:
        raise ValueError('Observed skin/locale differs from source profile')
    if runtime['viewport']['safe_area'] != profile['safe_area'] or runtime['shadows_enabled'] is not True:
        raise ValueError('Observed safe area or shadow camera setting differs')
    if observed['source']['facts']['profile']['skin'] != profile['skin']:
        raise ValueError('Source skin is not the requested skin')
    scale = runtime['screenutil']
    design = profile['screenutil_design_size']
    for axis in ('width', 'height'):
        checks.append(measurement('ScreenUtil design.' + axis, design[axis], scale['design_size'][axis], 0))
        checks.append(measurement('ScreenUtil scale.' + axis, profile['viewport'][axis] / design[axis], scale['scale_' + axis], 0.000001))
    return checks


def source_node(row, observed):
    nodes = observed['source']['facts']['nodes']
    return next(node for node in nodes if node['selector'] == row['selector'])


def css_pixels(css):
    if css == 'normal':
        raise ValueError('CSS normal line height requires measured line metrics; unsupported by this adapter')
    match = re.fullmatch(r'(-?\d+(?:\.\d+)?)px', css)
    if not match:
        raise ValueError('Unsupported CSS metric: ' + css)
    return float(match.group(1))


def typography_checks(row, observed):
    css = source_node(row, observed)['computed']
    expected = {'font_size': css_pixels(css['font-size']), 'font_weight': float(css['font-weight']),
                'line_height': css_pixels(css['line-height']),
                'letter_spacing': 0 if css['letter-spacing'] == 'normal' else css_pixels(css['letter-spacing'])}
    actual = observed['runtime']['typography']
    return [measurement('effective text.' + key, number, actual[key], 0.01) for key, number in expected.items()]


def contained_box(box, crop):
    return all(box[axis] >= crop[axis] and box[axis] + box[extent] <= crop[axis] + crop[extent]
               for axis, extent in (('x', 'width'), ('y', 'height')))


def field_checks(row, observed):
    runtime = observed['runtime']
    for number in runtime['outer_bounds'].values():
        finite_number(number)
    box = source_node(row, observed)['box']
    if not contained_box(box, row['profile']['crop']):
        raise ValueError('Field crop must include the entire painted border/fill')
    return rectangle_checks('painted field container', box, runtime['painted_bounds'], 1 / row['profile']['dpr'])


def glow_checks(row, observed):
    facts = observed['source']['facts']
    candidate = next(candidate for candidate in facts['composition']['visible'] if candidate['selector'] == row['selector'])
    bounds = candidate['bounds']
    if bounds is None:
        raise ValueError('Source glow bounds unresolved; inspect composition and retain NOT VERIFIED')
    expected = {'x': bounds['x'], 'y': bounds['y'], 'width': bounds['w'], 'height': bounds['h']}
    checks = rectangle_checks('glow paint box', expected, observed['runtime']['glow_bounds'], 1 / row['profile']['dpr'])
    selectors = row['overlap_selectors']
    if not selectors:
        raise ValueError('Glow calibration needs actual overlapping consumers, not a layer enum')
    for selector in selectors:
        checks += glow_overlap_checks(row, observed, expected, selector)
    return checks


def glow_overlap_checks(row, observed, glow, selector):
    facts = observed['source']['facts']
    box = next(node['box'] for node in facts['nodes'] if node['selector'] == selector)
    intersects = all(box[axis] + box[extent] > glow[axis] and box[axis] < glow[axis] + glow[extent]
                     for axis, extent in (('x', 'width'), ('y', 'height')))
    if not intersects or not contained_box(box, row['profile']['crop']):
        raise ValueError('Composition crop must include a consumer overlapping the glow')
    return rectangle_checks('overlapped consumer', box, observed['runtime']['overlap_bounds'][selector], 1 / row['profile']['dpr'])


CHECKS = {'typography': typography_checks, 'field': field_checks, 'glow': glow_checks}


def crop_image(identity, profile, output):
    viewport, crop, dpr = profile['viewport'], profile['crop'], profile['dpr']
    size = tuple(round(viewport[axis] * dpr) for axis in ('width', 'height'))
    numbers = {key: finite_number(crop[key]) for key in ('x', 'y', 'width', 'height')}
    if min(numbers['x'], numbers['y']) < 0 or min(numbers['width'], numbers['height']) <= 0:
        raise ValueError('Crop must have positive dimensions inside the layout viewport')
    if numbers['x'] + numbers['width'] > viewport['width'] or numbers['y'] + numbers['height'] > viewport['height']:
        raise ValueError('Crop exceeds layout viewport')
    edges = [crop['x'], crop['y'], crop['x'] + crop['width'], crop['y'] + crop['height']]
    pixels = [round(edge * dpr) for edge in edges]
    if any(abs(edge * dpr - pixel) > 1e-6 for edge, pixel in zip(edges, pixels)):
        raise ValueError('Use identical explicit integer-pixel crop edges; never resize')
    with Image.open(identity['path']) as image:
        if image.format != 'PNG' or image.size != size:
            raise ValueError('Camera PNG must match full layout viewport × DPR before cropping')
        image.load()
        image.crop(pixels).save(output)


def compare_crops(row, observed, directory):
    directory.mkdir()
    for name, capture in zip(('expected', 'actual'), observed['captures']):
        crop_image(capture, row['profile'], directory / (name + '.png'))
    command = [sys.executable, str(DIRECTORY / 'compare.py'), '--json', '--expected', str(directory / 'expected.png'),
               '--actual', str(directory / 'actual.png'), '--output', str(directory / 'diff.png')]
    compared = subprocess.run(command, capture_output=True, text=True)
    (directory / 'compare.stdout.log').write_text(compared.stdout)
    (directory / 'compare.stderr.log').write_text(compared.stderr)
    comparison = json.loads(compared.stdout)
    (directory / 'compare.json').write_text(json.dumps(comparison, indent=2) + '\n')
    return comparison, compared.returncode


def calibrate_row(row, observed, directory):
    evidence = {'id': row['id'], 'kind': row['kind'], 'status': 'NOT VERIFIED', 'numeric_status': 'NOT_RUN'}
    try:
        checks = viewport_checks(row, observed) + CHECKS[row['kind']](row, observed)
        comparison, code = compare_crops(row, observed, directory / row['id'])
        passed = all(check['pass'] for check in checks)
        evidence.update(checks=checks, comparison=comparison, numeric_status='PASS' if code == 0 and passed else 'DIFF')
        if code == 2:
            evidence.update(numeric_status='NOT_RUN', reason=comparison.get('error', 'Comparator could not run'))
        elif code or not passed:
            evidence['status'] = 'DIFF'
    except (OSError, ValueError, KeyError, TypeError, StopIteration) as error:
        evidence['reason'] = 'Missing/unsupported observation: ' + str(error)
    return evidence


def report_exit(report):
    if report['status'] == 'NOT VERIFIED' and not report.get('rows'):
        return 2
    if any(row['numeric_status'] == 'NOT_RUN' for row in report['rows']):
        return 2
    return 1 if any(row['status'] == 'DIFF' for row in report['rows']) else 0


def run_calibration(args):
    plan = read_json(args.manifest)
    for role in ('source_inputs', 'runtime_inputs'):
        for name in plan[role]:
            path = resolved(args.manifest.parent, name)
            if path.is_dir() and args.out.is_relative_to(path):
                raise ValueError('Evidence output must stay outside input directories')
    args.out.mkdir(parents=True)
    report = {'schema_version': 1, 'status': 'NOT VERIFIED', 'screen_verified': False, 'rows': []}
    try:
        plan, observations, identity, fingerprint = manifest_identity(args.manifest)
        report.update(fingerprint=fingerprint, identity=identity)
        report['rows'] = [calibrate_row(row, observed, args.out) for row, observed in zip(plan['rows'], observations)]
        report['artifacts'] = expanded_files(args.out, ['.']) if any(args.out.iterdir()) else []
        if any(row['status'] == 'DIFF' for row in report['rows']):
            report['status'] = 'DIFF'
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['reason'] = str(error)
    (args.out / 'results.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report, report_exit(report)


def validate_artifacts(artifacts):
    for artifact in artifacts:
        if file_identity(Path(artifact['path'])) != artifact:
            raise ValueError('Calibration evidence changed: ' + artifact['path'])


def current_report(args):
    report = read_json(args.results)
    _, _, identity, fingerprint = manifest_identity(args.manifest)
    if report['fingerprint'] != fingerprint or report['identity'] != identity:
        raise ValueError('Source, working code, probe, fonts, camera, profiles or exports changed')
    validate_artifacts(report['artifacts'])
    if report.get('inspection') and file_identity(Path(report['inspection']['path'])) != report['inspection']:
        raise ValueError('Inspection attestation changed')
    return report


def check_calibration(args):
    try:
        report = current_report(args)
        reusable = inspected_calibration(report)
        return {'fingerprint_match': True, 'calibration_reusable': reusable, 'screen_verified': False}, 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        return {'fingerprint_match': False, 'calibration_reusable': False, 'screen_verified': False, 'reason': str(error)}, 1


def inspection_decisions(report, inspection, results_hash):
    if inspection['fingerprint'] != report['fingerprint'] or inspection['results_sha256'] != results_hash:
        raise ValueError('Inspection must bind the exact report and input fingerprint')
    if not inspection['inspector'].strip() or not inspection['notes'].strip():
        raise ValueError('Describe actual probe/core/camera/PNG inspection')
    if set(inspection['rows']) != {row['id'] for row in report['rows']}:
        raise ValueError('Every calibration row requires inspection')
    for inspected in inspection['rows'].values():
        if type(inspected['accepted']) is not bool or not inspected['notes'].strip():
            raise ValueError('Inspection needs explicit decisions and measured findings')
    return inspection['rows']


def inspected_calibration(report):
    if not report.get('inspection') and report['status'] != 'CALIBRATED':
        return False
    source = report['source_results']
    if file_identity(Path(source['path'])) != source:
        raise ValueError('Inspected source report changed')
    original = read_json(Path(source['path']))
    if original['fingerprint'] != report['fingerprint'] or original['identity'] != report['identity']:
        raise ValueError('Inspected original identity differs from current calibration inputs')
    validate_artifacts(original['artifacts'])
    inspection = read_json(Path(report['inspection']['path']))
    expected = finalized_report(original, inspection, source, report['inspection'])
    if report != expected:
        raise ValueError('Final report must retain the original evidence and only permitted inspection changes')
    return report['status'] == 'CALIBRATED' and all(row['numeric_status'] == 'PASS' and row['status'] == 'CALIBRATED'
                                                  for row in report['rows'])


def finalized_report(original, inspection, source, attestation):
    if original.get('inspection') or original.get('source_results'):
        raise ValueError('Finalize the original run report, not a previously reviewed report')
    decisions = inspection_decisions(original, inspection, source['sha256'])
    report = copy.deepcopy(original)
    for row in report['rows']:
        if row['numeric_status'] == 'PASS':
            row['status'] = 'CALIBRATED' if decisions[row['id']]['accepted'] else 'DIFF'
    statuses = {row['status'] for row in report['rows']}
    report['status'] = 'CALIBRATED' if statuses == {'CALIBRATED'} else 'DIFF' if 'DIFF' in statuses else 'NOT VERIFIED'
    report['inspection'] = attestation
    report['source_results'] = source
    report['artifacts'].append(source)
    return report


def finalize_calibration(args):
    original = current_report(args)
    report = finalized_report(original, read_json(args.inspection), file_identity(args.results), file_identity(args.inspection))
    args.out.mkdir(parents=True)
    (args.out / 'results.json').write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
    return report, report_exit(report)


def main():
    parser = argparse.ArgumentParser(description='Calibrate representative actual-core captures; never verify a screen')
    parser.add_argument('action', choices=('run', 'check', 'finalize'))
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--results', type=Path)
    parser.add_argument('--inspection', type=Path)
    args = parser.parse_args()
    for key in ('manifest', 'out', 'results', 'inspection'):
        if getattr(args, key) is not None:
            setattr(args, key, getattr(args, key).resolve())
    required = {'run': ('out',), 'check': ('results',), 'finalize': ('results', 'inspection', 'out')}
    if any(getattr(args, key) is None for key in required[args.action]):
        parser.error('Missing arguments for ' + args.action)
    try:
        report, code = {'run': run_calibration, 'check': check_calibration, 'finalize': finalize_calibration}[args.action](args)
    except (OSError, ValueError, KeyError, TypeError) as error:
        report, code = {'status': 'NOT VERIFIED', 'screen_verified': False, 'reason': str(error)}, 2
    print(json.dumps(report, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
