def product(**identifier_properties) -> list:
    return [
        identifier_properties.get(
            "name",
            "NoName",
        ),
    ]