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
    ):
        self.reader = reader
        self.writer = writer
        self.progress_factory = progress_factory

    def execute(self, input_directory: str, output_directory: str):
        input_path = Path(input_directory)
        output_path = Path(output_directory)

        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        source_files = self.reader.find_files(input_path)

        if not source_files:
            print("No se encontraron archivos fuente soportados.")
            return {
                "documents": 0,
                "files": 0,
            }

        print(
            f"Se encontraron {len(source_files)} "
            f"archivos fuente soportados"
        )

        progress = self.progress_factory(len(source_files))
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

            for record in self.reader.parse_records(source_file):
                organism_id = get_record_organism_id(record)
                organism_name = get_record_organism_name(record)
                strain_name = get_record_strain_name(record)
                class_acronym = build_class_acronym(
                    organism_name
                )

                for feature in record.features:
                    if not feature.type:
                        continue

                    mapping = COLLECTION_MAPPING.get(
                        feature.type
                    )

                    if not mapping:
                        continue

                    try:
                        document = normalize_feature(
                            record=record,
                            feature=feature,
                            source_file=source_file.name,
                            organism_id=organism_id,
                        )

                        collection_name = mapping[
                            "collectionName"
                        ]

                        grouped_documents[
                            collection_name
                        ].append(document)

                        total_documents += 1

                    except Exception as error:
                        print(
                            f"\nError en feature "
                            f"{feature.type} "
                            f"de {source_file.name}: "
                            f"{error}"
                        )

            for collection_name, documents in grouped_documents.items():
                if not documents:
                    continue

                wrapper_document = build_collection_wrapper(
                    collection_name=collection_name,
                    class_acronym=class_acronym,
                    organism_name=organism_name,
                    strain_name=strain_name,
                    documents=documents,
                )

                self.writer.write_collection(
                    output_path=output_path,
                    collection_name=collection_name,
                    source_file=source_file,
                    wrapper_document=wrapper_document,
                )

                total_files += 1

            progress.update()

        progress.finish()

        print(
            f"\nProceso finalizado. "
            f"Documentos generados: {total_documents}"
        )
        print(f"Archivos JSON generados: {total_files}")
        print(f"Salida: {output_path.resolve()}")

        return {
            "documents": total_documents,
            "files": total_files,
        }
