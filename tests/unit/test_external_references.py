import pytest

from multigenomic_extractor.domain.external_references import (
    extract_external_references,
    resolve_external_references,
)

REFSEQ_ID = "RDBECOLIERC00049"
NCBI_REFSEQ_PRO_ID = "RDBECOLIERC00036"

# IDs de prueba. Los identificadores definitivos de estas
# bases deben obtenerse del catálogo de MongoDB.
RFAM_ID = "TEST_RFAM_ID"
NCBI_TAXONOMY_ID = "TEST_NCBI_TAXONOMY_ID"


def test_extract_refseq_protein_id():
    qualifiers = {
        "protein_id": ["WP_001234567.1"],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "WP_001234567.1",
        }
    ]


def test_extract_refseq_from_inference():
    qualifiers = {
        "inference": [
            "similar to AA sequence:RefSeq:NP_123456.2",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "REFSEQ",
            "objectId": "NP_123456.2",
        }
    ]


def test_extract_deduplicates_references():
    qualifiers = {
        "protein_id": [
            "WP_001234567.1",
            "WP_001234567.1",
        ],
        "inference": [
            "similar to AA sequence:RefSeq:WP_001234567.1",
            "similar to AA sequence:RefSeq:WP_001234567.1",
            "similar to AA sequence:RefSeq:NP_123456.2",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "WP_001234567.1",
        },
        {
            "database": "REFSEQ",
            "objectId": "WP_001234567.1",
        },
        {
            "database": "REFSEQ",
            "objectId": "NP_123456.2",
        },
    ]


def test_resolve_external_references():
    qualifiers = {
        "protein_id": ["WP_001234567.1"],
    }

    database_ids = {
        "NCBI-REFSEQ-PRO": NCBI_REFSEQ_PRO_ID,
    }

    result = resolve_external_references(
        qualifiers,
        database_ids,
    )

    assert result == [
        {
            "externalCrossReferences_id": NCBI_REFSEQ_PRO_ID,
            "objectId": "WP_001234567.1",
        }
    ]


def test_resolve_refseq_from_inference():
    qualifiers = {
        "inference": [
            "similar to AA sequence:RefSeq:NP_123456.2",
        ],
    }

    database_ids = {
        "REFSEQ": REFSEQ_ID,
    }

    result = resolve_external_references(
        qualifiers,
        database_ids,
    )

    assert result == [
        {
            "externalCrossReferences_id": REFSEQ_ID,
            "objectId": "NP_123456.2",
        }
    ]


def test_missing_database_id_raises_error():
    qualifiers = {
        "protein_id": ["WP_001234567.1"],
    }

    with pytest.raises(
        ValueError,
        match="Missing externalCrossReferences_id for NCBI-REFSEQ-PRO",
    ):
        resolve_external_references(
            qualifiers,
            {},
        )


def test_non_refseq_protein_id_is_preserved():
    qualifiers = {
        "protein_id": ["ABC12345.1"],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "ABC12345.1",
        }
    ]


def test_extract_rfam_reference():
    qualifiers = {
        "db_xref": [
            "RFAM:RF00177",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "RFAM",
            "objectId": "RF00177",
        }
    ]


def test_extract_taxonomy_reference():
    qualifiers = {
        "db_xref": [
            "taxon:562",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "NCBI-TAXONOMY",
            "objectId": "562",
        }
    ]


def test_ignore_unsupported_database_references():
    qualifiers = {
        "db_xref": [
            "GeneID:12345",
            "GI:987654",
            "UniProtKB/Swiss-Prot:P12345",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == []


def test_extract_multiple_database_references():
    qualifiers = {
        "protein_id": [
            "WP_001234567.1",
        ],
        "inference": [
            "similar to AA sequence:RefSeq:NP_123456.2",
        ],
        "db_xref": [
            "RFAM:RF00177",
            "taxon:562",
        ],
    }

    result = extract_external_references(qualifiers)

    assert result == [
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "WP_001234567.1",
        },
        {
            "database": "REFSEQ",
            "objectId": "NP_123456.2",
        },
        {
            "database": "RFAM",
            "objectId": "RF00177",
        },
        {
            "database": "NCBI-TAXONOMY",
            "objectId": "562",
        },
    ]


def test_resolve_multiple_database_references():
    qualifiers = {
        "protein_id": [
            "WP_001234567.1",
        ],
        "inference": [
            "similar to AA sequence:RefSeq:NP_123456.2",
        ],
        "db_xref": [
            "RFAM:RF00177",
        ],
    }

    database_ids = {
        "NCBI-REFSEQ-PRO": NCBI_REFSEQ_PRO_ID,
        "REFSEQ": REFSEQ_ID,
        "RFAM": RFAM_ID,
    }

    result = resolve_external_references(
        qualifiers,
        database_ids,
    )

    assert result == [
        {
            "externalCrossReferences_id": NCBI_REFSEQ_PRO_ID,
            "objectId": "WP_001234567.1",
        },
        {
            "externalCrossReferences_id": REFSEQ_ID,
            "objectId": "NP_123456.2",
        },
        {
            "externalCrossReferences_id": RFAM_ID,
            "objectId": "RF00177",
        },
    ]


def test_resolve_taxonomy_reference():
    qualifiers = {
        "db_xref": [
            "taxon:562",
        ],
    }

    result = resolve_external_references(
        qualifiers,
        {
            "NCBI-TAXONOMY": NCBI_TAXONOMY_ID,
        },
    )

    assert result == [
        {
            "externalCrossReferences_id": NCBI_TAXONOMY_ID,
            "objectId": "562",
        }
    ]


def test_resolve_database_names_case_insensitively():
    qualifiers = {
        "protein_id": [
            "WP_001234567.1",
        ],
    }

    result = resolve_external_references(
        qualifiers,
        {
            "ncbi-refseq-pro": NCBI_REFSEQ_PRO_ID,
        },
    )

    assert result == [
        {
            "externalCrossReferences_id": NCBI_REFSEQ_PRO_ID,
            "objectId": "WP_001234567.1",
        }
    ]
def test_missing_reference_is_skipped_with_callback():
    qualifiers = {
        "protein_id": ["WP_001234567.1"],
        "db_xref": ["RFAM:RF00177"],
    }

    warnings = []

    result = resolve_external_references(
        qualifiers,
        {
            "NCBI-REFSEQ-PRO": NCBI_REFSEQ_PRO_ID,
        },
        on_missing=lambda database, object_id: warnings.append(
            (database, object_id)
        ),
    )

    assert result == [
        {
            "externalCrossReferences_id": NCBI_REFSEQ_PRO_ID,
            "objectId": "WP_001234567.1",
        }
    ]

    assert warnings == [
        ("RFAM", "RF00177"),
    ]


def test_all_missing_references_return_empty_list():
    qualifiers = {
        "db_xref": ["RFAM:RF00177"],
    }

    warnings = []

    result = resolve_external_references(
        qualifiers,
        {},
        on_missing=lambda database, object_id: warnings.append(
            (database, object_id)
        ),
    )

    assert result == []
    assert warnings == [("RFAM", "RF00177")]
def test_protein_id_accepts_any_accession():
    qualifiers = {
        "protein_id": ["QHG47139.1", "WP_001500294.1"],
    }

    assert extract_external_references(qualifiers) == [
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "QHG47139.1",
        },
        {
            "database": "NCBI-REFSEQ-PRO",
            "objectId": "WP_001500294.1",
        },
    ]


def test_inference_extracts_refseq_identifier():
    qualifiers = {
        "inference": [
            "similar to AA sequence:RefSeq:WP_001500294.1",
            "COORDINATES: similar to AA sequence:RefSeq:NP_123456.1",
        ],
    }

    assert extract_external_references(qualifiers) == [
        {
            "database": "REFSEQ",
            "objectId": "WP_001500294.1",
        },
        {
            "database": "REFSEQ",
            "objectId": "NP_123456.1",
        },
    ]