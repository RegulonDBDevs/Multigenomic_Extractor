import re

IDENTIFIER_PREFIX = "RDBMG"
SEQUENCE_LENGTH = 7

IDENTIFIER_PATTERN = re.compile(
    r"^RDBMG[A-Z]{5}[A-Z]{2}[0-9]{7}$"
)


def build_identifier(
    organism_acronym: str,
    collection_acronym: str,
    sequence: int,
) -> str:
    identifier = (
        f"{IDENTIFIER_PREFIX}"
        f"{organism_acronym}"
        f"{collection_acronym}"
        f"{sequence:0{SEQUENCE_LENGTH}d}"
    )

    if not IDENTIFIER_PATTERN.fullmatch(
        identifier
    ):
        raise ValueError(
            f"Invalid identifier generated: "
            f"{identifier}"
        )

    return identifier