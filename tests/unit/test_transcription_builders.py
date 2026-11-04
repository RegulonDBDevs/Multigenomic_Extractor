"""Unit tests for predicted TU and operon builders."""

import pytest

from multigenomic_extractor.domain.predictions import Prediction
from multigenomic_extractor.domain.transcription_builders import (
    InvalidTranscriptionPrediction,
    build_transcription_documents,
)

ORG = "RDBMGECOLIOR0000001"
OP = "RDBMGECOLIOP0000001"
TU = "RDBMGECOLITU0000001"
G1 = "RDBMGECOLIGN0000001"
G2 = "RDBMGECOLIGN0000002"


def prediction(strand="forward", proteins=("P1", "P2"), names=("a", "b")):
    return Prediction(strand, proteins, names, 7)


def index(strand="forward"):
    return {
        "P1": {"gene_id": G1, "molecule": "CP1", "start": 10, "end": 30, "strand": strand},
        "P2": {"gene_id": G2, "molecule": "CP1", "start": 35, "end": 60, "strand": strand},
    }


def build(pred=None, idx=None, **kwargs):
    return build_transcription_documents(
        pred if pred is not None else prediction(),
        idx if idx is not None else index(),
        organism_id=kwargs.get("organism_id", ORG),
        operon_id=kwargs.get("operon_id", OP),
        transcription_unit_id=kwargs.get("transcription_unit_id", TU),
    )


def test_multiple_genes_and_required_fields():
    operon, tu = build()
    assert operon == {
        "_id": OP, "name": "a-b", "regulationPositions": {
            "leftEndPosition": 10, "rightEndPosition": 60,
        }, "organisms_id": ORG, "strand": "forward",
    }
    assert tu == {
        "_id": TU, "organisms_id": ORG, "operons_id": OP,
        "genes_ids": [G1, G2], "name": "a-b",
    }


def test_single_gene_reverse():
    operon, tu = build(prediction("reverse", ("P1",), ("uspF",)), index("reverse"))
    assert operon["strand"] == "reverse"
    assert operon["regulationPositions"] == {"leftEndPosition": 10, "rightEndPosition": 30}
    assert tu["genes_ids"] == [G1]


@pytest.mark.parametrize("change", [
    lambda d: d.pop("P2"),
    lambda d: d["P2"].update(molecule="CP2"),
    lambda d: d["P2"].update(strand="reverse"),
    lambda d: d["P2"].update(gene_id=G1),
    lambda d: d["P2"].update(start=70, end=60),
])
def test_reject_unsafe_predictions(change):
    idx = index()
    change(idx)
    with pytest.raises(InvalidTranscriptionPrediction):
        build(idx=idx)


def test_reject_invalid_identifier():
    with pytest.raises(InvalidTranscriptionPrediction):
        build(operon_id="not-an-rdb-id")


def test_fallback_name_does_not_change_gene_matching():
    _, tu = build(prediction(names=()))
    assert tu["name"] == f"{G1}-{G2}"
    assert tu["genes_ids"] == [G1, G2]
