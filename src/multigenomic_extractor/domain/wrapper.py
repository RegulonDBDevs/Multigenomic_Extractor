from typing import Any

from multigenomic_extractor.domain.constants import COLLECTION_MAPPING


def get_subclass_acronym_by_collection(collection_name):
    for mapping in COLLECTION_MAPPING.values():
        if mapping["collectionName"] == collection_name:
            return mapping["subClassAcronym"]

    return None


def build_collection_wrapper(
    collection_name: str,
    class_acronym: str,
    organism_name: str,
    strain_name: str,
    documents: list[dict[str, Any]],
):
    return {
        "classAcronym": class_acronym,
        "collectionName": collection_name,
        "subClassAcronym": get_subclass_acronym_by_collection(
            collection_name
        ),
        "organism": organism_name,
        "strain": strain_name,
        "collectionData": documents,
    }
