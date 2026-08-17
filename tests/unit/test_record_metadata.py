from multigenomic_extractor.domain.record_metadata import (
    get_record_organism_id,
    get_record_organism_name,
    get_record_strain_name,
)


class FakeFeature:
    def __init__(self, feature_type, qualifiers):
        self.type = feature_type
        self.qualifiers = qualifiers


class FakeRecord:
    def __init__(self):
        self.features = [
            FakeFeature(
                "source",
                {
                    "organism": ["Escherichia coli"],
                    "strain": ["536"],
                },
            )
        ]
        self.annotations = {}


def test_record_metadata_from_source_feature():
    record = FakeRecord()

    assert get_record_organism_name(record) == "Escherichia coli"
    assert get_record_strain_name(record) == "536"
    assert get_record_organism_id(record) == "organism_Escherichia_coli_536"
