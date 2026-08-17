import argparse

from multigenomic_extractor.application.use_cases import ExtractMultigenomicDirectoryUseCase
from multigenomic_extractor.infrastructure.adapters.biopython_genbank_reader import BiopythonGenBankReader
from multigenomic_extractor.infrastructure.adapters.json_collection_writer import JsonCollectionWriter
from multigenomic_extractor.infrastructure.adapters.progress_bar import ProgressBar


def build_parser():
    parser = argparse.ArgumentParser(
        description="Extract multigenomic source files into collection JSON files."
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

    return parser


def main():
    args = build_parser().parse_args()

    use_case = ExtractMultigenomicDirectoryUseCase(
        reader=BiopythonGenBankReader(),
        writer=JsonCollectionWriter(),
        progress_factory=ProgressBar,
    )

    use_case.execute(
        input_directory=args.input,
        output_directory=args.output,
    )


if __name__ == "__main__":
    main()
