from pathlib import Path
from typing import Protocol

from multigenomic_extractor.domain.builders import normalize_feature
from multigenomic_extractor.domain.constants import COLLECTION_MAPPING
from multigenomic_extractor.domain.helpers import build_class_acronym
from multigenomic_extractor.domain.record_metadata import (
    get_record_organism_id,
    get_record_organism_name,
    get_record_strain_name,
)
from multigenomic_extractor.domain.wrapper import build_collection_wrapper


class SourceReaderPort(Protocol):
    def find_files(self, input_path: Path):
        ...

    def parse_records(self, gb_file: Path):
        ...


class CollectionWriterPort(Protocol):
    def write_collection(
        self,
        output_path: Path,
        collection_name: str,
        source_file: Path,
        wrapper_document: dict,
    ) -> None:
        ...


class ProgressPort(Protocol):
    def update(self, step: int = 1) -> None:
        ...

    def finish(self) -> None:
        ...


class ExtractMultigenomicDirectoryUseCase:
    def __init__(
        self,
        reader: SourceReaderPort,
        writer: CollectionWriterPort,
        progress_factory,
        identifier_service=None,
    ):
        self.reader = reader
        self.writer = writer
        self.progress_factory = progress_factory
        self.identifier_service = identifier_service

    def execute(
        self,
        input_directory: str,
        output_directory: str,
    ):
        input_path = Path(input_directory)
        output_path = Path(output_directory)

        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_files = self.reader.find_files(
            input_path
        )

        if not source_files:
            print(
                "No se encontraron archivos fuente soportados."
            )

            return {
                "documents": 0,
                "files": 0,
            }

        print(
            f"Se encontraron {len(source_files)} "
            f"archivos fuente soportados"
        )

        progress = self.progress_factory(
            len(source_files)
        )

        total_documents = 0
        total_files = 0

        for source_file in source_files:
            grouped_documents = {
                "organisms": [],
                "genes": [],
                "products": [],
            }

            organism_name = "Unknown organism"
            class_acronym = "UNKNO"
            strain_name = None

            for record in self.reader.parse_records(
                source_file
            ):
                original_organism_id = (
                    get_record_organism_id(record)
                )

                organism_name = (
                    get_record_organism_name(record)
                )

                strain_name = (
                    get_record_strain_name(record)
                )

                class_acronym = build_class_acronym(
                    organism_name
                )

                organism_id = self._process_organism(
                    record=record,
                    source_file=source_file,
                    original_organism_id=(
                        original_organism_id
                    ),
                    organism_name=organism_name,
                    grouped_documents=(
                        grouped_documents
                    ),
                )

                gene_id_map = self._process_genes(
                    record=record,
                    source_file=source_file,
                    organism_id=organism_id,
                    organism_name=organism_name,
                    grouped_documents=(
                        grouped_documents
                    ),
                )

                self._process_products(
                    record=record,
                    source_file=source_file,
                    organism_id=organism_id,
                    organism_name=organism_name,
                    gene_id_map=gene_id_map,
                    grouped_documents=(
                        grouped_documents
                    ),
                )

            total_documents += sum(
                len(documents)
                for documents
                in grouped_documents.values()
            )

            for (
                collection_name,
                documents,
            ) in grouped_documents.items():
                if not documents:
                    continue

                wrapper_document = (
                    build_collection_wrapper(
                        collection_name=(
                            collection_name
                        ),
                        class_acronym=(
                            class_acronym
                        ),
                        organism_name=(
                            organism_name
                        ),
                        strain_name=(
                            strain_name
                        ),
                        documents=documents,
                    )
                )

                self.writer.write_collection(
                    output_path=output_path,
                    collection_name=(
                        collection_name
                    ),
                    source_file=source_file,
                    wrapper_document=(
                        wrapper_document
                    ),
                )

                total_files += 1

            progress.update()

        progress.finish()

        print(
            f"\nProceso finalizado. "
            f"Documentos generados: "
            f"{total_documents}"
        )

        print(
            f"Archivos JSON generados: "
            f"{total_files}"
        )

        print(
            f"Salida: "
            f"{output_path.resolve()}"
        )

        return {
            "documents": total_documents,
            "files": total_files,
        }

    def _process_organism(
        self,
        record,
        source_file: Path,
        original_organism_id: str,
        organism_name: str,
        grouped_documents: dict,
    ) -> str:
        source_feature = next(
            (
                feature
                for feature in record.features
                if feature.type == "source"
            ),
            None,
        )

        if source_feature is None:
            return original_organism_id

        document = normalize_feature(
            record=record,
            feature=source_feature,
            source_file=source_file.name,
            organism_id=original_organism_id,
        )

        if self.identifier_service:
            document["_id"] = (
                self.identifier_service.get_or_create(
                    document=document,
                    collection_name="organisms",
                    organism_name=organism_name,
                )
            )

        grouped_documents[
            "organisms"
        ].append(document)

        return document["_id"]

    def _process_genes(
        self,
        record,
        source_file: Path,
        organism_id: str,
        organism_name: str,
        grouped_documents: dict,
    ) -> dict[str, str]:
        gene_items = []

        for feature in record.features:
            if feature.type != "gene":
                continue

            try:
                document = normalize_feature(
                    record=record,
                    feature=feature,
                    source_file=source_file.name,
                    organism_id=organism_id,
                )

                gene_items.append(
                    {
                        "original_id": (
                            document.get("_id")
                        ),
                        "document": document,
                    }
                )

            except Exception as error:
                print(
                    f"\nError en feature gene "
                    f"de {source_file.name}: "
                    f"{error}"
                )

        if not gene_items:
            return {}

        gene_documents = [
            item["document"]
            for item in gene_items
        ]

        if self.identifier_service:
            generated_ids = (
                self.identifier_service
                .get_or_create_many(
                    documents=gene_documents,
                    collection_name="genes",
                    organism_name=organism_name,
                )
            )

            for document, identifier in zip(
                gene_documents,
                generated_ids,
            ):
                document["_id"] = identifier

        gene_id_map = {}

        for item in gene_items:
            document = item["document"]
            original_gene_id = item[
                "original_id"
            ]

            if original_gene_id:
                gene_id_map[
                    original_gene_id
                ] = document["_id"]

        grouped_documents[
            "genes"
        ].extend(
            gene_documents
        )

        return gene_id_map

    def _process_products(
        self,
        record,
        source_file: Path,
        organism_id: str,
        organism_name: str,
        gene_id_map: dict[str, str],
        grouped_documents: dict,
    ) -> None:
        product_feature_types = {
            feature_type
            for feature_type, mapping
            in COLLECTION_MAPPING.items()
            if mapping["collectionName"]
            == "products"
        }

        product_documents = []

        for feature in record.features:
            if (
                feature.type
                not in product_feature_types
            ):
                continue

            try:
                document = normalize_feature(
                    record=record,
                    feature=feature,
                    source_file=source_file.name,
                    organism_id=organism_id,
                )

                original_gene_id = document.get(
                    "genes_id"
                )

                if (
                    original_gene_id
                    and original_gene_id
                    in gene_id_map
                ):
                    document["genes_id"] = (
                        gene_id_map[
                            original_gene_id
                        ]
                    )

                product_documents.append(
                    document
                )

            except Exception as error:
                print(
                    f"\nError en feature "
                    f"{feature.type} "
                    f"de {source_file.name}: "
                    f"{error}"
                )

        if not product_documents:
            return

        if self.identifier_service:
            generated_ids = (
                self.identifier_service
                .get_or_create_many(
                    documents=product_documents,
                    collection_name="products",
                    organism_name=organism_name,
                )
            )

            for document, identifier in zip(
                product_documents,
                generated_ids,
            ):
                document["_id"] = identifier

        grouped_documents[
            "products"
        ].extend(
            product_documents
        )