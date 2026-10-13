import argparse
import hashlib
import json
import math
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

EXTRACTOR = Path(__file__).resolve().parents[2] / 'html-to-widget/scripts/layout-tree.js'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def file_identity(path):
    return {'path': str(path.resolve()), 'sha256': file_hash(path)}


def positive_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ValueError(label + ' must be a positive finite number')


def validate_profile(profile):
    if not isinstance(profile, dict):
        raise ValueError('Capture profile must be an object')
    viewport = profile.get('viewport')
    if not isinstance(viewport, dict):
        raise ValueError('Profile viewport must contain width and height')
    for axis in ('width', 'height'):
        positive_number(viewport.get(axis), 'viewport.' + axis)
    for key in ('dpr', 'text_scale'):
        positive_number(profile.get(key), key)
    for key in ('screen', 'state', 'selector', 'skin', 'locale', 'capture_adapter'):
        if not isinstance(profile.get(key), str) or not profile[key].strip():
            raise ValueError('Profile requires ' + key)
    if profile['capture_adapter'].strip().lower() in ('unknown', 'unavailable'):
        raise ValueError('Unknown renderer/tool identity cannot establish reusable extraction')
    safe_area = profile.get('safe_area')
    if not isinstance(safe_area, dict):
        raise ValueError('Profile requires safe_area')
    for side in ('top', 'right', 'bottom', 'left'):
        value = safe_area.get(side)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError('safe_area.' + side + ' must be finite and nonnegative')
    if not isinstance(profile.get('data'), dict):
        raise ValueError('Profile requires deterministic data identity')
    return profile


def fingerprint(source, profile_path, manifest_path):
    profile = validate_profile(read_json(profile_path))
    manifest = read_json(manifest_path)
    if not isinstance(manifest, dict) or manifest.get('complete') is not True:
        raise ValueError('Source dependency inventory is incomplete; recapture without cache reuse')
    if manifest.get('external_resources') != []:
        raise ValueError('Remote resources require current materialized snapshots; raw URLs are not cache identities')
    files = manifest.get('files')
    if not isinstance(files, list) or any(not isinstance(item, str) for item in files):
        raise ValueError('Source dependency files must be a list of paths')
    paths = {source.resolve(), EXTRACTOR.resolve()}
    for item in files:
        path = (manifest_path.parent / item).resolve()
        if path.is_dir():
            paths.update(child.resolve() for child in path.rglob('*') if child.is_file())
        else:
            paths.add(path)
    inputs = [file_identity(path) for path in sorted(paths)]
    identity = {'schema_version': 1, 'source': str(source.resolve()), 'profile': profile, 'inputs': inputs}
    encoded = json.dumps(identity, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(encoded).hexdigest(), identity


def reference_identity(path, profile):
    with Image.open(path) as image:
        if image.format != 'PNG':
            raise ValueError('Reference must be a PNG capture')
        expected = tuple(round(profile['viewport'][axis] * profile['dpr']) for axis in ('width', 'height'))
        if image.size != expected:
            raise ValueError(f'Reference dimensions {image.size} do not match profile {expected}; never resize to qualify')
        image.verify()
    return file_identity(path)


def output_record(record, status):
    reference = record.get('reference')
    return {
        'status': status,
        'fingerprint': record['fingerprint'],
        'facts_reusable': True,
        'facts_path': record['facts']['path'],
        'reference_reusable': bool(reference and record['reference_status'] == 'fresh'),
        'reference_status': record.get('reference_status'),
        'reference_path': reference['path'] if reference else None,
        'design_verified': False,
    }


def record_cache(args):
    key, identity = fingerprint(args.source, args.profile, args.inputs_manifest)
    facts = read_json(args.facts)
    if not isinstance(facts, (dict, list)) or not facts or isinstance(facts, dict) and facts.get('error'):
        raise ValueError('Facts must contain successful source extraction')
    if isinstance(facts, dict):
        if facts.get('hidden') is True or facts.get('visible') is False:
            raise ValueError('Requested source state is hidden; measure the visible state before caching')
        for dimension in ('w', 'h'):
            if dimension in facts:
                positive_number(facts[dimension], 'facts.' + dimension)
    record = {'fingerprint': key, 'identity': identity, 'facts': file_identity(args.facts),
              'reference': None, 'reference_status': None, 'capture_metadata': None}
    if args.reference:
        record['reference'] = reference_identity(args.reference, identity['profile'])
        record['reference_status'] = args.reference_status
        if args.reference_status == 'fresh':
            if args.capture_metadata is None:
                raise ValueError('Fresh reference requires capture-time provenance, not an after-the-fact cache association')
            metadata = read_json(args.capture_metadata)
            if not isinstance(metadata, dict) or metadata.get('fingerprint') != key:
                raise ValueError('Reference capture provenance does not match current source/profile/dependencies')
            if metadata.get('reference_sha256') != record['reference']['sha256']:
                raise ValueError('Capture provenance does not bind this reference PNG')
            if metadata.get('tool') != identity['profile']['capture_adapter']:
                raise ValueError('Capture provenance tool must match the profile adapter identity')
            timestamp = metadata.get('captured_at')
            if not isinstance(timestamp, str):
                raise ValueError('Capture provenance requires a timestamp string')
            captured_at = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            if captured_at.tzinfo is None:
                raise ValueError('Capture timestamp must have a timezone')
            record['capture_metadata'] = file_identity(args.capture_metadata)
    protected = {Path(item['path']) for item in identity['inputs']}
    protected.update(path.resolve() for path in (args.profile, args.inputs_manifest, args.facts, args.reference, args.capture_metadata) if path is not None)
    if args.cache.resolve() in protected:
        raise ValueError('Cache output must not replace a source, profile, dependency or extraction artifact')
    args.cache.parent.mkdir(parents=True, exist_ok=True)
    args.cache.write_text(json.dumps(record, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    return output_record(record, 'recorded'), 0


def check_cache(args):
    try:
        key, identity = fingerprint(args.source, args.profile, args.inputs_manifest)
        record = read_json(args.cache)
        if record['fingerprint'] != key or record['identity'] != identity:
            raise ValueError('Source, dependencies, extractor or capture profile changed')
        for role in ('facts', 'reference', 'capture_metadata'):
            artifact = record.get(role)
            if artifact and file_identity(Path(artifact['path'])) != artifact:
                raise ValueError(role + ' artifact changed')
        if record.get('reference'):
            reference_identity(Path(record['reference']['path']), identity['profile'])
            if record.get('reference_status') not in ('fresh', 'archived'):
                raise ValueError('Reference provenance status is invalid')
            if record['reference_status'] == 'fresh':
                metadata = read_json(Path(record['capture_metadata']['path']))
                if metadata.get('fingerprint') != key or metadata.get('reference_sha256') != record['reference']['sha256']:
                    raise ValueError('Reference capture provenance changed')
        if not record.get('facts'):
            raise ValueError('Cache has no extraction facts')
        return output_record(record, 'hit'), 0
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        return {'status': 'miss', 'reason': str(error), 'facts_reusable': False,
                'reference_reusable': False, 'design_verified': False}, 1


def main():
    parser = argparse.ArgumentParser(description='Validate source-fact/reference reuse; never certify design fidelity.')
    parser.add_argument('action', choices=('record', 'check'))
    for flag in ('source', 'profile', 'inputs-manifest', 'cache'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--facts', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--reference-status', choices=('fresh', 'archived'), default='archived')
    parser.add_argument('--capture-metadata', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'record':
            if args.facts is None:
                raise ValueError('record requires --facts')
            result, code = record_cache(args)
        else:
            result, code = check_cache(args)
    except (OSError, ValueError, KeyError, TypeError, SyntaxError) as error:
        result, code = {'status': 'error', 'reason': str(error), 'facts_reusable': False,
                        'reference_reusable': False, 'design_verified': False}, 2
    print(json.dumps(result, allow_nan=False))
    return code


if __name__ == '__main__':
    sys.exit(main())
