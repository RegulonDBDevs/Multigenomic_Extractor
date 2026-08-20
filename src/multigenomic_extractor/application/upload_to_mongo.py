import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pymongo import MongoClient
from pymongo.errors import (
    BulkWriteError,
    CollectionInvalid,
    OperationFailure,
)


DEFAULT_INPUT_DIRECTORY = "./output/json"
DEFAULT_SCHEMA_DIRECTORY = (
    "./src/multigenomic_extractor/domain/schemas"
)
DEFAULT_BATCH_SIZE = 1000

COLLECTION_ORDER = [
    "organisms",
    "genes",
    "products",
]

SUPPORTED_COLLECTIONS = set(
    COLLECTION_ORDER
)


class ProgressBar:
    def __init__(
        self,
        total: int,
        width: int = 30,
    ):
        self.total = max(total, 1)
        self.width = width
        self.current = 0

    def update(
        self,
        step: int,
        *,
        collection_name: str = "",
        source_file: str = "",
    ) -> None:
        self.current += step

        percentage = min(
            self.current / self.total,
            1.0,
        )

        completed = int(
            self.width * percentage
        )

        bar = (
            "█" * completed
            + "-" * (
                self.width - completed
            )
        )

        percent_value = int(
            percentage * 100
        )

        message = (
            f"Uploading "
            f"[{bar}] "
            f"{percent_value:3d}% | "
            f"{self.current}/"
            f"{self.total} docs"
        )

        if collection_name:
            message += (
                f" | {collection_name}"
            )

        if source_file:
            message += (
                f" | {source_file}"
            )

        # Limpia la línea actual y mueve
        # el cursor nuevamente al inicio.
        sys.stdout.write(
            "\033[2K\r"
        )

        sys.stdout.write(
            message
        )

        sys.stdout.flush()

    def finish(self) -> None:
        self.current = self.total

        self.update(
            0
        )

        sys.stdout.write("\n")
        sys.stdout.flush()

    def clear(self) -> None:
        sys.stdout.write(
            "\033[2K\r"
        )
        sys.stdout.flush()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create Multigenomic MongoDB collections "
            "from JSON schemas and upload extracted data."
        )
    )

    parser.add_argument(
        "--input",
        default=DEFAULT_INPUT_DIRECTORY,
        help=(
            "Directory containing extractor JSON files. "
            f"Default: {DEFAULT_INPUT_DIRECTORY}"
        ),
    )

    parser.add_argument(
        "--schemas",
        default=DEFAULT_SCHEMA_DIRECTORY,
        help=(
            "Directory containing collection JSON schemas. "
            f"Default: {DEFAULT_SCHEMA_DIRECTORY}"
        ),
    )

    parser.add_argument(
        "--mongo-url",
        required=True,
        help="MongoDB connection URL.",
    )

    parser.add_argument(
        "--database",
        required=True,
        help="Target MongoDB database.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=(
            "Number of documents inserted per batch. "
            f"Default: {DEFAULT_BATCH_SIZE}"
        ),
    )

    parser.add_argument(
        "--drop-collections",
        action="store_true",
        help=(
            "Drop supported collections before creating "
            "them from their schemas."
        ),
    )

    return parser


def load_json(
    file_path: Path,
) -> dict[str, Any]:
    with file_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def get_schema_files(
    schema_directory: Path,
) -> dict[str, Path]:
    schema_files = {}

    for collection_name in COLLECTION_ORDER:
        schema_path = (
            schema_directory
            / f"{collection_name}.json"
        )

        if not schema_path.exists():
            raise FileNotFoundError(
                "Schema not found for collection "
                f"{collection_name!r}: "
                f"{schema_path}"
            )

        schema_files[
            collection_name
        ] = schema_path

    return schema_files


def load_schema_config(
    schema_path: Path,
    collection_name: str,
) -> dict[str, Any]:
    schema_document = load_json(
        schema_path
    )

    if collection_name not in schema_document:
        raise ValueError(
            f"Schema file {schema_path} "
            f"does not contain collection "
            f"{collection_name!r}."
        )

    collection_config = schema_document[
        collection_name
    ]

    if "validator" not in collection_config:
        raise ValueError(
            f"Schema for {collection_name!r} "
            "does not contain 'validator'."
        )

    return collection_config


def create_collection_from_schema(
    database,
    collection_name: str,
    schema_config: dict[str, Any],
    drop_collection: bool,
) -> None:
    existing_collections = (
        database.list_collection_names()
    )

    collection_exists = (
        collection_name
        in existing_collections
    )

    if (
        collection_exists
        and drop_collection
    ):
        database.drop_collection(
            collection_name
        )

        collection_exists = False

    validator = schema_config[
        "validator"
    ]

    validation_level = (
        schema_config.get(
            "validationLevel",
            "strict",
        )
    )

    validation_action = (
        schema_config.get(
            "validationAction",
            "error",
        )
    )

    if not collection_exists:
        try:
            database.create_collection(
                collection_name,
                validator=validator,
                validationLevel=(
                    validation_level
                ),
                validationAction=(
                    validation_action
                ),
            )

        except CollectionInvalid as error:
            raise RuntimeError(
                "Could not create collection "
                f"{collection_name!r}: "
                f"{error}"
            ) from error

        return

    try:
        database.command(
            {
                "collMod": collection_name,
                "validator": validator,
                "validationLevel": (
                    validation_level
                ),
                "validationAction": (
                    validation_action
                ),
            }
        )

    except OperationFailure as error:
        raise RuntimeError(
            "Could not update validator "
            f"for {collection_name!r}: "
            f"{error}"
        ) from error


def prepare_collections(
    database,
    schema_directory: Path,
    drop_collections: bool,
) -> None:
    schema_files = get_schema_files(
        schema_directory
    )

    for collection_name in COLLECTION_ORDER:
        schema_config = load_schema_config(
            schema_path=(
                schema_files[
                    collection_name
                ]
            ),
            collection_name=(
                collection_name
            ),
        )

        create_collection_from_schema(
            database=database,
            collection_name=(
                collection_name
            ),
            schema_config=schema_config,
            drop_collection=(
                drop_collections
            ),
        )


def find_input_files(
    input_directory: Path,
) -> list[Path]:
    return sorted(
        path
        for path in input_directory.glob(
            "*.json"
        )
        if path.is_file()
    )


def get_wrapper_collection_name(
    wrapper: dict[str, Any],
    source_file: Path,
) -> str:
    collection_name = wrapper.get(
        "collectionName"
    )

    if not collection_name:
        raise ValueError(
            f"{source_file.name}: "
            "missing 'collectionName'."
        )

    if (
        collection_name
        not in SUPPORTED_COLLECTIONS
    ):
        raise ValueError(
            f"{source_file.name}: "
            "unsupported collection "
            f"{collection_name!r}."
        )

    return collection_name


def get_wrapper_documents(
    wrapper: dict[str, Any],
    source_file: Path,
) -> list[dict[str, Any]]:
    documents = wrapper.get(
        "collectionData"
    )

    if documents is None:
        raise ValueError(
            f"{source_file.name}: "
            "missing 'collectionData'."
        )

    if not isinstance(
        documents,
        list,
    ):
        raise TypeError(
            f"{source_file.name}: "
            "'collectionData' must be "
            "an array."
        )

    return documents


def group_input_files(
    input_files: list[Path],
) -> dict[str, list[Path]]:
    grouped_files = {
        collection_name: []
        for collection_name
        in COLLECTION_ORDER
    }

    for source_file in input_files:
        wrapper = load_json(
            source_file
        )

        collection_name = (
            get_wrapper_collection_name(
                wrapper,
                source_file,
            )
        )

        grouped_files[
            collection_name
        ].append(
            source_file
        )

    return grouped_files


def count_total_documents(
    grouped_files: dict[str, list[Path]],
) -> int:
    total_documents = 0

    for collection_name in COLLECTION_ORDER:
        for source_file in grouped_files[
            collection_name
        ]:
            wrapper = load_json(
                source_file
            )

            documents = (
                get_wrapper_documents(
                    wrapper,
                    source_file,
                )
            )

            total_documents += len(
                documents
            )

    return total_documents


def iter_batches(
    documents: list[dict[str, Any]],
    batch_size: int,
):
    for start in range(
        0,
        len(documents),
        batch_size,
    ):
        yield documents[
            start:
            start + batch_size
        ]


def print_bulk_write_error(
    error: BulkWriteError,
    source_file: Path,
    collection_name: str,
    batch_number: int,
) -> None:
    details = error.details or {}

    write_errors = details.get(
        "writeErrors",
        [],
    )

    print(
        "[ERROR] Bulk insert failed"
    )
    print(
        f"File: {source_file.name}"
    )
    print(
        f"Collection: {collection_name}"
    )
    print(
        f"Batch: {batch_number}"
    )

    if not write_errors:
        print(
            "\nMongoDB error:"
        )

        print(
            json.dumps(
                details,
                indent=2,
                default=str,
            )
        )

        return

    first_error = write_errors[0]

    print(
        "\nFirst MongoDB error:"
    )

    print(
        json.dumps(
            first_error,
            indent=2,
            default=str,
        )
    )


def insert_documents(
    database,
    collection_name: str,
    documents: list[dict[str, Any]],
    batch_size: int,
    source_file: Path,
    progress: ProgressBar,
) -> int:
    if not documents:
        return 0

    collection = database[
        collection_name
    ]

    inserted_count = 0

    for batch_number, batch in enumerate(
        iter_batches(
            documents,
            batch_size,
        ),
        start=1,
    ):
        try:
            result = collection.insert_many(
                batch,
                ordered=False,
            )

        except BulkWriteError as error:
            progress.clear()

            print_bulk_write_error(
                error=error,
                source_file=source_file,
                collection_name=(
                    collection_name
                ),
                batch_number=(
                    batch_number
                ),
            )

            raise

        inserted = len(
            result.inserted_ids
        )

        inserted_count += inserted

        progress.update(
            inserted,
            collection_name=(
                collection_name
            ),
            source_file=(
                source_file.name
            ),
        )

    return inserted_count


def upload_collection_files(
    database,
    collection_name: str,
    source_files: list[Path],
    batch_size: int,
    progress: ProgressBar,
) -> tuple[int, int]:
    collection_documents = 0
    processed_files = 0

    if not source_files:
        return (
            collection_documents,
            processed_files,
        )

    for source_file in source_files:
        wrapper = load_json(
            source_file
        )

        actual_collection_name = (
            get_wrapper_collection_name(
                wrapper,
                source_file,
            )
        )

        if (
            actual_collection_name
            != collection_name
        ):
            progress.clear()

            raise ValueError(
                f"{source_file.name}: "
                "collection changed between "
                "file discovery and upload."
            )

        documents = (
            get_wrapper_documents(
                wrapper,
                source_file,
            )
        )

        inserted = insert_documents(
            database=database,
            collection_name=(
                collection_name
            ),
            documents=documents,
            batch_size=batch_size,
            source_file=source_file,
            progress=progress,
        )

        collection_documents += (
            inserted
        )

        processed_files += 1

    return (
        collection_documents,
        processed_files,
    )


def validate_arguments(
    input_directory: Path,
    schema_directory: Path,
    batch_size: int,
) -> None:
    if not input_directory.exists():
        raise FileNotFoundError(
            "Input directory does not exist: "
            f"{input_directory}"
        )

    if not input_directory.is_dir():
        raise NotADirectoryError(
            "Input path is not a directory: "
            f"{input_directory}"
        )

    if not schema_directory.exists():
        raise FileNotFoundError(
            "Schema directory does not exist: "
            f"{schema_directory}"
        )

    if not schema_directory.is_dir():
        raise NotADirectoryError(
            "Schema path is not a directory: "
            f"{schema_directory}"
        )

    if batch_size <= 0:
        raise ValueError(
            "--batch-size must be greater "
            "than zero."
        )


def main() -> None:
    args = build_parser().parse_args()

    input_directory = Path(
        args.input
    )

    schema_directory = Path(
        args.schemas
    )

    validate_arguments(
        input_directory=(
            input_directory
        ),
        schema_directory=(
            schema_directory
        ),
        batch_size=(
            args.batch_size
        ),
    )

    input_files = find_input_files(
        input_directory
    )

    if not input_files:
        print(
            "No JSON files found in "
            f"{input_directory.resolve()}."
        )

        return

    grouped_files = group_input_files(
        input_files
    )

    total_documents_to_upload = (
        count_total_documents(
            grouped_files
        )
    )

    mongo_client = MongoClient(
        args.mongo_url
    )

    try:
        database = mongo_client[
            args.database
        ]

        prepare_collections(
            database=database,
            schema_directory=(
                schema_directory
            ),
            drop_collections=(
                args.drop_collections
            ),
        )

        progress = ProgressBar(
            total=(
                total_documents_to_upload
            )
        )

        total_documents = 0
        total_files = 0

        try:
            for collection_name in (
                COLLECTION_ORDER
            ):
                (
                    inserted_documents,
                    processed_files,
                ) = upload_collection_files(
                    database=database,
                    collection_name=(
                        collection_name
                    ),
                    source_files=(
                        grouped_files[
                            collection_name
                        ]
                    ),
                    batch_size=(
                        args.batch_size
                    ),
                    progress=progress,
                )

                total_documents += (
                    inserted_documents
                )

                total_files += (
                    processed_files
                )

        except Exception:
            progress.clear()
            raise

        progress.finish()

        print(
            f"Upload completed | "
            f"Files: {total_files} | "
            f"Documents: "
            f"{total_documents} | "
            f"Database: "
            f"{database.name}"
        )

    finally:
        mongo_client.close()


if __name__ == "__main__":
    main()