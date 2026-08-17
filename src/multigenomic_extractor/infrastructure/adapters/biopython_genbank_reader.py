from pathlib import Path

from Bio import SeqIO

from multigenomic_extractor.domain.constants import SUPPORTED_EXTENSIONS


class BiopythonGenBankReader:
    def find_files(self, input_path: Path):
        return sorted([
            path for path in input_path.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower()
                in SUPPORTED_EXTENSIONS
            )
        ])

    def parse_records(self, gb_file: Path):
        return SeqIO.parse(
            gb_file,
            "genbank",
        )
