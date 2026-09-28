#!/usr/bin/env python3
"""Compare versions on the same tasks, from the grades.json that grade.py wrote.

Usage: compare.py <out_dir> [--versions master,pr] [--modes forced,desc]

Only (mode, task) cells that every compared version has runs for are counted, so a
version with extra runs (d4, nowrap, ...) is not judged on tasks the others skipped.
Prints rule breaks, translation outcomes, tokens, skill files read, runs breaking each
rule, and a two-sided permutation test on rule breaks per run for each pair of versions.
"""
import argparse, itertools, json, os, random
from collections import defaultdict


def perm_p(a, b, n=20000, seed=1):
    rnd = random.Random(seed)
    obs = abs(sum(a) / len(a) - sum(b) / len(b))
    pool, hits = a + b, 0
    for _ in range(n):
        rnd.shuffle(pool)
        x, y = pool[:len(a)], pool[len(a):]
        if abs(sum(x) / len(x) - sum(y) / len(y)) >= obs - 1e-12:
            hits += 1
    return hits / n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--versions')
    ap.add_argument('--modes')
    a = ap.parse_args()
    g = json.load(open(os.path.join(a.out, 'grades.json'), encoding='utf-8'))
    versions = a.versions.split(',') if a.versions else sorted({r['version'] for r in g.values()})
    modes = set(a.modes.split(',')) if a.modes else {r['mode'] for r in g.values()}
    cells = defaultdict(set)
    for r in g.values():
        if r['mode'] in modes:
            cells[r['version']].add((r['mode'], r['task']))
    common = set.intersection(*(cells[v] for v in versions))
    if not common:
        raise SystemExit('no (mode, task) cell has runs for every version')
    runs = {v: [r for r in g.values() if r['version'] == v and (r['mode'], r['task']) in common] for v in versions}

    print('Cells compared: ' + ', '.join(f'{m} {t}' for m, t in sorted(common)) + '\n')
    rows = [
        ('Runs', lambda rs: len(rs)),
        ('Rule breaks', lambda rs: sum(len(r['violations']) for r in rs)),
        ('Rule breaks per run', lambda rs: f"{sum(len(r['violations']) for r in rs) / len(rs):.2f}"),
        ('Runs using a LocaleKeys key missing from the JSON', lambda rs: sum('locale_key_missing_from_json' in r['violations'] for r in rs)),
        ('Runs with only English in ar.json for new keys', lambda rs: sum(bool(r['info']['ar_placeholder']) and not r['info']['ar_real'] and 'locale_key_missing_from_json' not in r['violations'] for r in rs)),
        ('Runs with real Arabic for new keys', lambda rs: sum(bool(r['info']['ar_real']) for r in rs)),
        ('Mean skill files read', lambda rs: f"{sum(r['info']['skills_read'] for r in rs) / len(rs):.1f}"),
        ('Mean tokens', lambda rs: (lambda t: f'{sum(t) / len(t) / 1000:.1f}k' if t else '-')([r['info']['tokens'] for r in rs if r['info'].get('tokens')])),
    ]
    print('| | ' + ' | '.join(versions) + ' |')
    print('|---|' + '---|' * len(versions))
    for label, f in rows:
        print(f'| {label} | ' + ' | '.join(str(f(runs[v])) for v in versions) + ' |')

    rules = sorted({k for v in versions for r in runs[v] for k in r['violations']})
    if rules:
        print('\nRuns breaking each rule:\n')
        print('| rule | ' + ' | '.join(versions) + ' |')
        print('|---|' + '---|' * len(versions))
        for rule in rules:
            print(f'| {rule} | ' + ' | '.join(f"{sum(rule in r['violations'] for r in runs[v])}/{len(runs[v])}" for v in versions) + ' |')

    print('\nPermutation test on rule breaks per run (two-sided):\n')
    for x, y in itertools.combinations(versions, 2):
        bx = [len(r['violations']) for r in runs[x]]
        by = [len(r['violations']) for r in runs[y]]
        print(f'- {x} vs {y}: {sum(bx) / len(bx):.2f} vs {sum(by) / len(by):.2f} per run, p = {perm_p(bx, by):.4f}')


if __name__ == '__main__':
    main()
