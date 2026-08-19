def product(**identifier_properties) -> list:
    return [
        identifier_properties.get(
            "genes_id",
            "NoGeneId",
        ),
        identifier_properties.get(
            "name",
            "NoName",
        ),
        identifier_properties.get(
            "type",
            "NoType",
        ),
    ]