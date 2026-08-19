def gene(**identifier_properties) -> list:
    return [
        identifier_properties.get("name", "NoName"),
        identifier_properties.get(
            "leftEndPosition",
            "NoLEND",
        ),
        identifier_properties.get(
            "rightEndPosition",
            "NoREND",
        ),
        identifier_properties.get(
            "bnumber",
            "NoBNumber",
        ),
    ]