from pathlib import Path


def organism(**identifier_properties) -> list:
    unique_data_string = [
        identifier_properties.get("name", "NoName"),
        identifier_properties.get("strainName", "NoStrain"),
        identifier_properties.get("type", "NoType"),
    ]

    source_file = identifier_properties.get("sourceFile")

    if source_file:
        unique_data_string.append(
            Path(source_file).stem
        )

    plasmid_name = identifier_properties.get("plasmidName")

    if plasmid_name:
        unique_data_string.append(plasmid_name)

    return unique_data_string