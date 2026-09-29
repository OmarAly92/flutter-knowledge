#!/usr/bin/env python3
"""Set up a benchmark round: fixtures, one project copy per agent run, and the agent prompts.

Usage:
  prepare.py --version master=/path/to/master-checkout --version pr=/path/to/branch-checkout
             [--out benchmark/out] [--only MODE:TASKS:REPS ...] [--fresh]

Each --version is NAME=PATH, where PATH is a checkout of this repo (it must contain skills/).
NAME becomes the first part of every run name, so it must not contain '-'.
Without --only, the default_plan in tasks.json runs (forced x3, desc x1, nowrap x2 on d1/h1).
--only forced:d1,d2:3 runs just that slice; repeat it to add more slices.

Writes into --out:
  fixture-*/                     the fixture projects (from build_fixtures.py)
  skill-index-<NAME>.md          skill names + descriptions, for description-only mode
  runs/<NAME>-<MODE>-<TASK>-rN/  one fresh copy of the fixture per agent run
  agents.jsonl                   one {"run", "description", "prompt"} per run to launch
Existing run directories are left alone (and not listed again) unless --fresh is given.
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def frontmatter(path):
    text = open(path, encoding='utf-8').read()
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    fields = {}
    for line in (m.group(1) if m else '').splitlines():
        k, _, v = line.partition(':')
        if v:
            fields[k.strip()] = v.strip().strip('"\'')
    return fields


def skill_index(version_path, out_file):
    rows = []
    skills = os.path.join(version_path, 'skills')
    for name in sorted(os.listdir(skills)):
        p = os.path.join(skills, name, 'SKILL.md')
        if os.path.exists(p):
            rows.append(f"- **{name}**: {frontmatter(p).get('description', '')}")
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write('# Available skills\n\nEach skill is listed as name: description. '
                'To invoke one, read <VERSION>/skills/<name>/SKILL.md in full.\n\n' + '\n'.join(rows) + '\n')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--version', action='append', required=True, help='NAME=PATH')
    ap.add_argument('--out', default=os.path.join(HERE, 'out'))
    ap.add_argument('--only', action='append', help='MODE:TASK,TASK:REPS')
    ap.add_argument('--fresh', action='store_true', help='recreate run directories that already exist')
    a = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, 'tasks.json'), encoding='utf-8'))
    out = os.path.abspath(a.out)
    runs_dir = os.path.join(out, 'runs')
    os.makedirs(runs_dir, exist_ok=True)

    versions = []
    for v in a.version:
        name, _, path = v.partition('=')
        path = os.path.abspath(path)
        if not name or '-' in name or not os.path.isdir(os.path.join(path, 'skills')):
            sys.exit(f'bad --version {v!r}: need NAME=PATH, NAME without "-", PATH containing skills/')
        versions.append((name, path))

    if a.only:
        plan = []
        for spec in a.only:
            mode, tasks, reps = spec.split(':')
            plan.append({'mode': mode, 'tasks': tasks.split(','), 'reps': int(reps)})
    else:
        plan = cfg['default_plan']
    for step in plan:
        if step['mode'] not in cfg['modes'] or any(t not in cfg['tasks'] for t in step['tasks']):
            sys.exit(f'unknown mode or task in {step}')

    def fixture(task, mode):
        t = cfg['tasks'][task]
        return os.path.join(out, f"fixture-{t.get('fixture', t['engine'])}{cfg['modes'][mode]['fixture']}")

    if not all(os.path.isdir(fixture(task, step['mode'])) for step in plan for task in step['tasks']):
        subprocess.run([sys.executable, os.path.join(HERE, 'build_fixtures.py'), out], check=True)

    agents = []
    for name, path in versions:
        index = os.path.join(out, f'skill-index-{name}.md')
        skill_index(path, index)
        for step in plan:
            mode = cfg['modes'][step['mode']]
            for task in step['tasks']:
                t = cfg['tasks'][task]
                for rep in range(1, step['reps'] + 1):
                    run = f"{name}-{step['mode']}-{task}-r{rep}"
                    run_path = os.path.join(runs_dir, run)
                    if os.path.exists(run_path):
                        if not a.fresh:
                            continue
                        shutil.rmtree(run_path)
                    shutil.copytree(fixture(task, step['mode']), run_path)
                    prompt = cfg['prompts'][mode['prompt']].format(
                        run=run_path, version=path, skill_index=index, task=t['text'])
                    agents.append({'run': run, 'description': f"{name} {step['mode']} {task} r{rep}", 'prompt': prompt})

    with open(os.path.join(out, 'agents.jsonl'), 'w', encoding='utf-8') as f:
        for ag in agents:
            f.write(json.dumps(ag, ensure_ascii=False) + '\n')
    print(f'{len(agents)} runs prepared in {runs_dir}; prompts in {os.path.join(out, "agents.jsonl")}')


if __name__ == '__main__':
    main()
