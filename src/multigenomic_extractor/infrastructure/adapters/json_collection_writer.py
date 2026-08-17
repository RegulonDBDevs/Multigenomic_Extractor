import json
from pathlib import Path


class JsonCollectionWriter:
    def write_collection(
        self,
        output_path: Path,
        collection_name: str,
        source_file: Path,
        wrapper_document: dict,
    ) -> None:
        output_file = (
            output_path /
            f"{collection_name}_{source_file.stem}.json"
        )

        with open(
            output_file,
            "w",
            encoding="utf-8",
        ) as writer:
            json.dump(
                wrapper_document,
                writer,
                ensure_ascii=False,
                indent=4,
            )
