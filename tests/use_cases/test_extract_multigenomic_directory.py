from pathlib import Path

from multigenomic_extractor.application.use_cases import ExtractMultigenomicDirectoryUseCase


class FakeLocation:
    def __init__(self, start, end, strand=1):
        self.start = start
        self.end = end
        self.strand = strand


class FakeFeature:
    def __init__(self, feature_type, start, end, qualifiers, strand=1):
        self.type = feature_type
        self.location = FakeLocation(start, end, strand)
        self.qualifiers = qualifiers

    def extract(self, sequence):
        return sequence[self.location.start:self.location.end]


class FakeRecord:
    def __init__(self):
        self.seq = "ATGAAACCCGGGTTTAAACCCGGG"
        self.id = "CP000001.1"
        self.annotations = {"organism": "Escherichia coli"}
        self.features = [
            FakeFeature(
                "source",
                0,
                len(self.seq),
                {
                    "organism": ["Escherichia coli"],
                    "strain": ["536"],
                },
            ),
            FakeFeature(
                "gene",
                0,
                9,
                {
                    "gene": ["abcA"],
                    "locus_tag": ["ECP_0001"],
                },
            ),
            FakeFeature(
                "CDS",
                0,
                9,
                {
                    "gene": ["abcA"],
                    "locus_tag": ["ECP_0001"],
                    "protein_id": ["ABC123"],
                    "product": ["ABC transporter"],
                    "translation": ["MKP"],
                },
            ),
            FakeFeature(
                "misc_feature",
                10,
                12,
                {"note": ["not mapped"]},
            ),
        ]


class FakeReader:
    def __init__(self, source_files):
        self.source_files = source_files

    def find_files(self, input_path: Path):
        return self.source_files

    def parse_records(self, source_file: Path):
        return [FakeRecord()]


class FakeWriter:
    def __init__(self):
        self.writes = []

    def write_collection(self, output_path, collection_name, source_file, wrapper_document):
        self.writes.append(
            {
                "output_path": output_path,
                "collection_name": collection_name,
                "source_file": source_file,
                "wrapper_document": wrapper_document,
            }
        )


class FakeProgress:
    def __init__(self, total):
        self.total = total
        self.updates = 0
        self.finished = False

    def update(self, step=1):
        self.updates += step

    def finish(self):
        self.finished = True


created_progress = []


def progress_factory(total):
    progress = FakeProgress(total)
    created_progress.append(progress)
    return progress


def test_extract_multigenomic_directory_groups_documents_by_collection(tmp_path):
    created_progress.clear()
    source_file = tmp_path / "CP000001.gbff"
    source_file.write_text("fake content")

    writer = FakeWriter()
    use_case = ExtractMultigenomicDirectoryUseCase(
        reader=FakeReader([source_file]),
        writer=writer,
        progress_factory=progress_factory,
    )

    result = use_case.execute(
        input_directory=str(tmp_path),
        output_directory=str(tmp_path / "output"),
    )

    assert result == {"documents": 3, "files": 3}
    assert [write["collection_name"] for write in writer.writes] == [
        "organisms",
        "genes",
        "products",
    ]

    genes_wrapper = writer.writes[1]["wrapper_document"]
    assert genes_wrapper["classAcronym"] == "ESCOL"
    assert genes_wrapper["organism"] == "Escherichia coli"
    assert genes_wrapper["strain"] == "536"
    assert genes_wrapper["subClassAcronym"] == "GNC"
    assert genes_wrapper["collectionData"][0]["_id"] == "ECP_0001"
    assert "featureType" not in genes_wrapper["collectionData"][0]

    products_wrapper = writer.writes[2]["wrapper_document"]
    assert products_wrapper["collectionData"][0]["_id"] == "ABC123"
    assert products_wrapper["collectionData"][0]["type"] == "polypeptide"
    assert products_wrapper["collectionData"][0]["sequence"] == "MKP"

    assert created_progress[0].updates == 1
    assert created_progress[0].finished is True
