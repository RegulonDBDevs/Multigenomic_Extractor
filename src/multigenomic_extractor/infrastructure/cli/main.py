import argparse

from pymongo import MongoClient

from multigenomic_extractor.application.identifier_service import (
    IdentifierService,
)
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
from multigenomic_extractor.infrastructure.adapters.progress_bar import (
    ProgressBar,
)


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
        help=(
            "Input directory containing "
            "supported source files."
        ),
    )

    parser.add_argument(
        "--output",
        default="./output/json",
        help=(
            "Output directory for generated "
            "JSON files."
        ),
    )

    parser.add_argument(
        "--mongo-url",
        required=True,
        help="MongoDB connection URL.",
    )

    parser.add_argument(
        "--identifiers-db",
        default="regulondbidentifiers",
        help=(
            "MongoDB database containing "
            "identifiers and sequences."
        ),
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

    mongo_client = MongoClient(
        args.mongo_url
    )

    identifiers_database = mongo_client[
        args.identifiers_db
    ]

    identifier_repository = (
        MongoIdentifierRepository(
            database=identifiers_database,
        )
    )

    identifier_service = IdentifierService(
        repository=identifier_repository,
        regulondb_release=(
            args.rdb_version
        ),
        source_db_name=args.source_name,
        source_db_version=(
            args.source_version
        ),
    )

    use_case = (
        ExtractMultigenomicDirectoryUseCase(
            reader=BiopythonGenBankReader(),
            writer=JsonCollectionWriter(),
            progress_factory=ProgressBar,
            identifier_service=(
                identifier_service
            ),
        )
    )

    try:
        use_case.execute(
            input_directory=args.input,
            output_directory=args.output,
        )
    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()
