
import re
from collections.abc import Mapping

_REFSEQ_INFERENCE = re.compile(
    r":RefSeq:\s*([^\s,;]+)",
    re.IGNORECASE,
)


def _values(qualifiers: Mapping, key: str) -> list[str]:
    raw = qualifiers.get(key, [])

    if isinstance(raw, str):
        raw = [raw]

    return [
        value.strip()
        for value in raw
        if isinstance(value, str) and value.strip()
    ]


def extract_external_references(
    qualifiers: Mapping,
) -> list[dict[str, str]]:
    references = []
    seen = set()

    def add(database: str, identifier: str) -> None:
        key = (database, identifier)

        if key not in seen:
            seen.add(key)
            references.append(
                {
                    "database": database,
                    "objectId": identifier,
                }
            )

    # /protein_id: conservar el identificador original.
    for protein_id in _values(qualifiers, "protein_id"):
        add("NCBI-REFSEQ-PRO", protein_id)

    # /inference: extraer el valor posterior a :RefSeq:
    for inference in _values(qualifiers, "inference"):
        for match in _REFSEQ_INFERENCE.finditer(inference):
            add("REFSEQ", match.group(1))

    # /db_xref: referencias adicionales.
    for value in _values(qualifiers, "db_xref"):
        database, separator, identifier = value.partition(":")

        if not separator:
            continue

        database = database.strip().upper()
        identifier = identifier.strip()

        if database == "RFAM":
            if re.fullmatch(
                r"RF\d+",
                identifier,
                re.IGNORECASE,
            ):
                add("RFAM", identifier)

        elif database == "TAXON":
            if identifier.isascii() and identifier.isdecimal():
                add("NCBI-TAXONOMY", identifier)

    return references


def resolve_external_references(
    qualifiers: Mapping,
    database_ids: Mapping[str, str],
    on_missing=None,
) -> list[dict[str, str]]:
    references = extract_external_references(qualifiers)

    normalized_ids = {
        name.upper(): identifier
        for name, identifier in database_ids.items()
    }

    result = []

    for reference in references:
        database = reference["database"]
        database_id = normalized_ids.get(database.upper())

        if not database_id:
            if on_missing is not None:
                on_missing(database, reference["objectId"])
                continue

            raise ValueError(
                f"Missing externalCrossReferences_id for {database}"
            )

        result.append(
            {
                "externalCrossReferences_id": database_id,
                "objectId": reference["objectId"],
            }
        )

    return result
