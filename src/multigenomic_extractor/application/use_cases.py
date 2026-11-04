from pathlib import Path
from typing import Protocol

from multigenomic_extractor.domain.assembly_metadata import (
    normalize_molecule,
    read_assembly_metadata,
)
from multigenomic_extractor.domain.builders import normalize_feature
from multigenomic_extractor.domain.constants import COLLECTION_MAPPING
from multigenomic_extractor.domain.helpers import build_class_acronym
from multigenomic_extractor.domain.prediction_directory import (
    find_prediction_files,
    record_assembly_ids,
)
from multigenomic_extractor.domain.predictions import (
    build_protein_gene_index,
    read_predictions,
    resolve_prediction,
)
from multigenomic_extractor.domain.record_metadata import (
    get_record_organism_id,
    get_record_organism_name,
    get_record_strain_name,
)
from multigenomic_extractor.domain.transcription_builders import (
    InvalidTranscriptionPrediction,
    build_transcription_documents,
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
        predictions_directory: str | None = None,
        metadata_file: str | None = None,
    ):
        input_path = Path(input_directory)
        output_path = Path(output_directory)

        output_path.mkdir(
            parents=True,
            exist_ok=True,
        )

        prediction_files = (
            find_prediction_files(predictions_directory)
            if predictions_directory is not None else {}
        )
        accession_to_assemblies = (
            read_assembly_metadata(metadata_file) if metadata_file else {}
        )
        self.prediction_matches = {}
        self.prediction_warnings = []
        self.assembly_gene_indices = {}
        self.assembly_record_info = {}
        self.protein_gene_indices = {}
        self.protein_gene_warnings = {}
        self._prediction_cache = {}
        self._matched_assemblies = set()

        source_files = list(self.reader.find_files(input_path))

        # Unmapped files are processed first. Then each recognized assembly's
        # GenBank molecules are consecutive, so its predictions can be exported
        # as soon as the last molecule has been processed.
        grouped_sources = {}
        ungrouped_sources = []
        for source_file in source_files:
            try:
                molecule = normalize_molecule(source_file.stem)
            except ValueError:
                ungrouped_sources.append(source_file)
                continue
            candidates = accession_to_assemblies.get(molecule, set()) & prediction_files.keys()
            if len(candidates) == 1:
                assembly = next(iter(candidates))
                grouped_sources.setdefault(assembly, []).append(source_file)
            else:
                ungrouped_sources.append(source_file)
        source_files = ungrouped_sources + [
            source_file
            for assembly in sorted(grouped_sources)
            for source_file in grouped_sources[assembly]
        ]
        last_source_for_assembly = {
            files[-1]: assembly for assembly, files in grouped_sources.items()
        }

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
        progress.label = "Genomas"

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
                if predictions_directory is not None:
                    assembly_ids = record_assembly_ids(record)
                    # The TSV links molecule accessions to GCA/GCF assemblies.
                    # Prefer its explicit mapping; fall back to GenBank metadata.
                    molecule_ids = {record.id, Path(source_file).stem}
                    molecule_ids.update(record.annotations.get('accessions', []))
                    tsv_assemblies = set()
                    for molecule_id in molecule_ids:
                        try:
                            key = normalize_molecule(str(molecule_id))
                        except ValueError:
                            continue
                        tsv_assemblies.update(accession_to_assemblies.get(key, ()))
                    candidates = tsv_assemblies if tsv_assemblies else assembly_ids
                    matching = candidates.intersection(prediction_files)
                    if len(matching) == 1:
                        assembly = next(iter(matching))
                        path = prediction_files[assembly]
                        self._matched_assemblies.add(assembly)
                        self.prediction_matches[(str(source_file), record.id)] = {
                            "assembly": assembly,
                            "path": path,
                        }
                    elif len(matching) > 1:
                        self.prediction_warnings.append(
                            f"{source_file.name}/{record.id}: multiple assembly matches: {sorted(matching)}"
                        )

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

                # Resolver CDS -> gene una vez asignados los IDs definitivos.
                # El índice no se exporta a la colección genes.
                protein_index, warnings = build_protein_gene_index(
                    record, gene_id_map
                )
                record_key = (str(source_file), record.id)
                match = self.prediction_matches.get(record_key)
                if match:
                    assembly = match["assembly"]
                    # Keep provenance per molecule; do not merge conflicting protein IDs.
                    self.assembly_record_info[record_key] = {
                        "source_file": source_file,
                        "organism_name": organism_name,
                        "strain_name": strain_name,
                        "class_acronym": class_acronym,
                    }
                    self.assembly_gene_indices.setdefault(assembly, {})[record_key] = {
                        "organism_id": organism_id,
                        "protein_gene_index": protein_index,
                    }
                if warnings:
                    self.protein_gene_warnings[record_key] = warnings
                    # TODO: Registrar las advertencias con logging.
                    # for warning in warnings:
                    #     print(f"\nAdvertencia predicciones: {warning}")

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

            completed_assembly = last_source_for_assembly.get(source_file)
            if completed_assembly is not None:
                new_documents, new_files = self._export_transcriptions(
                    prediction_files, output_path, assemblies={completed_assembly}
                )
                total_documents += new_documents
                total_files += new_files
            progress.update()

        # Fallback for matches discovered only through record annotations,
        # whose source filenames were not recognized by the TSV.
        remaining = set(self.assembly_gene_indices)
        if remaining:
            new_documents, new_files = self._export_transcriptions(
                prediction_files, output_path, assemblies=remaining
            )
            total_documents += new_documents
            total_files += new_files
        progress.finish()

        if predictions_directory is not None:
            matched = self._matched_assemblies
            print(f"Predictions: {len(prediction_files)} files discovered, "
                  f"{len(matched)} assemblies matched via TSV or explicit GenBank metadata")
            # TODO: Registrar las advertencias con logging.
            # for assembly in sorted(set(prediction_files) - matched):
            #     print(f"Prediction without GenBank assembly match: {assembly}")
            # for warning in self.prediction_warnings:
            #     print(f"Prediction warning: {warning}")

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

    def _export_transcriptions(self, prediction_files, output_path, *, assemblies):
        """Resolve each assembly once; batch Mongo ID allocation per organism."""
        if self.identifier_service is None:
            self.prediction_warnings.append(
                "Skipping TU/operon export: identifier service is required"
            )
            return 0, 0

        document_groups = {}
        pending = {}
        # A separate progress bar tracks prediction resolution, MongoDB ID
        # allocation and JSON export. The final 100% means all three finished.
        available = {
            assembly: self.assembly_gene_indices[assembly]
            for assembly in assemblies
            if assembly in self.assembly_gene_indices and assembly in prediction_files
        }
        prediction_batches = {}
        for assembly in sorted(available):
            path = prediction_files[assembly]
            prediction_batches[assembly] = read_predictions(path)
        prediction_progress = (
            self.progress_factory(sum(len(rows) for rows in prediction_batches.values()) + 2)
            if prediction_batches else None
        )
        if prediction_progress is not None:
            prediction_progress.label = "Predicciones"
        for assembly in sorted(assemblies):
            records = self.assembly_gene_indices.pop(assembly, {})
            if not records or assembly not in prediction_files:
                continue
            predictions = prediction_batches[assembly]
            protein_owners = {}
            for key, item in records.items():
                for protein in item["protein_gene_index"]:
                    protein_owners.setdefault(protein, []).append(key)

            # Progress is displayed by the dedicated prediction bar.
            for prediction in predictions:
                prediction_progress.update()
                owner_sets = [set(protein_owners.get(protein, ()))
                              for protein in prediction.protein_ids]
                common = set.intersection(*owner_sets) if owner_sets else set()
                if len(common) != 1 or any(len(owners) != 1 for owners in owner_sets):
                    self.prediction_warnings.append(
                        f"{assembly}:{prediction.line_number}: proteins missing, "
                        "ambiguous or distributed across molecules"
                    )
                    continue
                key = next(iter(common))
                item = records[key]
                protein_index = item["protein_gene_index"]
                if resolve_prediction(prediction, protein_index) is None:
                    self.prediction_warnings.append(
                        f"{assembly}:{prediction.line_number}: invalid gene/strand mapping"
                    )
                    continue
                info = self.assembly_record_info[key]
                organism_id = item["organism_id"]
                try:
                    operon_preview, tu_preview = build_transcription_documents(
                        prediction, protein_index, organism_id=organism_id,
                        operon_id="RDBMGECOLIOP0000001",
                        transcription_unit_id="RDBMGECOLITU0000001",
                    )
                except InvalidTranscriptionPrediction as error:
                    self.prediction_warnings.append(
                        f"{assembly}:{prediction.line_number}: {error}"
                    )
                    continue

                source_id = f"{assembly}:{key[1]}:{prediction.line_number}"
                operon_seed = {
                    "_id": source_id,
                    "organisms_id": organism_id,
                    "name": operon_preview["name"],
                    "regulationPositions": operon_preview["regulationPositions"],
                    "strand": operon_preview["strand"],
                }
                tu_seed = {
                    "_id": source_id,
                    "organisms_id": organism_id,
                    "name": tu_preview["name"],
                    "genes_ids": tu_preview["genes_ids"],
                }
                # Keep both seeds aligned with the same prediction.
                batch_key = (info["organism_name"], key)
                pending.setdefault(batch_key, []).append(
                    (prediction, protein_index, organism_id, operon_seed, tu_seed)
                )

        for (organism_name, key), items in pending.items():
            operon_seeds = [item[3] for item in items]
            tu_seeds = [item[4] for item in items]
            operon_ids = self.identifier_service.get_or_create_many(
                documents=operon_seeds,
                collection_name="operons",
                organism_name=organism_name,
            )
            tu_ids = self.identifier_service.get_or_create_many(
                documents=tu_seeds,
                collection_name="transcriptionUnits",
                organism_name=organism_name,
            )
            for (prediction, protein_index, organism_id, _, _), operon_id, tu_id in zip(
                items, operon_ids, tu_ids
            ):
                operon, tu = build_transcription_documents(
                    prediction, protein_index, organism_id=organism_id,
                    operon_id=operon_id, transcription_unit_id=tu_id,
                )
                group = document_groups.setdefault(key, {
                    "operons": [], "transcriptionUnits": []
                })
                group["operons"].append(operon)
                group["transcriptionUnits"].append(tu)

        if prediction_progress is not None:
            prediction_progress.update()  # MongoDB identifiers allocated
        total_documents = total_files = 0
        for key, collections in document_groups.items():
            info = self.assembly_record_info[key]
            for collection_name, documents in collections.items():
                if not documents:
                    continue
                wrapper = build_collection_wrapper(
                    collection_name=collection_name,
                    class_acronym=info["class_acronym"],
                    organism_name=info["organism_name"],
                    strain_name=info["strain_name"],
                    documents=documents,
                )
                self.writer.write_collection(
                    output_path=output_path,
                    collection_name=collection_name,
                    source_file=info["source_file"],
                    wrapper_document=wrapper,
                )
                total_documents += len(documents)
                total_files += 1
        for assembly in assemblies:
            for key in list(self.assembly_record_info):
                if key not in self.assembly_record_info:
                    continue
                # Only remove metadata for records belonging to this assembly.
                match = self.prediction_matches.get(key)
                if match and match["assembly"] == assembly:
                    self.assembly_record_info.pop(key, None)
        if prediction_progress is not None:
            prediction_progress.update()  # JSON export completed
            prediction_progress.finish()
        print(f"TUs/operones exportados: {total_documents} documentos", flush=True)
        return total_documents, total_files

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