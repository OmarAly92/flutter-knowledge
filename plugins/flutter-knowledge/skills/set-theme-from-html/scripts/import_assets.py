import argparse
import base64
import binascii
import hashlib
import io
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


RESOURCE_LIMIT = 16 * 1024 * 1024
TOTAL_LIMIT = 128 * 1024 * 1024


def approved_url(url):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or parsed.username or parsed.password:
        raise ValueError('unsupported or credential-bearing remote URL')
    return url


class BoundedRedirects(urllib.request.HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def redirect_request(self, request, response, code, message, headers, url):
        return super().redirect_request(request, response, code, message, headers, approved_url(url))


def bounded_read(stream, limit):
    payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ValueError('resource exceeds resource/invocation byte limit')
    return payload


def resource_bytes(asset, limit):
    url = asset['url']
    if not urllib.parse.urlsplit(url).scheme:
        if not asset.get('base'):
            raise ValueError('relative resource requires its actual document/CSS base URL')
        url = urllib.parse.urljoin(asset['base'], url)
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme == 'data':
        header, encoded = url.split(',', 1)
        if len(encoded) > limit * 4:
            raise ValueError('encoded resource exceeds limit')
        payload = (base64.b64decode(urllib.parse.unquote_to_bytes(encoded), validate=True)
                   if header.endswith(';base64') else urllib.parse.unquote_to_bytes(encoded))
        if len(payload) > limit:
            raise ValueError('resource exceeds resource/invocation byte limit')
        return payload
    if parsed.scheme == 'file':
        if parsed.netloc not in {'', 'localhost'}:
            raise ValueError('nonlocal file host is unsupported')
        with Path(urllib.parse.unquote(parsed.path)).open('rb') as stream:
            return bounded_read(stream, limit)
    approved_url(url)
    opener = urllib.request.build_opener(BoundedRedirects())
    with opener.open(url, timeout=15) as stream:
        return bounded_read(stream, limit)


def svg_metadata(payload):
    if b'<!DOCTYPE' in payload.upper() or b'<!ENTITY' in payload.upper() or b'<?xml-stylesheet' in payload.lower():
        raise ValueError('SVG external entities/document types are unsupported')
    root = ET.fromstring(payload)
    if root.tag != '{http://www.w3.org/2000/svg}svg':
        raise ValueError('SVG requires an explicit SVG namespace')
    ids = {node.attrib['id'] for node in root.iter() if 'id' in node.attrib}
    references = []
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] in {'script', 'foreignObject'}:
            raise ValueError('SVG script/foreignObject requires a portable source export')
        for key, attribute in node.attrib.items():
            if key.lower().startswith('on'):
                raise ValueError('SVG event handlers require a portable source export')
            if key.rsplit('}', 1)[-1] == 'href':
                references.append(attribute)
            references.extend(re.findall(r'url\(\s*[\'\"]?([^\)\'\"]+)', attribute))
        if node.tag.rsplit('}', 1)[-1] == 'style' and node.text:
            references.extend(re.findall(r'url\(\s*[\'\"]?([^\)\'\"]+)', node.text))
            if '@import' in node.text:
                raise ValueError('SVG external stylesheet requires a portable source export')
    if any(not ref.startswith('#') or ref[1:] not in ids for ref in references):
        raise ValueError('SVG has unresolved or external references; preserve and resolve original defs/resources')
    return {'format': 'SVG', 'extension': '.svg', 'currentColor': b'currentcolor' in payload.lower(),
            'viewBox': root.get('viewBox'), 'references': references}


def font_metadata(payload, asset):
    from fontTools.ttLib import TTFont, TTLibError
    try:
        with TTFont(io.BytesIO(payload)) as font:
            cmap = font.getBestCmap() or {}
            required = {ord(char) for char in asset.get('text', '')
                        if unicodedata.category(char) not in {'Cc', 'Cf'}}
            missing = sorted(required - cmap.keys())
            if missing:
                raise ValueError('font misses requested glyphs: ' + ', '.join(f'U+{code:04X}' for code in missing))
            flavor = font.flavor or ('otf' if font.sfntVersion == 'OTTO' else 'ttf')
            names = font['name']
            return {'format': flavor.upper(), 'extension': '.' + flavor,
                    'family': names.getDebugName(1), 'subfamily': names.getDebugName(2),
                    'weight': font['OS/2'].usWeightClass if 'OS/2' in font else None,
                    'glyphCount': len(cmap), 'axes': [{
                        'tag': axis.axisTag, 'min': axis.minValue, 'default': axis.defaultValue,
                        'max': axis.maxValue} for axis in font['fvar'].axes] if 'fvar' in font else []}
    except (TTLibError, KeyError, EOFError, AssertionError) as error:
        raise ValueError('invalid or unsupported font bytes') from error


def resource_metadata(payload, asset):
    if asset['kind'] == 'fonts':
        return font_metadata(payload, asset)
    if payload.removeprefix(b'\xef\xbb\xbf').lstrip().startswith((b'<svg', b'<?xml', b'<!--')):
        return svg_metadata(payload)
    from PIL import Image, UnidentifiedImageError
    formats = {'PNG': '.png', 'JPEG': '.jpg', 'GIF': '.gif', 'WEBP': '.webp',
               'BMP': '.bmp', 'TIFF': '.tiff', 'ICO': '.ico'}
    try:
        with Image.open(io.BytesIO(payload)) as image:
            image.verify()
            if image.format not in formats:
                raise ValueError('unsupported raster format')
            return {'format': image.format, 'extension': formats[image.format], 'size': list(image.size)}
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError('invalid or unsupported image bytes') from error


def destination_directory(project, kind):
    folder = project / 'assets' / kind
    if not folder.resolve().is_relative_to(project):
        raise ValueError('asset directory escapes project through a symlink')
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def import_payload(project, asset, payload, metadata):
    folder = destination_directory(project, asset['kind'])
    digest = hashlib.sha256(payload).hexdigest()
    for existing in sorted(folder.rglob('*')):
        if (existing.is_file() and not existing.is_symlink()
                and existing.resolve().is_relative_to(project)
                and existing.suffix.lower() == metadata['extension']):
            if existing.stat().st_size == len(payload) and hashlib.sha256(existing.read_bytes()).hexdigest() == digest:
                return {'path': existing.relative_to(project).as_posix(), 'status': 'reused', 'sha256': digest}
    destination = folder / (asset['name'] + metadata['extension'])
    if destination.exists() or destination.is_symlink():
        destination = folder / (asset['name'] + '_' + digest[:12] + metadata['extension'])
    if destination.exists() or destination.is_symlink():
        raise ValueError('hash-suffixed destination already exists with different bytes')
    with destination.open('xb') as stream:
        stream.write(payload)
    return {'path': destination.relative_to(project).as_posix(), 'status': 'created', 'sha256': digest}


def validate_manifest(manifest):
    if not isinstance(manifest, dict) or not isinstance(manifest.get('assets'), list):
        raise ValueError('manifest requires an assets list')
    seen = set()
    for asset in manifest['assets']:
        if not isinstance(asset, dict) or not isinstance(asset.get('id'), str) or not asset['id']:
            raise ValueError('each resource requires a unique string id')
        if asset['id'] in seen:
            raise ValueError('duplicate resource id')
        seen.add(asset['id'])
        if asset.get('kind') not in {'images', 'icons', 'fonts'}:
            raise ValueError('kind must be images, icons or fonts')
        if not isinstance(asset.get('name'), str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,79}', asset['name']):
            raise ValueError('name must be a safe readable basename')
        if not isinstance(asset.get('url'), str) or not asset['url']:
            raise ValueError('resource requires a URL')
        if 'base' in asset and not isinstance(asset['base'], str):
            raise ValueError('base must be its source URL')
        if 'text' in asset and not isinstance(asset['text'], str):
            raise ValueError('font text must be a string')


def import_manifest(manifest, project):
    validate_manifest(manifest)
    project = project.resolve()
    if not project.is_dir():
        raise ValueError('project directory is missing')
    rows = []
    total = 0
    for asset in manifest['assets']:
        try:
            if total >= TOTAL_LIMIT:
                raise ValueError('invocation reached 128 MiB; remaining resources require a scoped retry')
            payload = resource_bytes(asset, min(RESOURCE_LIMIT, TOTAL_LIMIT - total))
            total += len(payload)
            metadata = resource_metadata(payload, asset)
            reference = urllib.parse.urljoin(asset.get('base', ''), asset['url'])
            reference_hash = hashlib.sha256(reference.encode()).hexdigest()
            rows.append({'id': asset['id'], 'kind': asset['kind'], 'reference_sha256': reference_hash, **metadata,
                         **import_payload(project, asset, payload, metadata)})
        except (ValueError, OSError, ET.ParseError, binascii.Error, urllib.error.URLError) as error:
            if isinstance(error, urllib.error.HTTPError):
                error.close()
            if isinstance(error, (OSError, urllib.error.URLError)):
                message = 'resource could not be read/fetched or destination could not be written'
            else:
                message = str(error)
            rows.append({'id': asset['id'], 'kind': asset['kind'], 'status': 'error', 'error': message})
    return {'assets': rows, 'bytesRead': total,
            'errors': sum(row['status'] == 'error' for row in rows)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text())
        report = import_manifest(manifest, args.project.resolve())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(f"Imported {len(report['assets']) - report['errors']} resources; {report['errors']} errors")
        return 1 if report['errors'] else 0
    except (OSError, ValueError, ImportError):
        print('Invalid input/project/report or missing Pillow/fontTools; inspect supplied inputs and installed dependencies', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
