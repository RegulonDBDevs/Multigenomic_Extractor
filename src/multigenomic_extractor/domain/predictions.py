"""Parse predicted transcription units and resolve their GenBank genes."""
from dataclasses import dataclass
from pathlib import Path
import bz2


@dataclass(frozen=True)
class Prediction:
    strand: str
    protein_ids: tuple[str, ...]
    gene_names: tuple[str, ...]
    line_number: int


def read_predictions(path: str | Path) -> list[Prediction]:
    path = Path(path)
    opener = bz2.open if path.suffix == '.bz2' else open
    predictions = []
    with opener(path, 'rt', encoding='utf-8') as stream:
        for line_number, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            parts = line.split('\t')
            if len(parts) != 3:
                raise ValueError(f'{path}:{line_number}: expected 3 tab-separated columns')
            strand, proteins, names = parts
            if strand not in {'F', 'R'}:
                raise ValueError(f'{path}:{line_number}: invalid strand {strand!r}')
            protein_ids = tuple(p.strip() for p in proteins.split(','))
            gene_names = tuple(n.strip() for n in names.split(','))
            if not all(protein_ids) or len(protein_ids) != len(gene_names):
                raise ValueError(f'{path}:{line_number}: invalid protein/gene pairs')
            predictions.append(Prediction('forward' if strand == 'F' else 'reverse', protein_ids, gene_names, line_number))
    return predictions


def build_protein_gene_index(record, gene_id_map: dict[str, str]) -> tuple[dict[str, dict], list[str]]:
    """Return protein_id -> resolved gene metadata, plus unresolved/ambiguous warnings.

    Uses locus_tag preferentially, then gene name; never guesses from coordinates.
    Coordinates use Biopython's zero-based, end-exclusive convention.
    """
    gene_by_locus = {}
    gene_by_name = {}
    for feature in record.features:
        if feature.type != 'gene':
            continue
        q = feature.qualifiers
        locus = (q.get('locus_tag') or [None])[0]
        name = (q.get('gene') or [None])[0]
        original = locus or name or f"gene_{int(feature.location.start)}_{int(feature.location.end)}"
        resolved = gene_id_map.get(original)
        if not resolved:
            continue
        entry = {'gene_id': resolved, 'molecule': record.id,
                 'start': int(feature.location.start), 'end': int(feature.location.end),
                 'strand': 'forward' if feature.location.strand == 1 else 'reverse' if feature.location.strand == -1 else None}
        if locus:
            gene_by_locus.setdefault(locus, []).append(entry)
        if name:
            gene_by_name.setdefault(name, []).append(entry)
    index, warnings = {}, []
    for feature in record.features:
        if feature.type != 'CDS':
            continue
        q = feature.qualifiers
        protein = (q.get('protein_id') or [None])[0]
        if not protein:
            continue
        locus = (q.get('locus_tag') or [None])[0]
        name = (q.get('gene') or [None])[0]
        candidates = gene_by_locus.get(locus, []) if locus else []
        if not candidates and name:
            candidates = gene_by_name.get(name, [])
        if len(candidates) != 1 or protein in index:
            warnings.append(f'{record.id}: protein_id {protein}: unresolved or ambiguous gene')
            index.pop(protein, None)
            continue
        index[protein] = candidates[0]
    return index, warnings


def resolve_prediction(prediction: Prediction, protein_index: dict[str, dict]):
    """Return gene entries only when all protein IDs resolve uniquely on one molecule."""
    entries = [protein_index.get(pid) for pid in prediction.protein_ids]
    if any(entry is None for entry in entries):
        return None
    if len({entry['molecule'] for entry in entries}) != 1:
        return None
    if len({entry['gene_id'] for entry in entries}) != len(entries):
        return None
    if any(entry['strand'] != prediction.strand for entry in entries):
        return None
    return entries
