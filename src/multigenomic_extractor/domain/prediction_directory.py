"""Discover prediction files by assembly accession, without guessing matches."""
from pathlib import Path
import re

_PATTERN = re.compile(r'^(GC[AF]_\d{9})(?:\.\d+)?\.pred(?:\.bz2)?$')


def find_prediction_files(directory: str | Path) -> dict[str, Path]:
    root = Path(directory)
    if not root.is_dir():
        raise NotADirectoryError(f'Prediction directory does not exist: {root}')
    matches: dict[str, Path] = {}
    for path in sorted(root.iterdir()):
        if not path.is_file():
            continue
        match = _PATTERN.fullmatch(path.name)
        if match is None:
            continue
        assembly = match.group(1)
        if assembly in matches:
            raise ValueError(f'Multiple prediction files for {assembly}: {matches[assembly]} and {path}')
        matches[assembly] = path
    return matches


def record_assembly_ids(record) -> set[str]:
    """Only accept explicit assembly identifiers present in GenBank metadata."""
    strings = list(getattr(record, 'dbxrefs', ()) or ())
    annotations = getattr(record, 'annotations', {}) or {}
    for value in annotations.get('dbxrefs', ()) or ():
        strings.append(str(value))
    for value in annotations.get('structured_comment', {}).values():
        if isinstance(value, dict):
            strings.extend(str(v) for v in value.values())
    ids = set()
    for value in strings:
        ids.update(re.findall(r'\bGC[AF]_\d{9}(?:\.\d+)?\b', str(value)))
    return {re.match(r'GC[AF]_\d{9}', value).group() for value in ids}
