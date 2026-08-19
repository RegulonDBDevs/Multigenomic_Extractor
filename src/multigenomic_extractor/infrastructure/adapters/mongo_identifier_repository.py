from typing import Any

from pymongo import ReturnDocument


class MongoIdentifierRepository:
    def __init__(
        self,
        database,
        target_database_name: str = "Multigenomic_TESTING",
    ):
        self.identifiers = database["identifiers"]
        self.sequences = database["sequences"]
        self.target_database_name = target_database_name

    def find_identifier(
        self,
        organism: str,
        collection_name: str,
        properties_to_make_id: list,
    ) -> dict[str, Any] | None:
        return self.identifiers.find_one(
            {
                "organism": organism,
                "type": collection_name,
                "propertiesToMakeId": properties_to_make_id,
            }
        )

    def find_identifiers_by_type(
        self,
        organism: str,
        collection_name: str,
    ) -> list[dict[str, Any]]:
        return list(
            self.identifiers.find(
                {
                    "organism": organism,
                    "type": collection_name,
                },
                {
                    "_id": 1,
                    "propertiesToMakeId": 1,
                },
            )
        )

    def get_next_sequence(
        self,
        organism_acronym: str,
        collection_name: str,
        collection_acronym: str,
    ) -> int:
        sequence_document = self.sequences.find_one_and_update(
            {
                "database": self.target_database_name,
                "organism": organism_acronym,
                "type": collection_name,
                "subClassAcronym": collection_acronym,
            },
            {
                "$inc": {
                    "value": 1,
                },
                "$setOnInsert": {
                    "classAcronym": organism_acronym,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        return sequence_document["value"]

    def reserve_sequences(
        self,
        organism_acronym: str,
        collection_name: str,
        collection_acronym: str,
        amount: int,
    ) -> range:
        if amount <= 0:
            return range(0)

        sequence_document = self.sequences.find_one_and_update(
            {
                "database": self.target_database_name,
                "organism": organism_acronym,
                "type": collection_name,
                "subClassAcronym": collection_acronym,
            },
            {
                "$inc": {
                    "value": amount,
                },
                "$setOnInsert": {
                    "classAcronym": organism_acronym,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        last_value = sequence_document["value"]
        first_value = last_value - amount + 1

        return range(
            first_value,
            last_value + 1,
        )

    def save_identifier(
        self,
        identifier_document: dict,
    ) -> None:
        self.identifiers.insert_one(
            identifier_document
        )

    def save_identifiers(
        self,
        identifier_documents: list[dict],
    ) -> None:
        if not identifier_documents:
            return

        self.identifiers.insert_many(
            identifier_documents,
            ordered=False,
        )