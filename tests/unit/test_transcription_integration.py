"""Integration of resolved predictions into operon/TU JSON wrappers."""
from pathlib import Path

from multigenomic_extractor.application.use_cases import ExtractMultigenomicDirectoryUseCase

ORG = "RDBMGECOLIOR0000001"
GENE = "RDBMGECOLIGN0000001"


class Writer:
    def __init__(self):
        self.writes = []

    def write_collection(self, **kwargs):
        self.writes.append(kwargs)

class Progress:
    def __init__(self):
        self.total = 0

    def update(self, step=1):
        pass

    def finish(self):
        pass

class Identifiers:
    def __init__(self):
        self.calls = []

    def get_or_create(self, *, document, collection_name, organism_name):
        self.calls.append((document.copy(), collection_name, organism_name))
        acronym = "OP" if collection_name == "operons" else "TU"
        return f"RDBMGECOLI{acronym}{len(self.calls):07d}"
    
    def get_or_create_many(
        self,
        *,
        documents,
        collection_name,
        organism_name,
    ):
        if not hasattr(self, "calls"):
            self.calls = []

        self.calls.append(
            (documents, collection_name, organism_name)
        )

        prefix = {
            "operons": "OP",
            "transcriptionUnits": "TU",
        }[collection_name]

        return [
            f"RDBMGECOLI{prefix}{index:07d}"
            for index, _ in enumerate(documents, start=1)
        ]



def test_exports_valid_pair_and_skips_unresolved(tmp_path):
    pred = tmp_path / "GCA_013146725.pred"
    pred.write_text("F\tP1\tgeneA\nF\tMISSING\tunknown\n", encoding="utf-8")
    writer, identifiers = Writer(), Identifiers()
    uc = ExtractMultigenomicDirectoryUseCase(
        None,
        writer,
        lambda total: Progress(),
        identifiers,
    )
    key = ("CP049163.gb", "CP049163.1")
    uc.assembly_gene_indices = {
        "GCA_013146725": {key: {
            "organism_id": ORG,
            "protein_gene_index": {"P1": {
                "gene_id": GENE, "molecule": "CP049163.1",
                "start": 5, "end": 20, "strand": "forward",
            }},
        }}
    }
    uc.assembly_record_info = {key: {
        "source_file": Path("CP049163.gb"), "organism_name": "Escherichia coli",
        "strain_name": "test", "class_acronym": "ECOLI",
    }}
    uc.prediction_warnings = []
    uc.prediction_matches = {key: {"assembly": "GCA_013146725", "path": pred}}
    count, files = uc._export_transcriptions(
        {"GCA_013146725": pred},
        tmp_path,
        assemblies={"GCA_013146725"},
    )
    assert (count, files) == (2, 2)
    assert len(identifiers.calls) == 2
    data = {w["collection_name"]: w["wrapper_document"]["collectionData"]
            for w in writer.writes}
    assert data["transcriptionUnits"][0]["genes_ids"] == [GENE]
    assert data["transcriptionUnits"][0]["operons_id"] == data["operons"][0]["_id"]
    assert len(uc.prediction_warnings) == 1
