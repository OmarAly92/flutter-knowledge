import argparse
import hashlib
import json
import math
import re
from pathlib import Path


STAGES = ('source', 'calibration', 'implementation', 'verification', 'baseline', 'review', 'task_total')
TOKEN_FIELDS = ('input_tokens', 'output_tokens', 'cached_input_tokens', 'total_tokens')
COUNTER_FIELDS = ('tool_calls', 'captures', 'correction_rounds')
WORKLOAD_FIELDS = ('task', 'fixture_sha256', 'source_sha256', 'coverage_sha256', 'renderer')
EVENT_ID = re.compile(r'^[a-z0-9][a-z0-9._-]*$')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def validate_measurement(event):
    if not isinstance(event, dict) or type(event.get('schema_version')) is not int or event['schema_version'] != 1:
        raise ValueError('Measurement schema_version must be 1')
    if not isinstance(event.get('event_id'), str) or not EVENT_ID.fullmatch(event['event_id']):
        raise ValueError('event_id must be a stable lowercase slug')
    if event.get('stage') not in STAGES:
        raise ValueError('Unknown measurement stage')
    for group, fields in [('workload', WORKLOAD_FIELDS), ('agent', ('provider', 'model', 'plugin'))]:
        if not isinstance(event.get(group), dict):
            raise ValueError('Missing ' + group)
        if any(not isinstance(event[group].get(key), str) or not event[group][key].strip() for key in fields):
            raise ValueError(group + ' requires ' + ', '.join(fields))
    if any(not re.fullmatch(r'[0-9a-f]{64}', event['workload'][key])
           for key in ('fixture_sha256', 'source_sha256', 'coverage_sha256')):
        raise ValueError('Workload fingerprints must be SHA-256 hex digests')
    measurements = event.get('measurements')
    if not isinstance(measurements, dict):
        raise ValueError('measurements must be an object')
    validate_numbers(measurements)
    usage = event.get('usage')
    if not isinstance(usage, dict) or usage.get('availability') not in ('reported', 'unavailable'):
        raise ValueError('usage availability must be reported or unavailable')
    validate_usage(usage)
    return event


def validate_numbers(measurements):
    for key in ('elapsed_seconds',) + COUNTER_FIELDS:
        value = measurements.get(key)
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(key + ' must be nonnegative and finite, or null')
        if key in COUNTER_FIELDS and not isinstance(value, int):
            raise ValueError(key + ' must be an integer')


def validate_usage(usage):
    if usage['availability'] == 'unavailable':
        if any(usage.get(key) is not None for key in TOKEN_FIELDS):
            raise ValueError('Unavailable tokens cannot have numeric values')
        if not isinstance(usage.get('reason'), str) or not usage['reason'].strip():
            raise ValueError('Unavailable usage needs a reason')
        return
    if not isinstance(usage.get('origin'), str) or not usage['origin'].strip():
        raise ValueError('Reported usage needs its counter origin')
    if not isinstance(usage.get('counter_id'), str) or not usage['counter_id'].strip():
        raise ValueError('Reported usage needs a stable provider request/task counter_id')
    for key in TOKEN_FIELDS:
        value = usage.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(key + ' must be a nonnegative integer, or null')
    if all(usage.get(key) is None for key in TOKEN_FIELDS):
        raise ValueError('Reported usage needs at least one counter')
    inputs, outputs, cached, total = (usage.get(key) for key in TOKEN_FIELDS)
    if cached is not None and inputs is not None and cached > inputs:
        raise ValueError('Cached input is a subset of input, not an additional token total')
    minimum = (inputs if inputs is not None else cached or 0) + (outputs or 0)
    if total is not None and total < minimum:
        raise ValueError('total_tokens is below the known input/output lower bound')
    if inputs is not None and outputs is not None and total is not None and total != inputs + outputs:
        raise ValueError('total_tokens must equal input_tokens plus output_tokens')


def record(input_path, output):
    input_path = input_path.resolve()
    event = validate_measurement(read_json(input_path))
    document = {'measurement': event, 'recorded_input': {'path': str(input_path), 'sha256': digest(input_path)}}
    output.mkdir(parents=True, exist_ok=True)
    target = output / (event['event_id'] + '.json')
    if target.exists():
        if read_json(target) != document:
            raise ValueError('Existing event changed; retain it and use a new event_id')
        return target
    with target.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(document, indent=2, allow_nan=False) + '\n')
    return target


def load_events(directory):
    events = []
    for path in sorted(directory.glob('*.json')):
        document = read_json(path)
        if not isinstance(document, dict):
            raise ValueError('Recorded event must be an object: ' + str(path))
        event = validate_measurement(document.get('measurement'))
        bound = document.get('recorded_input', {})
        if not isinstance(bound, dict) or not isinstance(bound.get('path'), str):
            raise ValueError('Recorded event needs its input identity: ' + str(path))
        source = Path(bound.get('path', ''))
        if not source.is_file() or digest(source) != bound.get('sha256'):
            raise ValueError('Measurement input changed: ' + str(path))
        if read_json(source) != event:
            raise ValueError('Recorded measurement changed: ' + str(path))
        events.append(event)
    if not events:
        raise ValueError('No measurement events')
    return events


def homogeneous(events):
    workload = events[0]['workload']
    agent = events[0]['agent']
    if any(event['workload'] != workload or event['agent'] != agent for event in events):
        raise ValueError('One summary requires the same workload, provider/model and plugin')
    if len({event['event_id'] for event in events}) != len(events):
        raise ValueError('Duplicate event_id')
    if sum(event['stage'] == 'task_total' for event in events) > 1:
        raise ValueError('Only one whole-task total is permitted per workload ledger')
    counters = [('task_total' if event['stage'] == 'task_total' else 'stage', event['usage']['counter_id'])
                for event in events if event['usage']['availability'] == 'reported']
    if len(counters) != len(set(counters)):
        raise ValueError('Provider counter reused across stage events; do not sum cumulative snapshots')
    return workload, agent


def complete_sum(events, group, key):
    values = [event[group].get(key) for event in events]
    return sum(values) if values and all(value is not None for value in values) else None


def stage_summary(events):
    reported = [event for event in events if event['usage']['availability'] == 'reported']
    tokens = {key: complete_sum(reported, 'usage', key) if len(reported) == len(events) else None
              for key in TOKEN_FIELDS}
    return {'events': len(events), 'measurements': {key: complete_sum(events, 'measurements', key)
            for key in ('elapsed_seconds',) + COUNTER_FIELDS}, 'tokens': tokens,
            'usage_available_events': len(reported), 'usage_unavailable_events': len(events) - len(reported)}


def summarize(directory):
    events = load_events(directory)
    workload, agent = homogeneous(events)
    stages = {stage: stage_summary([event for event in events if event['stage'] == stage])
              for stage in STAGES if any(event['stage'] == stage for event in events)}
    return {'schema_version': 1, 'workload': workload, 'agent': agent, 'stages': stages,
            'notes': ['Counters are recorded measurements, not independently proven provider billing.',
                      'Cached input tokens are included within input tokens; never add them twice.',
                      'task_total is separate from stage counters; overlapping totals are not summed.']}


def compare(before_dir, after_dir):
    before, after = summarize(before_dir), summarize(after_dir)
    if before['workload'] != after['workload']:
        raise ValueError('Comparisons require identical task, fixture, source, coverage and renderer')
    for key in ('provider', 'model'):
        if before['agent'][key] != after['agent'][key]:
            raise ValueError('Comparisons require the same provider and model')
    if before['stages'].keys() != after['stages'].keys():
        raise ValueError('Comparisons require the same recorded stages')
    deltas = {}
    for stage in before['stages']:
        deltas[stage] = {}
        for group in ('measurements', 'tokens'):
            deltas[stage][group] = {}
            for key, first in before['stages'][stage][group].items():
                second = after['stages'][stage][group][key]
                comparable = first is not None and second is not None
                deltas[stage][group][key] = {'before': first, 'after': second,
                    'change': second - first if comparable else None,
                    'reduction_percent': 100 * (first - second) / first if comparable and first > 0 else None}
    return {'before': before, 'after': after, 'deltas': deltas,
            'claim': 'Descriptive counters only; matching workload does not establish statistical significance.'}


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='action', required=True)
    add = commands.add_parser('record')
    add.add_argument('--input', type=Path, required=True)
    add.add_argument('--out', type=Path, required=True)
    summary = commands.add_parser('summary')
    summary.add_argument('--events', type=Path, required=True)
    comparison = commands.add_parser('compare')
    comparison.add_argument('--before', type=Path, required=True)
    comparison.add_argument('--after', type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.action == 'record':
            payload = {'event': str(record(args.input, args.out))}
        elif args.action == 'summary':
            payload = summarize(args.events)
        else:
            payload = compare(args.before, args.after)
        print(json.dumps(payload, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError) as error:
        print(json.dumps({'status': 'ERROR', 'error': str(error)}))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
