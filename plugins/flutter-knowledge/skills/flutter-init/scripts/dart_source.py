from dataclasses import dataclass


@dataclass(frozen=True)
class DartString:
    text: str
    start: int
    end: int
    interpolated: bool


GENERATED_SUFFIXES = ('.g.dart', '.freezed.dart', '.mocks.dart', '.gr.dart', '.gen.dart')


def authored_dart(path):
    return path.suffix == '.dart' and not path.name.endswith(GENERATED_SUFFIXES) and not path.is_symlink()


def blank_span(mask, start, end):
    for index in range(start, end):
        if mask[index] not in '\r\n':
            mask[index] = ' '


def comment_end(text, start):
    if text.startswith('//', start):
        newline = text.find('\n', start)
        return len(text) if newline < 0 else newline
    depth, cursor = 1, start + 2
    while cursor < len(text) and depth:
        if text.startswith('/*', cursor):
            depth += 1
            cursor += 2
        elif text.startswith('*/', cursor):
            depth -= 1
            cursor += 2
        else:
            cursor += 1
    return cursor


def expression_end(text, start):
    depth, cursor = 1, start
    while cursor < len(text):
        if text.startswith(('//', '/*'), cursor):
            cursor = comment_end(text, cursor)
        elif text[cursor] in '\'"':
            raw = cursor > 0 and text[cursor - 1] in 'rR'
            _, cursor, _ = string_end(text, cursor, raw)
        elif text[cursor] == '{':
            depth += 1
            cursor += 1
        elif text[cursor] == '}':
            depth -= 1
            if depth == 0:
                return cursor
            cursor += 1
        else:
            cursor += 1
    return cursor


def string_end(text, start, raw):
    quote = text[start]
    delimiter = quote * 3 if text.startswith(quote * 3, start) else quote
    cursor = start + len(delimiter)
    content_start, expressions = cursor, []
    while cursor < len(text):
        if not raw and text[cursor] == '\\':
            cursor += 2
        elif not raw and text.startswith('${', cursor):
            end = expression_end(text, cursor + 2)
            expressions.append((cursor + 2, end))
            cursor = min(len(text), end + 1)
        elif text.startswith(delimiter, cursor):
            return text[content_start:cursor], min(len(text), cursor + len(delimiter)), expressions
        else:
            cursor += 1
    return text[content_start:], len(text), expressions


def scan_dart(text):
    mask, strings, cursor = list(text), [], 0
    while cursor < len(text):
        if text.startswith(('//', '/*'), cursor):
            end = comment_end(text, cursor)
            blank_span(mask, cursor, end)
            cursor = end
        elif text[cursor] in '\'"':
            raw = cursor > 0 and text[cursor - 1] in 'rR' and (cursor < 2 or not text[cursor - 2].isalnum())
            content, end, expressions = string_end(text, cursor, raw)
            start = cursor - 1 if raw else cursor
            strings.append(DartString(content, start, end, not raw and '$' in content))
            blank_span(mask, start, end)
            for first, last in expressions:
                inner_code, inner_strings = scan_dart(text[first:last])
                mask[first:last] = inner_code
                strings.extend(DartString(literal.text, first + literal.start, first + literal.end, literal.interpolated)
                               for literal in inner_strings)
            cursor = end
        else:
            cursor += 1
    return ''.join(mask), sorted(strings, key=lambda literal: literal.start)


def project_sources(project):
    library = project / 'lib'
    if not library.is_dir():
        return []
    sources = []
    for path in sorted(library.rglob('*.dart')):
        if authored_dart(path):
            text = path.read_text(encoding='utf-8')
            code, strings = scan_dart(text)
            sources.append((path.relative_to(project).as_posix(), code, strings))
    return sources
