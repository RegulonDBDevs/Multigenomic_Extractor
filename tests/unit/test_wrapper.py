from multigenomic_extractor.domain.wrapper import build_collection_wrapper


def test_build_collection_wrapper_keeps_expected_structure():
    wrapper = build_collection_wrapper(
        collection_name="genes",
        class_acronym="ESCOL",
        organism_name="Escherichia coli",
        strain_name="536",
        documents=[{"_id": "gene_1"}],
    )

    assert wrapper == {
        "classAcronym": "ESCOL",
        "collectionName": "genes",
        "subClassAcronym": "GNC",
        "organism": "Escherichia coli",
        "strain": "536",
        "collectionData": [{"_id": "gene_1"}],
    }
