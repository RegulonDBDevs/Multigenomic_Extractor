# MultigenomicExtractor

Hexagonal-architecture project for extracting multigenomic source files into collection-based JSON files.

The current adapter reads GenBank files (`.gb`, `.gbk`, `.gbff`, `.genbank`) using BioPython. The design keeps the use case separate from the input format so that other adapters can be added later.

## Structure

```txt
MultigenomicExtractor/
├── main.py
├── pyproject.toml
├── src/
│   └── multigenomic_extractor/
│       ├── domain/
│       ├── application/
│       ├── infrastructure/
│       │   ├── adapters/
│       │   └── cli/
│       └── shared/
└── tests/
    ├── unit/
    └── use_cases/
```

## Layers

- `domain/`: pure normalization logic, builders, helpers, metadata, and wrappers.
- `application/`: the main `ExtractMultigenomicDirectoryUseCase` use case and ports.
- `infrastructure/`: concrete adapters—currently a BioPython GenBank reader, JSON writer, and CLI.
- `tests/unit/`: helper, wrapper, and metadata tests.
- `tests/use_cases/`: use-case flow tests with fake adapters.

## Usage without installing the project

```bash
pip install biopython
py main.py --input ../download_genome/genomes/genbank --output ./output/json/
```

## Optional installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
multigenomic-extractor --input ./genomes/genbank --output ./output/json
```

## Tests

```bash
pip install -e .[dev]
pytest
```

Or, without installing the project:

```bash
PYTHONPATH=src pytest
```

## Output

For each supported source file, the extractor generates files such as:

```txt
organisms_{file}.json
genes_{file}.json
products_{file}.json
```

Each file uses the following wrapper structure:

```json
{
  "classAcronym": "ESCOL",
  "collectionName": "genes",
  "subClassAcronym": "GNC",
  "organism": "Escherichia coli",
  "strain": "536",
  "collectionData": []
}
```
