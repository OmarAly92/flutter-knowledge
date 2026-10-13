import re
from pathlib import Path
from urllib.parse import unquote

from checks import finding


def local_links(cell, report_path):
    links = re.findall(r'\]\((?:<([^>]+)>|([^\s)]+))\)', cell)
    paths = []
    for wrapped, plain in links:
        target = unquote(wrapped or plain)
        if '://' in target or target.startswith('#'):
            continue
        artifact = report_path.parent / target.split('#')[0]
        if artifact.suffix.lower() == '.png':
            paths.append(artifact.resolve())
    return paths


def percentage(cell):
    match = re.fullmatch(r'\s*(\d+(?:\.\d+)?)%\s*', cell)
    if not match or not 0 <= float(match[1]) <= 100:
        raise ValueError('Both difference cells must contain a percentage between 0% and 100%')
    return float(match[1])


def inspect_design(project, screens, report_file):
    if not screens:
        return [], [], {'name': 'design_evidence', 'status': 'skipped', 'reason': 'No explicit design screen/state scope; reviewer must establish applicability from the task'}
    path = project / report_file
    hits, results = [], []
    try:
        text = path.read_text(encoding='utf-8')
    except OSError as error:
        return [finding('design_evidence', 'blocking', f'Missing/unreadable design report: {error}', str(report_file))], [], {'name': 'design_evidence', 'status': 'failed'}
    rows = {}
    for line in text.splitlines():
        if line.strip().startswith('|'):
            cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
            if len(cells) == 7:
                rows.setdefault(cells[0], []).append(cells)
    for screen in dict.fromkeys(screens):
        try:
            matches = rows.get(screen, [])
            if len(matches) != 1:
                raise ValueError('Expected exactly one seven-column evidence row for this screen/state')
            row = matches[0]
            if not row[6].startswith('VERIFIED') or (len(row[6]) > 8 and row[6][8].isalpha()):
                raise ValueError('Design status remains ' + row[6])
            reference = local_links(row[1], path)
            captures = local_links(row[3], path)
            if len(reference) != 1 or len(captures) != 2:
                raise ValueError('Link one local reference PNG and two local Flutter/diff PNGs; source URLs can accompany the reference')
            artifacts = reference + captures
            if len(set(artifacts)) != 3:
                raise ValueError('Reference, Flutter capture and diff must be distinct files')
            for artifact in artifacts:
                if artifact.suffix.lower() != '.png' or not artifact.is_file() or artifact.stat().st_size == 0:
                    raise ValueError('Missing or empty PNG artifact: ' + str(artifact))
            if not row[2]:
                raise ValueError('Capture profile is missing')
            overall, worst = percentage(row[4]), percentage(row[5])
            results.append({'screen': screen, 'overall_percent': overall, 'worst_region_percent': worst, 'status': 'evidence_present_unverified', 'artifacts': [str(item) for item in artifacts]})
            hits.append(finding('design_inspection', 'review', f'{screen}: evidence present ({overall:.2f}% overall, {worst:.2f}% worst region). Inspect PNG contents, matching dimensions/profile, source identity, comparison output/settings and freshness. Reported values are not independently recomputed.', str(report_file)))
        except (ValueError, OSError) as error:
            hits.append(finding('design_evidence', 'blocking', f'{screen}: {error}', str(report_file)))
    status = 'failed' if any(hit['severity'] == 'blocking' for hit in hits) else 'manual'
    return hits, results, {'name': 'design_evidence', 'status': status, 'reason': 'Presence checks only; visual fidelity and complete task coverage require inspection'}
