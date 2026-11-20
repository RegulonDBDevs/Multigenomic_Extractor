
#!/usr/bin/env python3
"""List external database names referenced in GenBank files."""

import argparse
import gzip
import re
from collections import Counter, defaultdict
from pathlib import Path

from Bio import SeqIO


REFSEQ_PROTEIN = re.compile(
    r"^(?:WP|NP|XP|YP|AP|ZP)_\d+(?:\.\d+)?$",
    re.IGNORECASE,
)

INFERENCE_SOURCE = re.compile(
    r"(?:similar to .*? sequence|sequence)\s*:"
    r"\s*([A-Za-z][A-Za-z0-9_.-]*)\s*:"
    r"\s*([^\s,;]+)",
    re.IGNORECASE,
)


def open_genbank(path):
    if path.name.lower().endswith(".gz"):
        return gzip.open(path, "rt", encoding="utf-8")

    return path.open("r", encoding="utf-8")


def list_genbank_files(directory):
    return sorted(
        path
        for path in directory.rglob("*")
        if path.is_file()
        and path.name.lower().endswith(
            (".gb", ".gbk", ".genbank",
             ".gb.gz", ".gbk.gz", ".genbank.gz")
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="List external databases in GenBank files."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing GenBank files.",
    )
    parser.add_argument(
        "--examples",
        type=int,
        default=5,
        help="Maximum examples per database.",
    )

    args = parser.parse_args()

    if not args.directory.is_dir():
        parser.error("The supplied directory does not exist.")

    counts = Counter()
    examples = defaultdict(set)
    feature_types = defaultdict(Counter)

    files = list_genbank_files(args.directory)

    print(f"GenBank files found: {len(files)}")

    for index, path in enumerate(files, start=1):
        print(
            f"\rProcessing {index}/{len(files)}: {path.name[:60]}",
            end="",
            flush=True,
        )

        with open_genbank(path) as handle:
            for record in SeqIO.parse(handle, "genbank"):
                for feature in record.features:
                    qualifiers = feature.qualifiers

                    references = []

                    # db_xref: GeneID:12345
                    for value in qualifiers.get("db_xref", []):
                        database, separator, identifier = value.partition(":")

                        if separator and database and identifier:
                            references.append(
                                (database.strip(), identifier.strip())
                            )

                    # inference: sequence:RefSeq:WP_...
                    for value in qualifiers.get("inference", []):
                        for match in INFERENCE_SOURCE.finditer(value):
                            references.append(
                                (match.group(1), match.group(2))
                            )

                    # protein_id: RefSeq accessions
                    for value in qualifiers.get("protein_id", []):
                        if REFSEQ_PROTEIN.fullmatch(value):
                            references.append(("RefSeq", value))

                    # Avoid counting the same reference twice
                    for database, identifier in set(references):
                        counts[database] += 1
                        feature_types[database][feature.type] += 1

                        if len(examples[database]) < args.examples:
                            examples[database].add(identifier)

    print("\n\nExternal databases found:\n")

    for database, count in counts.most_common():
        types = ", ".join(
            f"{name}:{amount}"
            for name, amount in feature_types[database].most_common()
        )

        print(f"{database}: {count:,}")
        print(f"  Features: {types}")
        print(f"  Examples: {', '.join(sorted(examples[database]))}")
        print()

    print(f"Total distinct database names: {len(counts)}")
    print(f"Total references: {sum(counts.values()):,}")


if __name__ == "__main__":
    main()
