import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

import yaml


CASES = Path(__file__).with_name('selection_cases.json')


def read_catalog(root):
    catalog = []
    for path in sorted((root / 'plugins/flutter-knowledge/skills').glob('*/SKILL.md')):
        text = path.read_text()
        match = re.fullmatch(r'---\n(.*?)\n---\n(.*)', text, re.S)
        if not match:
            raise ValueError(f'Invalid frontmatter: {path}')
        fields = yaml.safe_load(match[1])
        if (not isinstance(fields, dict) or fields.get('name') != path.parent.name
                or not isinstance(fields.get('description'), str) or not fields['description'].strip()):
            raise ValueError(f'Invalid skill identity: {path}')
        catalog.append({'name': fields['name'], 'description': fields['description'],
                        'body_sha256': hashlib.sha256(match[2].encode()).hexdigest()})
    if not catalog:
        raise ValueError(f'No skills found under {root}')
    return catalog


def prepare(root, out):
    catalog = read_catalog(root)
    cases = json.loads(CASES.read_text())
    out.mkdir(parents=True, exist_ok=True)
    public_catalog = [{k: item[k] for k in ('name', 'description')} for item in catalog]
    requests = [{k: item[k] for k in ('id', 'request')} for item in cases]
    (out / 'catalog.json').write_text(json.dumps(public_catalog, indent=2) + '\n')
    (out / 'manifest.json').write_text(json.dumps({
        'catalog': catalog, 'cases_sha256': hashlib.sha256(CASES.read_bytes()).hexdigest(),
    }, indent=2) + '\n')
    prompt = (
        'Select the single most specific entry skill for each independent request from this catalog. '
        'Choose the entry skill, not all downstream prerequisites. Use flutter-knowledge only for '
        'broad Flutter work without a more specific entry; use null if no skill applies. '
        'Evaluate each request independently. Do not implement tasks or read skill bodies, other '
        'files, expected answers, or installed skills. Return only a JSON object mapping every '
        'request id to one catalog skill name or null.\n\nCATALOG\n'
        + json.dumps(public_catalog, indent=2) + '\n\nREQUESTS\n'
        + json.dumps(requests, indent=2) + '\n'
    )
    (out / 'prompt.txt').write_text(prompt)
    return {'skills': len(catalog), 'requests': len(cases), 'prompt': str(out / 'prompt.txt')}


def score(before, after, result_paths):
    cases = json.loads(CASES.read_text())
    expected = {case['id']: case['expected'] for case in cases}
    catalogs = {label: json.loads((root / 'manifest.json').read_text())
                for label, root in (('before', before), ('after', after))}
    case_hash = hashlib.sha256(CASES.read_bytes()).hexdigest()
    if any(item['cases_sha256'] != case_hash for item in catalogs.values()):
        raise ValueError('Requests changed after preparation; prepare and rerun both versions')
    names = {item['name'] for item in catalogs['before']['catalog']}
    after_names = {item['name'] for item in catalogs['after']['catalog']}
    if names != after_names:
        raise ValueError('Catalog skill names differ')
    runs = {label: [] for label in catalogs}
    def unique_decisions(pairs):
        decisions = {}
        for key, value in pairs:
            if key in decisions:
                raise ValueError(f'Duplicate decision id: {key}')
            decisions[key] = value
        return decisions

    for label, path in result_paths:
        if label not in runs:
            raise ValueError(f'Unknown variant: {label}')
        decisions = json.loads(path.read_text(), object_pairs_hook=unique_decisions)
        if not isinstance(decisions, dict) or set(decisions) != set(expected):
            raise ValueError(f'{path}: expected every request exactly once')
        if any(value is not None and (not isinstance(value, str) or value not in names)
               for value in decisions.values()):
            raise ValueError(f'{path}: unknown skill selection')
        runs[label].append({'path': str(path), 'decisions': decisions,
                            'correct': sum(decisions[k] == v for k, v in expected.items()),
                            'misses': [k for k, v in expected.items() if decisions[k] != v]})
    if not runs['before'] or len(runs['before']) != len(runs['after']):
        raise ValueError('Provide equal nonzero repetitions for before and after')
    stats = {}
    for label, items in runs.items():
        total = len(expected) * len(items)
        correct = sum(item['correct'] for item in items)
        stats[label] = {'repetitions': len(items), 'correct': correct, 'total': total,
                        'accuracy': correct / total, 'runs': items}
    before_bodies = {item['name']: item['body_sha256'] for item in catalogs['before']['catalog']}
    after_bodies = {item['name']: item['body_sha256'] for item in catalogs['after']['catalog']}
    counts = {}
    for label in catalogs:
        descriptions = '\n'.join(item['description'] for item in catalogs[label]['catalog'])
        counts[label] = {'description_words': len(descriptions.split()),
                         'description_utf8_bytes': len(descriptions.encode())}
    changed = []
    for key in expected:
        old = sum(item['decisions'][key] == expected[key] for item in runs['before'])
        new = sum(item['decisions'][key] == expected[key] for item in runs['after'])
        if old != new:
            changed.append({'id': key, 'expected': expected[key],
                            'before_correct': old, 'after_correct': new})
    return {'selection': stats, 'size': counts, 'changed_cases': changed,
            'changed_skill_bodies': [name for name in sorted(names)
                                     if before_bodies[name] != after_bodies[name]],
            'limits': 'Description-only routing probe; not execution, native builds, host-client integration, or end-to-end token usage.'}


def main():
    parser = argparse.ArgumentParser(description='Prepare and score paired description-only skill selection probes.')
    sub = parser.add_subparsers(dest='command', required=True)
    prep = sub.add_parser('prepare')
    prep.add_argument('--root', type=Path, required=True)
    prep.add_argument('--out', type=Path, required=True)
    grade = sub.add_parser('score')
    grade.add_argument('--before', type=Path, required=True)
    grade.add_argument('--after', type=Path, required=True)
    grade.add_argument('--result', action='append', required=True, metavar='VARIANT=FILE')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            report = prepare(args.root, args.out)
        else:
            result_paths = []
            for value in args.result:
                label, separator, path = value.partition('=')
                if not separator or not path:
                    raise ValueError('Result must be VARIANT=FILE')
                result_paths.append((label, Path(path)))
            if len({path.resolve() for _, path in result_paths}) != len(result_paths):
                raise ValueError('Each repetition needs a distinct result file')
            report = score(args.before, args.after, result_paths)
    except (ValueError, OSError, KeyError, yaml.YAMLError) as error:
        parser.exit(2, f'{error}\n')
    json.dump(report, sys.stdout, indent=2)
    print()


if __name__ == '__main__':
    main()
