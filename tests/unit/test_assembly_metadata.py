from pathlib import Path
import pytest
from multigenomic_extractor.domain.assembly_metadata import (
    normalize_molecule, read_assembly_metadata,
)


def test_normalizes_refseq_genbank_versions():
    assert normalize_molecule('NZ_CP023061.1') == 'CP023061'
    assert normalize_molecule('CP023061') == 'CP023061'


def test_reads_assemblies_and_multiple_molecules(tmp_path: Path):
    path = tmp_path / 'metadata.tsv'
    path.write_text(
        'genbank_assembly_accession\trefseq_assembly_accession\t'
        'replicon_genbank_accessions\treplicon_refseq_accessions\n'
        'GCA_013146725.1\t\tCP049163,CP049164\t\n'
        'GCA_003491165.1\tGCF_003491165.1\tCP023061\tNZ_CP023061.1\n'
    )
    index = read_assembly_metadata(path)
    assert index['CP049163'] == {'GCA_013146725'}
    assert index['CP049164'] == {'GCA_013146725'}
    assert index['CP023061'] == {'GCA_003491165', 'GCF_003491165'}


def test_missing_columns_fails(tmp_path: Path):
    path = tmp_path / 'bad.tsv'
    path.write_text('genbank_assembly_accession\nGCA_013146725.1\n')
    with pytest.raises(ValueError, match='missing columns'):
        read_assembly_metadata(path)
