def organism(**identifier_properties) -> list:
    unique_data_string = [
        identifier_properties.get("name", "NoName"),
        identifier_properties.get("strainName", "NoStrain"),
        identifier_properties.get("type", "NoType"),
    ]

    plasmid_name = identifier_properties.get("plasmidName")

    if plasmid_name:
        unique_data_string.append(plasmid_name)

    return unique_data_string