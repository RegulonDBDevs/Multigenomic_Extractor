"""Map molecule accessions to assemblies using the input metadata TSV."""
import csv
import re
from pathlib import Path

_ASSEMBLY = re.compile(r"^GC[AF]_\d{9}(?:\.\d+)?$")
_MOLECULE = re.compile(r"^(?:NZ_)?(?:CP|NC_)\d+(?:\.\d+)?$", re.I)


def normalize_assembly(value: str) -> str:
    value = value.strip()
    if not _ASSEMBLY.fullmatch(value):
        raise ValueError(f"Invalid assembly accession: {value!r}")
    return value.split('.')[0]


def normalize_molecule(value: str) -> str:
    """Normalize accession versions and NZ_ prefix for GenBank/RefSeq pairing."""
    value = value.strip().upper()
    if not _MOLECULE.fullmatch(value):
        raise ValueError(f"Invalid molecule accession: {value!r}")
    return value.removeprefix('NZ_').split('.')[0]


def read_assembly_metadata(path: str | Path) -> dict[str, set[str]]:
    """Return molecule -> assembly IDs. Ambiguity is preserved, not guessed."""
    index: dict[str, set[str]] = {}
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream, delimiter='\t')
        required = {'genbank_assembly_accession', 'refseq_assembly_accession',
                    'replicon_genbank_accessions', 'replicon_refseq_accessions'}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Metadata TSV missing columns: {sorted(required - set(reader.fieldnames or []))}")
        for line, row in enumerate(reader, start=2):
            assemblies = {normalize_assembly(row[column]) for column in
                          ('genbank_assembly_accession', 'refseq_assembly_accession')
                          if (row.get(column) or '').strip() and (row.get(column) or '').strip().lower() not in {'unavailable', 'na', 'n/a'}}
            if not assemblies:
                continue
            for column in ('replicon_genbank_accessions', 'replicon_refseq_accessions'):
                for raw in (row.get(column) or '').split(','):
                    if not raw.strip():
                        continue
                    try:
                        molecule = normalize_molecule(raw)
                    except ValueError as exc:
                        raise ValueError(f"TSV line {line}: {exc}") from exc
                    index.setdefault(molecule, set()).update(assemblies)
    return index
