import argparse
import json
import math
import os
import re
import subprocess
import sys
import uuid
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import design_cache

COMPARE = Path(__file__).resolve().parent / 'compare.py'
ROW_ID = re.compile(r'^[a-z0-9][a-z0-9._-]*$')
CONDITIONS = ('fonts', 'shadows', 'motion', 'pointer', 'expected_state')
KINDS = ('source', 'regression')
OUTCOMES = ('accepted', 'rejected')
SEVERITY = {'PASS': 0, 'NOT_RUN': 0, 'DIFF': 1, 'ERROR': 2}


def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(path):
    return design_cache.file_hash(Path(path))


def identity(path):
    return {'path': str(Path(path).resolve()), 'sha256': sha256(path)}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def require_file(path, label):
    if not path.is_file():
        raise ValueError(label + ' is not a file: ' + str(path))
    return path


def inside(root, path, label):
    resolved = path.resolve()
    if root.resolve() not in resolved.parents:
        raise ValueError(label + ' must stay inside ' + str(root))
    return resolved


def expected_size(profile):
    return tuple(round(profile['viewport'][axis] * profile['dpr']) for axis in ('width', 'height'))


def load_profile(path):
    profile = design_cache.validate_profile(read_json(path))
    conditions = profile.get('conditions')
    if not isinstance(conditions, dict) or any(conditions.get(key) in (None, '') for key in CONDITIONS):
        raise ValueError('Profile conditions must state ' + ', '.join(CONDITIONS))
    for key in ('fonts', 'motion', 'pointer', 'expected_state'):
        if not isinstance(conditions[key], str) or not conditions[key].strip():
            raise ValueError('Profile conditions.' + key + ' must describe the controlled capture')
    if not isinstance(conditions['shadows'], bool):
        raise ValueError('Profile conditions.shadows must explicitly enable or disable shadows')
    inset = conditions.get('keyboard_inset', 0)
    if isinstance(inset, bool) or not isinstance(inset, (int, float)) or not math.isfinite(inset) or inset < 0:
        raise ValueError('Profile conditions.keyboard_inset must be finite and nonnegative')
    return profile


def check_camera(command, batch):
    if not isinstance(command, list) or len(command) < 2 or any(not isinstance(item, str) for item in command):
        raise ValueError('Capture command must be an argv list')
    if Path(command[0]).name != 'flutter' or command[1] != 'test':
        raise ValueError('Capture command must be a flutter test argv')
    joined = '\0'.join(command)
    if batch:
        if '--dart-define=CAPTURE_ROUND={attempt}' not in command:
            raise ValueError('Batch capture must pass --dart-define=CAPTURE_ROUND={attempt}')
    elif '{actual}' not in joined or '{profile}' not in joined:
        raise ValueError('Per-row capture must reference {actual} and {profile}')


def camera_argv(command, values):
    argv = list(command)
    for flag in ('--no-pub', '--update-goldens'):
        if flag not in argv:
            argv.insert(2, flag)
    for key, value in values.items():
        argv = [item.replace('{' + key + '}', value) for item in argv]
    return argv


def parse_manifest(path, project_override):
    manifest = read_json(path)
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
        raise ValueError('Manifest schema_version must be 1')
    base = path.parent.resolve()
    project = project_override or (base / manifest['project'] if manifest.get('project') else base)
    project = Path(project).resolve()
    if not project.is_dir():
        raise ValueError('Project directory does not exist: ' + str(project))
    rows = manifest.get('rows')
    if not isinstance(rows, list) or not rows:
        raise ValueError('Manifest requires rows')
    batch = manifest.get('capture')
    if batch is not None:
        if not isinstance(batch, dict):
            raise ValueError('capture must be an object with command')
        check_camera(batch.get('command'), True)
    seen, candidates, parsed = set(), set(), []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Rows must be objects')
        row_id = row.get('id')
        if not isinstance(row_id, str) or not ROW_ID.match(row_id) or row_id in seen:
            raise ValueError('Rows need unique stable ids matching ' + ROW_ID.pattern)
        seen.add(row_id)
        if row.get('kind') not in KINDS:
            raise ValueError(row_id + ': kind must be source or regression')
        if not isinstance(row.get('label'), str) or not row['label'].strip() or '|' in row['label']:
            raise ValueError(row_id + ': label must be plain text without a pipe')
        profile_path = require_file(base / str(row.get('profile', '')), row_id + ' profile')
        profile = load_profile(profile_path)
        entry = {'row': row, 'id': row_id, 'profile_path': profile_path.resolve(), 'profile': profile,
                 'source': None, 'reference': None, 'cache': None}
        if row['kind'] == 'source':
            source = row.get('source')
            if not isinstance(source, dict) or not source.get('path'):
                raise ValueError(row_id + ': source rows require source.path')
            entry['source'] = require_file(base / source['path'], row_id + ' source').resolve()
            if bool(source.get('cache')) != bool(source.get('inputs_manifest')):
                raise ValueError(row_id + ': source.cache and source.inputs_manifest go together')
            if source.get('cache'):
                entry['cache'] = {'cache': (base / source['cache']).resolve(),
                                  'inputs': (base / source['inputs_manifest']).resolve()}
            if not row.get('reference'):
                raise ValueError(row_id + ': source rows require a reference PNG')
        elif row.get('source'):
            raise ValueError(row_id + ': regression rows declare no source')
        reference = row.get('reference')
        if reference is not None:
            if not isinstance(reference, dict) or not reference.get('path'):
                raise ValueError(row_id + ': reference requires path')
            entry['reference'] = require_file(base / reference['path'], row_id + ' reference').resolve()
        if batch is not None:
            if row.get('capture') is not None:
                raise ValueError(row_id + ': do not combine manifest-level and per-row capture commands')
            actual = row.get('actual')
            if not isinstance(actual, str) or '{attempt}' not in actual:
                raise ValueError(row_id + ': batch rows need an actual path containing {attempt}')
            relative = Path(actual)
            if relative.is_absolute():
                raise ValueError(row_id + ': actual must be project-relative')
            candidate = inside(project, project / actual.replace('{attempt}', 'attempt'), row_id + ' actual')
            if candidate in candidates:
                raise ValueError(row_id + ': actual paths must be unique per row')
            candidates.add(candidate)
            entry['mode'] = 'batch'
        else:
            capture = row.get('capture')
            if not isinstance(capture, dict):
                raise ValueError(row_id + ': row needs capture.command or a manifest-level capture')
            check_camera(capture.get('command'), False)
            entry['mode'] = 'row'
        parsed.append(entry)
    return manifest, project, batch, parsed, base


def execute(argv, cwd):
    try:
        return subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    except OSError as error:
        return subprocess.CompletedProcess(argv, None, '', 'Could not launch command: ' + str(error))


def save_log(directory, name, text):
    path = directory / name
    path.write_text(text or '', encoding='utf-8')
    return identity(path)


def dimension_error(actual, profile):
    try:
        with Image.open(actual) as image:
            if image.format != 'PNG':
                return 'Capture is not a PNG image.'
            image.verify()
        with Image.open(actual) as image:
            size = image.size
    except (OSError, ValueError, SyntaxError) as error:
        return 'Capture is not a readable PNG: ' + str(error)
    want = expected_size(profile)
    if size != want:
        return 'Capture is ' + 'x'.join(map(str, size)) + ' but the profile requires ' + 'x'.join(map(str, want))
    return None


def provenance(entry):
    if entry['source'] is None:
        return {'source_backed': False, 'reference_reusable': False,
                'reason': 'No source reference is declared for this row.'}
    if entry['cache'] is None:
        return {'source_backed': True, 'cache_status': 'none', 'reference_reusable': False,
                'reason': 'No design cache binds capture-time freshness to this reference.'}
    result, _ = design_cache.check_cache(Namespace(
        source=entry['source'], profile=entry['profile_path'],
        inputs_manifest=entry['cache']['inputs'], cache=entry['cache']['cache']))
    reusable = bool(result.get('reference_reusable') and result.get('reference_path') and
                    Path(result['reference_path']).resolve() == entry['reference'])
    reason = result.get('reason') or ('Reference is fresh and bound to the current source.' if reusable else
                                       'Cached reference is archived or is another file.')
    return {'source_backed': True, 'cache_status': result['status'], 'reference_reusable': reusable,
            'fingerprint': result.get('fingerprint'), 'reference_status': result.get('reference_status'),
            'reason': reason}


def compare_row(actual, reference, diff):
    argv = [sys.executable, str(COMPARE), '--actual', str(actual), '--expected', str(reference),
            '--output', str(diff), '--json']
    done = execute(argv, actual.parent)
    try:
        payload = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        payload = {'status': 'ERROR', 'error': 'Comparator produced no JSON: ' + (done.stderr or done.stdout)[-400:]}
    if done.returncode not in (0, 1) or payload.get('status') not in ('PASS', 'DIFF'):
        payload = {'status': 'ERROR', 'error': payload.get('error') or 'Comparator exit ' + str(done.returncode)}
    return payload, done, argv


def source_inputs(entry):
    inputs = {'profile': identity(entry['profile_path'])}
    if entry['source']:
        inputs['source'] = identity(entry['source'])
    if entry['reference']:
        inputs['reference'] = identity(entry['reference'])
    if entry['cache']:
        for role, path in entry['cache'].items():
            if path.is_file():
                inputs['source_' + role] = identity(path)
        if entry['provenance']['reference_reusable']:
            cached = read_json(entry['cache']['cache'])
            inputs.update({'source_dependency_' + str(index): artifact
                           for index, artifact in enumerate(cached['identity']['inputs'])})
            inputs.update({'cache_' + role: cached[role] for role in ('facts', 'capture_metadata') if cached.get(role)})
    return inputs


def current_source_cache(row):
    inputs = row['inputs']
    checked, _ = design_cache.check_cache(Namespace(
        source=Path(inputs['source']['path']), profile=Path(inputs['profile']['path']),
        inputs_manifest=Path(inputs['source_inputs']['path']), cache=Path(inputs['source_cache']['path'])))
    return checked


def inputs_changed(inputs):
    return any(not Path(artifact['path']).is_file() or sha256(artifact['path']) != artifact['sha256']
               for artifact in inputs.values())


def preserve_uncompared(actual, candidate, artifacts):
    if candidate is not None and candidate.is_file():
        actual.write_bytes(candidate.read_bytes())
    if actual.is_file():
        artifacts['uncompared_actual'] = identity(actual)


def run_manifest(manifest_path, out_dir, project=None):
    manifest_path = Path(manifest_path).resolve()
    manifest, project, batch, entries, base = parse_manifest(manifest_path, Path(project) if project else None)
    manifest_identity = identity(manifest_path)
    for entry in entries:
        entry['provenance'] = provenance(entry)
        entry['inputs'] = source_inputs(entry)
    out_dir = Path(out_dir)
    started = now()
    attempt_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    attempt = (out_dir / attempt_id).resolve()
    values = {'attempt': attempt_id}
    candidates = {}
    if batch is not None:
        for entry in entries:
            path = (project / entry['row']['actual'].replace('{attempt}', attempt_id)).resolve()
            inside(project, path, entry['id'] + ' actual')
            if path.exists():
                raise ValueError(entry['id'] + ': candidate path already exists; attempts must be unique')
            candidates[entry['id']] = path
    attempt.mkdir(parents=True)
    shared = None
    if batch is not None:
        argv = camera_argv(batch['command'], values)
        done = execute(argv, project)
        shared = {'mode': 'batch', 'argv': argv, 'exit_code': done.returncode,
                  'stdout': save_log(attempt, 'capture.stdout.log', done.stdout),
                  'stderr': save_log(attempt, 'capture.stderr.log', done.stderr)}
    results = []
    for entry in entries:
        row = entry['row']
        row_dir = attempt / 'rows' / entry['id']
        row_dir.mkdir(parents=True)
        actual = row_dir / 'actual.png'
        capture = shared
        if shared is None:
            argv = camera_argv(row['capture']['command'], dict(values, actual=str(actual), profile=str(entry['profile_path'])))
            done = execute(argv, project)
            capture = {'mode': 'row', 'argv': argv, 'exit_code': done.returncode,
                       'stdout': save_log(row_dir, 'capture.stdout.log', done.stdout),
                       'stderr': save_log(row_dir, 'capture.stderr.log', done.stderr)}
        candidate = candidates.get(entry['id'])
        artifacts = {'capture_stdout': capture['stdout'], 'capture_stderr': capture['stderr']}
        inputs = dict(entry['inputs'])
        if entry['reference']:
            artifacts['reference'] = inputs['reference']
        record = {'id': entry['id'], 'label': row['label'], 'kind': row['kind'], 'profile': entry['profile'],
                  'capture': {'mode': capture['mode'], 'argv': capture['argv'], 'exit_code': capture['exit_code']},
                  'inputs': inputs, 'artifacts': artifacts, 'provenance': entry['provenance'],
                  'inspection_required': True}
        problem = None
        if capture['exit_code'] is None:
            problem = Path(capture['stderr']['path']).read_text(encoding='utf-8')
        elif capture['exit_code'] != 0:
            problem = 'Capture command exited ' + str(capture['exit_code']) + '; no PNG was compared.'
        elif inputs_changed(inputs) or identity(manifest_path) != manifest_identity:
            problem = 'Capture inputs changed while the camera ran; no PNG was compared.'
        elif entry['provenance']['reference_reusable'] and not current_source_cache(record).get('reference_reusable'):
            problem = 'Source dependency inventory changed while the camera ran; no PNG was compared.'
        elif candidate is not None:
            if not candidate.is_file():
                problem = 'Capture finished without writing ' + str(candidate)
            else:
                inputs['candidate'] = identity(candidate)
                actual.write_bytes(candidate.read_bytes())
        elif not actual.is_file():
            problem = 'Capture finished without writing the requested actual PNG.'
        if problem is None:
            artifacts['actual'] = identity(actual)
            problem = dimension_error(actual, entry['profile'])
        if problem:
            preserve_uncompared(actual, candidate, artifacts)
            record['comparison'] = {'status': 'ERROR', 'error': problem}
            record['compare'] = None
        elif entry['reference'] is None:
            record['comparison'] = {'status': 'NOT_RUN', 'reason': 'No reference PNG is declared for this row.'}
            record['compare'] = None
        else:
            diff = row_dir / 'diff.png'
            payload, done, argv = compare_row(actual, entry['reference'], diff)
            record['compare'] = {'argv': argv, 'exit_code': done.returncode}
            artifacts['compare_stdout'] = save_log(row_dir, 'compare.stdout.log', done.stdout)
            artifacts['compare_stderr'] = save_log(row_dir, 'compare.stderr.log', done.stderr)
            record['comparison'] = payload
            if payload['status'] != 'ERROR' and diff.is_file():
                artifacts['diff'] = identity(diff)
            write_json(row_dir / 'compare.json', payload)
            artifacts['compare_json'] = identity(row_dir / 'compare.json')
        results.append(record)
    code = max(SEVERITY[item['comparison']['status']] if item['comparison']['status'] in SEVERITY else 2
               for item in results)
    summary = {}
    for item in results:
        summary[item['comparison']['status']] = summary.get(item['comparison']['status'], 0) + 1
    document = {'schema_version': 1, 'attempt': attempt_id, 'started_at': started, 'finished_at': now(),
                'manifest': manifest_identity, 'project': str(project),
                'capture': shared and {key: shared[key] for key in ('mode', 'argv', 'exit_code', 'stdout', 'stderr')},
                'rows': results, 'summary': summary, 'exit_code': code}
    write_json(attempt / 'results.json', document)
    (attempt / 'verification.md').write_text(render(document, attempt, None), encoding='utf-8')
    return attempt, code


def artifact_hashes(row):
    hashes = {}
    for group in ('inputs', 'artifacts'):
        for role, item in sorted(row.get(group, {}).items()):
            path = Path(item['path'])
            hashes[group + '.' + role] = sha256(path) if path.is_file() else None
    return hashes


def recorded_hashes(row):
    return {group + '.' + role: item['sha256']
            for group in ('inputs', 'artifacts') for role, item in sorted(row.get(group, {}).items())}


def percent(value):
    return '{:.2f}%'.format(value)


def link(label, target, base):
    return '[' + label + '](<' + os.path.relpath(target, base).replace(os.sep, '/') + '>)'


def profile_cell(profile):
    viewport = profile['viewport']
    return '{}x{}@{}x {} {} scale {}'.format(viewport['width'], viewport['height'], profile['dpr'],
                                              profile['skin'], profile['locale'], profile['text_scale'])


def final_status(row, review):
    comparison = row['comparison']
    status = comparison['status']
    if status == 'ERROR':
        return 'NOT VERIFIED', 'Blocked: ' + comparison['error']
    if status == 'NOT_RUN':
        return 'NOT VERIFIED', 'No reference PNG; this row is regression coverage only.'
    if review is None:
        if status == 'PASS':
            return 'NOT VERIFIED', 'Numeric PASS; full-resolution PNG inspection required.'
        return 'DIFF', 'Thresholds exceeded; inspect the diff and fix.'
    notes = review['notes']
    if status == 'DIFF':
        return 'DIFF', 'Thresholds exceeded. ' + notes
    if review['outcome'] != 'accepted':
        return 'DIFF', 'Inspection rejected the numeric PASS. ' + notes
    if row['kind'] != 'source':
        return 'NOT VERIFIED', 'Regression PASS inspected; no source reference. ' + notes
    if not row['provenance']['reference_reusable']:
        return 'NOT VERIFIED', 'Inspected PASS; reference freshness is not established (' + row['provenance']['reason'] + '). ' + notes
    return 'VERIFIED', 'Inspected PASS. ' + notes


def render(document, report_dir, inspection):
    reviews = {item['id']: item for item in inspection['rows']} if inspection else {}
    lines = ['# Visual verification', '',
             'Attempt `{}` of manifest `{}`.'.format(document['attempt'], document['manifest']['path']), '',
             'Settings: compare.py defaults (threshold 0.02, max-cluster 0.25, tolerance 12, shift 2, no ignored regions, no resize). '
             'A numeric PASS is NOT VERIFIED until a recorded inspection of the unchanged artifacts accepts it.', '']
    if inspection:
        lines += ['Inspection by {} at {} against results `{}`.'.format(
            inspection['inspector'], inspection['inspected_at'], inspection['results_sha256']), '']
    lines += ['| Screen / state | Source and reference PNG | Capture profile | Flutter PNG / diff PNG | Overall difference | Worst region | Status / remaining differences |',
              '| --- | --- | --- | --- | --- | --- | --- |']
    for row in document['rows']:
        artifacts, comparison = row['artifacts'], row['comparison']
        source = row['inputs'].get('source')
        reference = (link('reference', artifacts['reference']['path'], report_dir) if 'reference' in artifacts else 'no reference')
        if source:
            reference = 'Source `' + source['path'] + '`; ' + reference
        flutter = (link('flutter', artifacts['actual']['path'], report_dir) if 'actual' in artifacts else 'not captured')
        if 'diff' in artifacts:
            flutter += ' ' + link('diff', artifacts['diff']['path'], report_dir)
        status, detail = final_status(row, reviews.get(row['id']))
        measured = row['kind'] == 'source' and comparison['status'] in ('PASS', 'DIFF')
        lines.append('| ' + ' | '.join([
            row['label'], reference, profile_cell(row['profile']), flutter,
            percent(comparison['overall_percent']) if measured else 'n/a',
            percent(comparison['worst_region_percent']) if measured else 'n/a',
            status + ' — ' + detail.replace('|', '/').replace('\n', ' ')]) + ' |')
    if document.get('capture'):
        lines += ['', 'Capture logs: ' + link('stdout', document['capture']['stdout']['path'], report_dir) + ', ' +
                  link('stderr', document['capture']['stderr']['path'], report_dir) + '.']
    return '\n'.join(lines) + '\n'


def validate_inspection(results_path, inspection_path, document):
    inspection = read_json(inspection_path)
    if not isinstance(inspection, dict) or inspection.get('schema_version') != 1:
        raise ValueError('Inspection schema_version must be 1')
    if inspection.get('results_sha256') != sha256(results_path):
        raise ValueError('Inspection is bound to different results')
    for key in ('inspector', 'inspected_at'):
        if not isinstance(inspection.get(key), str) or not inspection[key].strip():
            raise ValueError('Inspection requires ' + key)
    reviews = {}
    for item in inspection.get('rows', []):
        if not isinstance(item, dict) or item.get('id') in reviews:
            raise ValueError('Inspection rows must be unique objects')
        reviews[item['id']] = item
    expected = [row['id'] for row in document['rows']]
    if sorted(reviews) != sorted(expected):
        raise ValueError('Inspection must cover exactly the result rows: ' + ', '.join(expected))
    for row in document['rows']:
        review = reviews[row['id']]
        if review.get('inspected') is not True or review.get('outcome') not in OUTCOMES:
            raise ValueError(row['id'] + ': inspected must be true and outcome one of ' + ', '.join(OUTCOMES))
        if not isinstance(review.get('notes'), str) or not review['notes'].strip():
            raise ValueError(row['id'] + ': inspection notes are required')
        current = artifact_hashes(row)
        if current != review.get('artifact_hashes') or current != recorded_hashes(row):
            raise ValueError(row['id'] + ': artifacts changed since the run or the inspection')
        if row['provenance']['reference_reusable']:
            checked = current_source_cache(row)
            if not checked.get('reference_reusable') or checked.get('fingerprint') != row['provenance']['fingerprint']:
                raise ValueError(row['id'] + ': source dependency inventory or capture provenance changed')
    return inspection


def finalize(results_path, inspection_path, output_dir):
    results_path, output_dir = Path(results_path).resolve(), Path(output_dir)
    document = read_json(results_path)
    inspection = validate_inspection(results_path, Path(inspection_path), document)
    if output_dir.exists():
        raise ValueError('Reviewed output already exists: ' + str(output_dir))
    reviews = {item['id']: item for item in inspection['rows']}
    reviewed = json.loads(json.dumps(document))
    for row in reviewed['rows']:
        status, detail = final_status(row, reviews[row['id']])
        row['reviewed'] = {'status': status, 'detail': detail, 'outcome': reviews[row['id']]['outcome'],
                           'notes': reviews[row['id']]['notes']}
    reviewed['inspection'] = {'inspector': inspection['inspector'], 'inspected_at': inspection['inspected_at'],
                              'results_sha256': inspection['results_sha256'],
                              'inspection_sha256': sha256(inspection_path)}
    output_dir.mkdir(parents=True)
    write_json(output_dir / 'reviewed_results.json', reviewed)
    (output_dir / 'verification.md').write_text(render(document, output_dir, inspection), encoding='utf-8')
    return output_dir


def template(results_path):
    document = read_json(results_path)
    return {'schema_version': 1, 'results_sha256': sha256(results_path), 'inspector': '', 'inspected_at': '',
            'rows': [{'id': row['id'], 'artifact_hashes': artifact_hashes(row), 'inspected': False,
                      'outcome': None, 'notes': ''} for row in document['rows']]}


def main():
    parser = argparse.ArgumentParser(description='Run a manifest of golden captures and source comparisons.')
    commands = parser.add_subparsers(dest='action', required=True)
    run = commands.add_parser('run')
    run.add_argument('--manifest', type=Path, required=True)
    run.add_argument('--out', type=Path, required=True)
    run.add_argument('--project', type=Path)
    final = commands.add_parser('finalize')
    final.add_argument('--results', type=Path, required=True)
    final.add_argument('--inspection', type=Path, required=True)
    final.add_argument('--out', type=Path, required=True)
    blank = commands.add_parser('inspection-template')
    blank.add_argument('--results', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'run':
            attempt, code = run_manifest(args.manifest, args.out, args.project)
            print(json.dumps({'attempt': str(attempt), 'results': str(attempt / 'results.json'),
                              'report': str(attempt / 'verification.md'), 'exit_code': code}))
            return code
        if args.action == 'finalize':
            print(json.dumps({'reviewed': str(finalize(args.results, args.inspection, args.out))}))
            return 0
        print(json.dumps(template(args.results), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
