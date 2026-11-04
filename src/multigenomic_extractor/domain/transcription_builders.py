"""Build schema-compatible operon/TU documents from a resolved .pred row.

This module does not allocate identifiers or write files. Callers must obtain
final RegulonDB identifiers through IdentifierService before calling it.
Coordinates retain the extractor's current Biopython convention (0-based,
end-exclusive); confirm the DB convention before enabling export.
"""

import re

from multigenomic_extractor.domain.predictions import Prediction, resolve_prediction

_RDB_ID = re.compile(r"^RDB(?:MG[A-Z]{7}[0-9]{7}|[A-Z]{8}[0-9]{5})$")


class InvalidTranscriptionPrediction(ValueError):
    """A prediction cannot safely be represented as a TU/operon pair."""


def compact_gene_names(gene_names: list[str]) -> str:
    groups = []
    previous_prefix = None

    for gene in gene_names:
        match = re.fullmatch(r"([a-z][a-z0-9]*)([A-Z])", gene)

        if match:
            prefix, suffix = match.groups()

            if prefix == previous_prefix:
                groups[-1] += suffix
            else:
                groups.append(gene)

            previous_prefix = prefix
        else:
            groups.append(gene)
            previous_prefix = None

    return "-".join(groups)

def build_transcription_documents(
    prediction: Prediction,
    protein_index: dict[str, dict],
    *,
    organism_id: str,
    operon_id: str,
    transcription_unit_id: str,
) -> tuple[dict, dict]:
    """Return (operon, transcription_unit) for a fully resolved prediction.

    All proteins must resolve uniquely to genes on one molecule and match the
    predicted strand. Unresolved, mixed-molecule and duplicate-gene rows fail
    explicitly; no partial TU is emitted.
    """
    for field, identifier in (
        ("organism_id", organism_id),
        ("operon_id", operon_id),
        ("transcription_unit_id", transcription_unit_id),
    ):
        if not isinstance(identifier, str) or not _RDB_ID.fullmatch(identifier):
            raise InvalidTranscriptionPrediction(f"Invalid {field}: {identifier!r}")

    if prediction.strand not in ("forward", "reverse") or not prediction.protein_ids:
        raise InvalidTranscriptionPrediction("Missing proteins or invalid strand")

    entries = resolve_prediction(prediction, protein_index)
    if not entries:
        raise InvalidTranscriptionPrediction(
            f"Line {prediction.line_number}: unresolved, ambiguous, duplicate, "
            "mixed-molecule or strand-inconsistent genes"
        )

    try:
        starts = [entry["start"] for entry in entries]
        ends = [entry["end"] for entry in entries]
        if any(type(x) is not int or x < 0 for x in starts + ends):
            raise ValueError("Coordinates must be nonnegative integers")
        if any(start >= end for start, end in zip(starts, ends)):
            raise ValueError("Each gene must have start < end")
        gene_ids = [entry["gene_id"] for entry in entries]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidTranscriptionPrediction(f"Invalid gene metadata: {exc}") from exc

    if any(not isinstance(gene_id, str) or not _RDB_ID.fullmatch(gene_id) for gene_id in gene_ids):
        raise InvalidTranscriptionPrediction("Gene identifiers must be final RegulonDB IDs")

    # The names column is informative, never used to resolve protein IDs.
    names = [name.strip() for name in prediction.gene_names if name.strip()]
    name = compact_gene_names(names) if len(names) == len(gene_ids) else "-".join(gene_ids)

    operon = {
        "_id": operon_id,
        "name": name,
        "regulationPositions": {
            "leftEndPosition": min(starts),
            "rightEndPosition": max(ends),
        },
        "organisms_id": organism_id,
        "strand": prediction.strand,
    }
    transcription_unit = {
        "_id": transcription_unit_id,
        "organisms_id": organism_id,
        "operons_id": operon_id,
        "genes_ids": gene_ids,
        "name": name,
    }
    return operon, transcription_unit
