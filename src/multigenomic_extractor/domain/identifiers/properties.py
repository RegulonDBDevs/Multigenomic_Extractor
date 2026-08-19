from .gene import gene
from .organism import organism
from .product import product

PROPERTY_BUILDERS = {
    "organisms": organism,
    "genes": gene,
    "products": product,
}


def get_properties_to_make_id(
    collection_name: str,
    document: dict,
) -> list:
    try:
        builder = PROPERTY_BUILDERS[
            collection_name
        ]
    except KeyError as exc:
        raise ValueError(
            "Unsupported collection for identifier "
            f"generation: {collection_name}"
        ) from exc

    return builder(**document)