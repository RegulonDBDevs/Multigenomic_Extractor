from datetime import datetime, timezone
from typing import Any

from multigenomic_extractor.domain.constants import COLLECTION_MAPPING
from multigenomic_extractor.domain.helpers import build_class_acronym
from multigenomic_extractor.domain.identifiers import (
    build_identifier,
    get_properties_to_make_id,
)


def get_collection_acronym(
    collection_name: str,
) -> str:
    for mapping in COLLECTION_MAPPING.values():
        if mapping["collectionName"] == collection_name:
            return mapping["subClassAcronym"]

    raise ValueError(
        f"No acronym configured for collection {collection_name!r}"
    )


class IdentifierService:
    def __init__(
        self,
        repository,
        *,
        regulondb_release: str | None = None,
        source_db_name: str | None = None,
        source_db_version: str | None = None,
    ):
        self.repository = repository
        self.regulondb_release = regulondb_release
        self.source_db_name = source_db_name
        self.source_db_version = source_db_version

    def get_or_create(
        self,
        document: dict[str, Any],
        collection_name: str,
        organism_name: str,
    ) -> str:
        organism_acronym = build_class_acronym(
            organism_name
        )

        collection_acronym = get_collection_acronym(
            collection_name
        )

        properties_to_make_id = get_properties_to_make_id(
            collection_name,
            document,
        )

        existing_identifier = (
            self.repository.find_identifier(
                organism=organism_acronym,
                collection_name=collection_name,
                properties_to_make_id=properties_to_make_id,
            )
        )

        if existing_identifier:
            return existing_identifier["_id"]

        original_source_id = document.get("_id")

        sequence = self.repository.get_next_sequence(
            organism_acronym=organism_acronym,
            collection_name=collection_name,
            collection_acronym=collection_acronym,
        )

        identifier = build_identifier(
            organism_acronym=organism_acronym,
            collection_acronym=collection_acronym,
            sequence=sequence,
        )

        now = datetime.now(timezone.utc)

        identifier_document = self._build_identifier_document(
            identifier=identifier,
            original_source_id=original_source_id,
            organism_acronym=organism_acronym,
            properties_to_make_id=properties_to_make_id,
            collection_name=collection_name,
            now=now,
        )

        self.repository.save_identifier(
            identifier_document
        )

        return identifier

    def get_or_create_many(
        self,
        documents: list[dict[str, Any]],
        collection_name: str,
        organism_name: str,
    ) -> list[str]:
        if not documents:
            return []

        organism_acronym = build_class_acronym(
            organism_name
        )

        collection_acronym = get_collection_acronym(
            collection_name
        )

        existing_identifiers = (
            self.repository.find_identifiers_by_type(
                organism=organism_acronym,
                collection_name=collection_name,
            )
        )

        existing_by_properties = {
            self._properties_key(
                identifier.get(
                    "propertiesToMakeId",
                    [],
                )
            ): identifier["_id"]
            for identifier in existing_identifiers
        }

        result_ids: list[str | None] = [
            None
        ] * len(documents)

        new_items: list[dict[str, Any]] = []

        pending_by_properties: dict[
            tuple,
            dict[str, Any],
        ] = {}

        for index, document in enumerate(
            documents
        ):
            properties_to_make_id = (
                get_properties_to_make_id(
                    collection_name,
                    document,
                )
            )

            properties_key = self._properties_key(
                properties_to_make_id
            )

            existing_id = (
                existing_by_properties.get(
                    properties_key
                )
            )

            if existing_id:
                result_ids[index] = existing_id
                continue

            pending_item = (
                pending_by_properties.get(
                    properties_key
                )
            )

            if pending_item is not None:
                pending_item["indexes"].append(
                    index
                )
                continue

            new_item = {
                "indexes": [index],
                "document": document,
                "propertiesToMakeId": (
                    properties_to_make_id
                ),
            }

            pending_by_properties[
                properties_key
            ] = new_item

            new_items.append(
                new_item
            )

        if not new_items:
            return self._validate_result_ids(
                result_ids
            )

        sequences = (
            self.repository.reserve_sequences(
                organism_acronym=(
                    organism_acronym
                ),
                collection_name=(
                    collection_name
                ),
                collection_acronym=(
                    collection_acronym
                ),
                amount=len(new_items),
            )
        )

        now = datetime.now(
            timezone.utc
        )

        identifier_documents = []

        for item, sequence in zip(
            new_items,
            sequences,
        ):
            identifier = build_identifier(
                organism_acronym=(
                    organism_acronym
                ),
                collection_acronym=(
                    collection_acronym
                ),
                sequence=sequence,
            )

            original_source_id = (
                item["document"].get("_id")
            )

            identifier_document = (
                self._build_identifier_document(
                    identifier=identifier,
                    original_source_id=(
                        original_source_id
                    ),
                    organism_acronym=(
                        organism_acronym
                    ),
                    properties_to_make_id=(
                        item[
                            "propertiesToMakeId"
                        ]
                    ),
                    collection_name=(
                        collection_name
                    ),
                    now=now,
                )
            )

            identifier_documents.append(
                identifier_document
            )

            for index in item["indexes"]:
                result_ids[index] = identifier

        self.repository.save_identifiers(
            identifier_documents
        )

        return self._validate_result_ids(
            result_ids
        )

    def _build_identifier_document(
        self,
        identifier: str,
        original_source_id: Any,
        organism_acronym: str,
        properties_to_make_id: list,
        collection_name: str,
        now: datetime,
    ) -> dict[str, Any]:
        return {
            "_id": identifier,
            "creationDate": now,
            "createdOnRegulonDBRelease": (
                self.regulondb_release
            ),
            "regulondbDatabase": (
                "Multigenomic_TESTING"
            ),
            "lastRegulonDBReleaseUsed": (
                self.regulondb_release
            ),
            "lastUpdate": now,
            "objectOriginalSourceId": (
                original_source_id
            ),
            "organism": organism_acronym,
            "propertiesToMakeId": (
                properties_to_make_id
            ),
            "sourceDBName": (
                self.source_db_name
            ),
            "sourceDBVersion": (
                self.source_db_version
            ),
            "type": collection_name,
        }

    @staticmethod
    def _properties_key(
        properties: list,
    ) -> tuple:
        return tuple(
            IdentifierService._make_hashable(
                value
            )
            for value in properties
        )

    @staticmethod
    def _make_hashable(
        value: Any,
    ) -> Any:
        if isinstance(value, list):
            return tuple(
                IdentifierService._make_hashable(
                    item
                )
                for item in value
            )

        if isinstance(value, dict):
            return tuple(
                sorted(
                    (
                        key,
                        IdentifierService._make_hashable(
                            item
                        ),
                    )
                    for key, item
                    in value.items()
                )
            )

        return value

    @staticmethod
    def _validate_result_ids(
        result_ids: list[str | None],
    ) -> list[str]:
        missing_indexes = [
            index
            for index, identifier
            in enumerate(result_ids)
            if identifier is None
        ]

        if missing_indexes:
            raise RuntimeError(
                "Could not resolve identifiers "
                f"for document indexes: "
                f"{missing_indexes}"
            )

        return [
            identifier
            for identifier in result_ids
            if identifier is not None
        ]