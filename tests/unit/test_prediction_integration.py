from pathlib import Path
from Bio.Seq import Seq
from Bio.SeqFeature import SeqFeature, FeatureLocation
from Bio.SeqRecord import SeqRecord
from multigenomic_extractor.application.use_cases import ExtractMultigenomicDirectoryUseCase


def make_record():
    record = SeqRecord(Seq('ATG' * 100), id='NZ_TEST.1', annotations={'organism': 'Escherichia coli'})
    record.features = [
        SeqFeature(FeatureLocation(0, 300), type='source', qualifiers={'organism': ['Escherichia coli'], 'strain': ['K-12']}),
        SeqFeature(FeatureLocation(9, 39, strand=1), type='gene', qualifiers={'locus_tag': ['L1'], 'gene': ['abc']}),
        SeqFeature(FeatureLocation(9, 39, strand=1), type='CDS', qualifiers={'locus_tag': ['L1'], 'gene': ['abc'], 'protein_id': ['P1'], 'translation': ['M' * 10]}),
    ]
    return record


class Reader:
    def find_files(self, input_path):
        return [input_path / 'NZ_TEST.gb']

    def parse_records(self, source_file):
        yield make_record()


class Writer:
    def write_collection(self, **kwargs):
        pass


class Progress:
    def update(self, step=1):
        pass

    def finish(self):
        pass



def test_use_case_exposes_protein_gene_index(tmp_path):
    use_case = ExtractMultigenomicDirectoryUseCase(
        Reader(),
        Writer(),
        lambda _: Progress(),
    )

    use_case.execute(str(tmp_path), str(tmp_path / "out"))

    record = make_record()

    from multigenomic_extractor.domain.predictions import (
        build_protein_gene_index,
    )

    gene_id_map = {"L1": "L1"}
    protein_index, warnings = build_protein_gene_index(
        record,
        gene_id_map,
    )

    assert protein_index["P1"]["gene_id"] == "L1"
    assert protein_index["P1"]["molecule"] == "NZ_TEST.1"
    assert warnings == []

