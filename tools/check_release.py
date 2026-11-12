"""Verify an exact reviewed snapshot; not a guarantee of privacy or redistribution rights."""
import ast
import csv
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    errors = []
    manifest = root / 'MANIFEST.sha256'
    if manifest.is_symlink():
        return ['Manifest must not be a symlink']
    expected = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        parts = line.split('  ', 1)
        if len(parts) != 2 or not re.fullmatch(r'[a-f0-9]{64}', parts[0]):
            errors.append('Malformed manifest entry')
            continue
        digest, name = parts
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or str(path) != name or '\\' in name or name in expected or name == 'MANIFEST.sha256':
            errors.append('Invalid or duplicate manifest path')
            continue
        expected[name] = digest
    if errors:
        return errors
    allowed_dirs = {str(parent) for name in expected for parent in PurePosixPath(name).parents if str(parent) != '.'}
    actual = {}
    # Do not descend into unexpected directories, virtual environments or links.
    for current, directories, files in os.walk(root, followlinks=False):
        for name in directories[:]:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if path.is_symlink() or rel not in allowed_dirs:
                errors.append(rel + ': unexpected directory or symlink')
                directories.remove(name)
        for name in files:
            path = Path(current) / name
            rel = path.relative_to(root).as_posix()
            if rel != 'MANIFEST.sha256':
                actual[rel] = path
    if set(actual) != set(expected):
        errors.append(f'Inventory mismatch: unexpected={sorted(set(actual)-set(expected))}; missing={sorted(set(expected)-set(actual))}')
    for name, path in actual.items():
        if path.is_symlink():
            errors.append(name + ': symlink')
        elif name in expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected[name]:
            errors.append(name + ': checksum mismatch')
    # Fail before opening unreviewed content or following a redirected data path.
    if errors:
        return errors
    patterns = {
        'machine-specific path': r'(?:/(?:mnt/[a-zA-Z]|home/[^/\s]+|Users/[^/\s]+)/|[A-Za-z]:\\Users\\)',
        'JWT-like token': r'eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]+',
        'AWS access key': r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'private key': r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'credential literal': r'''(?i)["']?(?:password|api_key|access_token|secret_key)["']?\s*[:=]\s*["'][^"'\n]{6,}["']''',
    }
    for name, path in actual.items():
        if path.suffix not in {'.py', '.ipynb', '.csv', '.md', '.txt', '.cff', '.geojson'}:
            continue
        text = path.read_text(encoding='utf-8')
        scan_text = text
        try:
            if path.suffix == '.py':
                ast.parse(text)
            if path.suffix == '.ipynb':
                nb = json.loads(text)
                if set(nb.get('metadata', {})) - {'kernelspec'}:
                    errors.append(name + ': unexpected notebook metadata')
                scan_text = '\n'.join(''.join(c['source']) for c in nb['cells'])
                for cell in nb['cells']:
                    if cell.get('outputs') or cell.get('execution_count') is not None or cell.get('attachments') or cell.get('metadata'):
                        errors.append(name + ': notebook output/metadata/attachment')
                    if cell['cell_type'] == 'code':
                        ast.parse(''.join(cell['source']))
            for label, pattern in patterns.items():
                if re.search(pattern, scan_text):
                    errors.append(name + ': ' + label)
        except (SyntaxError, ValueError, KeyError, TypeError):
            errors.append(name + ': invalid source or notebook structure')
    columns = {}
    with (root / 'docs/CSV_COLUMNS.csv').open(encoding='utf-8', newline='') as handle:
        for row in csv.DictReader(handle):
            columns.setdefault(row['file'], []).append(row['column'])
    if set(columns) != {p.name for p in (root / 'data/summary').glob('*.csv')}:
        errors.append('Summary CSV inventory differs from data dictionary')
    for name, fields in columns.items():
        if name not in {p.name for p in (root / 'data/summary').glob('*.csv')}:
            continue
        with (root / 'data/summary' / name).open(encoding='utf-8', newline='') as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames != fields or len(set(fields)) != len(fields):
                errors.append(name + ': undocumented or duplicated schema')
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    errors.append(name + ': malformed CSV row')
    synthetic = json.loads((root / 'data/synthetic/model_cells.geojson').read_text(encoding='utf-8'))
    allowed = {'grid_id', 'park', 'F_h', 'D_h', 'ps', 'pl', 'pb', 'pm', 'peg', 'peo', 'pep', 'peps', 'per', 'pepw', 'set'}
    if len(synthetic['features']) != 192:
        errors.append('Unexpected synthetic row count')
    for feature in synthetic['features']:
        if set(feature['properties']) != allowed:
            errors.append('Unexpected synthetic fields')
    return errors


def main():
    try:
        errors = check()
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit('FAIL: unreadable or invalid release structure (' + type(error).__name__ + ')')
    if errors:
        raise SystemExit('\n'.join(errors))
    print('PASS: reviewed inventory/checksums, notebook hygiene, syntax, common secret/path patterns and CSV schemas.')
    print('This is a snapshot check, not proof of privacy or third-party redistribution permission.')


if __name__ == '__main__':
    main()
