from multigenomic_extractor.domain.helpers import (
    build_org_name,
    generate_dynamic_id,
    safe_get_first,
)


def get_record_organism_id(record):
    for feature in record.features:
        if feature.type != "source":
            continue

        qualifiers = feature.qualifiers

        return generate_dynamic_id(
            "organism",
            qualifiers,
            [
                "organism",
                "strain",
                "plasmid",
            ],
        )

    return None


def get_record_organism_name(record):
    for feature in record.features:
        if feature.type != "source":
            continue

        qualifiers = feature.qualifiers

        return (
            build_org_name(
                (
                    safe_get_first(qualifiers.get("organism"))
                    or record.annotations.get("organism")
                ),
                safe_get_first(
                    qualifiers.get("strain")
                )
            )
            or record.annotations.get("organism")
            or "Unknown organism"
        )

    return (
        record.annotations.get("organism")
        or "Unknown organism"
    )


def get_record_strain_name(record):
    for feature in record.features:
        if feature.type != "source":
            continue

        return safe_get_first(
            feature.qualifiers.get("strain")
        )

    return None
