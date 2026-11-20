import argparse

from pymongo import MongoClient

from multigenomic_extractor.application.identifier_service import IdentifierService
from multigenomic_extractor.application.use_cases import (
    ExtractMultigenomicDirectoryUseCase,
)
from multigenomic_extractor.infrastructure.adapters.biopython_genbank_reader import (
    BiopythonGenBankReader,
)
from multigenomic_extractor.infrastructure.adapters.json_collection_writer import (
    JsonCollectionWriter,
)
from multigenomic_extractor.infrastructure.adapters.mongo_identifier_repository import (
    MongoIdentifierRepository,
)
from multigenomic_extractor.infrastructure.adapters.progress_bar import ProgressBar

REFERENCE_DATABASE_NAMES = (
    "REFSEQ",
    "NCBI-REFSEQ-PRO",
    "RFAM",
)

def load_external_reference_database_ids(database):
    """
    Load external reference database identifiers from MongoDB.

    Returns:
        dict[str, str]: Mapping of database names to RegulonDB IDs.
    """
    collection = database["externalCrossReferences"]

    database_ids = {}

    cursor = collection.find(
        {},
        {
            "_id": 1,
            "name": 1,
        },
    )

    for document in cursor:
        name = document.get("name")
        identifier = document.get("_id")

        if not name or identifier is None:
            raise ValueError(
                "Invalid externalCrossReferences document: "
                f"{document}"
            )

        normalized_name = name.strip().upper()

        if normalized_name in database_ids:
            raise ValueError(
                "Duplicate external reference database: "
                f"{normalized_name}"
            )

        database_ids[normalized_name] = str(identifier)

    if not database_ids:
        raise ValueError(
            "No external reference databases found in MongoDB."
        )

    return database_ids

def build_parser():
    parser = argparse.ArgumentParser(
        description=(
            "Extract multigenomic source files "
            "into collection JSON files."
        )
    )

    parser.add_argument(
        "--input",
        default="./genomes/genbank",
        help="Input directory containing supported source files.",
    )

    parser.add_argument(
        "--output",
        default="./output/json",
        help="Output directory for generated JSON files.",
    )

    parser.add_argument(
        "--predictions",
        default=None,
        help="Optional directory with GCA/GCF .pred or .pred.bz2 files.",
    )

    parser.add_argument(
        "--metadata-file",
        default=None,
        help="Optional TSV with assembly and molecule accession mappings.",
    )

    parser.add_argument(
        "--mongo-url",
        required=True,
        help="MongoDB connection URL.",
    )

    parser.add_argument(
        "--identifiers-db",
        default="regulondbidentifiers",
        help="MongoDB database containing identifiers and sequences.",
    )

    parser.add_argument(
        "--references-db",
        default="regulondbmultigenomic",
        help="MongoDB database containing externalCrossReferences.",
    )

    parser.add_argument(
        "--rdb-version",
        default=None,
        help="RegulonDB release version.",
    )

    parser.add_argument(
        "--source-name",
        default="GenBank",
        help="Original source database name.",
    )

    parser.add_argument(
        "--source-version",
        default=None,
        help="Original source database version.",
    )

    return parser


def main():
    args = build_parser().parse_args()

    mongo_client = MongoClient(args.mongo_url)

    try:
        identifiers_database = mongo_client[
            args.identifiers_db
        ]

        references_database = mongo_client[
            args.references_db
        ]

        external_reference_database_ids = (
            load_external_reference_database_ids(
                references_database
            )
        )

        print("External reference databases loaded:")

        for name, identifier in sorted(
            external_reference_database_ids.items()
        ):
            print(f"  {name}: {identifier}")

        identifier_repository = MongoIdentifierRepository(
            database=identifiers_database
        )

        identifier_service = IdentifierService(
            repository=identifier_repository,
            regulondb_release=args.rdb_version,
            source_db_name=args.source_name,
            source_db_version=args.source_version,
            identifiers_db=args.identifiers_db,
        )

        use_case = ExtractMultigenomicDirectoryUseCase(
            reader=BiopythonGenBankReader(),
            writer=JsonCollectionWriter(),
            progress_factory=ProgressBar,
            identifier_service=identifier_service,
            external_reference_database_ids=(
                external_reference_database_ids
            ),
        )

        use_case.execute(
            input_directory=args.input,
            output_directory=args.output,
            predictions_directory=args.predictions,
            metadata_file=args.metadata_file,
        )

    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
