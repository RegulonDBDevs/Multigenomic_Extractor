# MultigenomicExtractor

Hexagonal-architecture project for extracting multigenomic source files into collection-based JSON files.

The current adapter reads GenBank files (`.gb`, `.gbk`, `.gbff`, `.genbank`) using BioPython. The design keeps the use case separate from the input format so that other source adapters can be added later.

The extractor also supports RegulonDB Multi-Genomic identifier generation, MongoDB sequence counters, JSON Schema-based collection creation, and batch uploading of extracted objects to MongoDB.

## Structure

```txt
MultigenomicExtractor/
├── main.py
├── pyproject.toml
├── output/
│   └── json/
├── src/
│   └── multigenomic_extractor/
│       ├── domain/
│       │   ├── identifiers/
│       │   └── schemas/
│       │       ├── organisms.json
│       │       ├── genes.json
│       │       └── products.json
│       ├── application/
│       │   └── upload_to_mongo.py
│       ├── infrastructure/
│       │   ├── adapters/
│       │   └── cli/
│       └── shared/
└── tests/
    ├── unit/
    └── use_cases/
```

## Layers

- `domain/`: pure normalization logic, builders, helpers, identifier properties, metadata, wrappers, and MongoDB collection schemas.
- `application/`: extraction use cases, ports, identifier services, and independent utilities such as the MongoDB uploader.
- `infrastructure/`: concrete adapters, including the BioPython GenBank reader, JSON writer, MongoDB identifier repository, and CLI.
- `tests/unit/`: helper, wrapper, metadata, and domain tests.
- `tests/use_cases/`: use-case flow tests with fake adapters.

## Main extraction flow

The current GenBank extraction process is:

```text
GenBank file
    │
    ├── chromosome
    │      ├── organism
    │      ├── genes
    │      └── products
    │
    └── plasmid(s)
           ├── organism
           ├── genes
           └── products
```

Chromosomes and plasmids are treated as independent organism objects.

Each generated organism, gene, and product receives a RegulonDB Multi-Genomic identifier during extraction.

## RegulonDB Multi-Genomic identifiers

Identifiers follow the structure:

```text
RDBMG{ORGANISM_ACRONYM}{COLLECTION_ACRONYM}{SEQUENTIAL_ID}
```

Example:

```text
RDBMG ECOLI GN 0000001
│     │     │  └──────── sequential number
│     │     └─────────── collection acronym
│     └───────────────── organism acronym
└─────────────────────── RegulonDB Multi-Genomic
```

The generic identifier pattern is:

```regex
^RDBMG[A-Z]{7}[0-9]{7}$
```

Examples:

```text
RDBMGECOLIOR0000001
RDBMGECOLIGN0000001
RDBMGECOLIPD0000001
RDBMGSBOYDGN0000001
RDBMGSFLEXGN0000001
RDBMGSSONNGN0000001
```

### Organism acronyms

| Organism | Acronym |
| --- | --- |
| *Escherichia coli* | `ECOLI` |
| *Shigella boydii* | `SBOYD` |
| *Shigella flexneri* | `SFLEX` |
| *Shigella sonnei* | `SSONN` |

### Collection acronyms

| Collection | Acronym |
| --- | --- |
| `evidences` | `EV` |
| `externalCrossReferences` | `ER` |
| `genes` | `GN` |
| `motifs` | `MT` |
| `operons` | `OP` |
| `organisms` | `OR` |
| `products` | `PD` |
| `promoters` | `PM` |
| `promoterFeatures` | `PF` |
| `publications` | `PR` |
| `regulatoryComplexes` | `RC` |
| `regulatoryContinuants` | `CN` |
| `regulatoryInteractions` | `RI` |
| `sigmaFactors` | `SF` |
| `terminators` | `TM` |
| `transcriptionFactors` | `TF` |
| `regulatorySites` | `BS` |
| `transcriptionUnits` | `TU` |

The seven-digit sequential section allows up to 9,999,999 identifiers for each organism and collection combination.

## Identifier storage

Generated identifiers are stored in the MongoDB `identifiers` collection.

The properties used to determine whether an identifier already exists depend on the collection.

For organisms, the identifying properties include:

```text
name
strainName
type
sourceFile
plasmidName (when available)
```

`sourceFile` is normalized without its GenBank file extension when it is used as an identifying property.

This allows different GenBank accessions representing organisms with the same name and strain to receive different identifiers.

Products also include their gene reference as part of their identifying properties so that products associated with different genes are treated as different objects.

## Sequence counters

Sequential identifier values are managed in the MongoDB `sequences` collection.

Counters are differentiated by:

```text
database
organism
collection
collection acronym
```

For example, gene identifiers for `ECOLI` use a sequence independent from organism or product identifiers.

This prevents scanning the identifiers collection to calculate the next sequential identifier and significantly improves extraction performance.

## Usage without installing the project

Install the required dependencies:

```bash
pip install biopython pymongo
```

Run the extractor:

```bash
python main.py \
    --input ../download_genome/genomes/genbank/ \
    --output ./output/json/ \
    --mongo-url "mongodb://localhost:27017" \
    --identifiers-db Multigenomic_TESTING \
    --rdb-version "14.4.0" \
    --source-name "GenBank"
```

For authenticated MongoDB connections, credentials can be included in the connection URI:

```bash
python main.py \
    --input ../download_genome/genomes/genbank/ \
    --output ./output/json/ \
    --mongo-url "mongodb://USER:PASSWORD@localhost:27017/?authSource=admin" \
    --identifiers-db Multigenomic_TESTING \
    --rdb-version "14.4.0" \
    --source-name "GenBank"
```

## Optional installation

```bash
python -m venv .venv
source .venv/bin/activate

pip install -e .

multigenomic-extractor \
    --input ./genomes/genbank \
    --output ./output/json
```

## Output

For each supported GenBank record, the extractor generates collection files such as:

```text
organisms_{file}.json
genes_{file}.json
products_{file}.json
```

Each file uses a collection wrapper. For example:

```json
{
  "classAcronym": "ECOLI",
  "collectionName": "genes",
  "subClassAcronym": "GN",
  "organism": "Escherichia coli",
  "strain": "536",
  "collectionData": []
}
```

Only the objects inside `collectionData` are uploaded to their corresponding MongoDB collection.

## Strand normalization

BioPython represents feature strand direction using numeric values:

```text
 1  -> forward
-1  -> reverse
```

The extractor normalizes these values to the representation expected by the RegulonDB collection schemas:

```json
{
  "strand": "forward"
}
```

or:

```json
{
  "strand": "reverse"
}
```

## MongoDB collection schemas

MongoDB JSON Schemas are stored in:

```text
src/multigenomic_extractor/domain/schemas/
```

Currently supported schemas are:

```text
organisms.json
genes.json
products.json
```

The schemas define the MongoDB collection validator, validation level, and validation action.

Identifiers use the generic RegulonDB Multi-Genomic pattern:

```regex
^RDBMG[A-Z]{7}[0-9]{7}$
```

DNA sequence fields support IUPAC nucleotide symbols, including ambiguous bases such as `N`.

## MongoDB uploader

The project includes an independent uploader:

```text
src/multigenomic_extractor/application/upload_to_mongo.py
```

The uploader:

1. Reads the MongoDB JSON Schemas.
2. Creates the `organisms`, `genes`, and `products` collections.
3. Applies or updates their MongoDB validators.
4. Reads the generated files from `./output/json/`.
5. Uses `collectionName` to determine the target collection.
6. Extracts the objects from `collectionData`.
7. Inserts documents in batches.
8. Displays upload progress.
9. Reports MongoDB validation or duplicate identifier errors when encountered.

Collections are processed in the following order:

```text
organisms
    ↓
genes
    ↓
products
```

### Upload extracted data

```bash
python src/multigenomic_extractor/application/upload_to_mongo.py \
    --input ./output/json \
    --schemas ./src/multigenomic_extractor/domain/schemas \
    --mongo-url "mongodb://localhost:27017" \
    --database Multigenomic_TESTING
```

### Clean database upload

During testing or when rebuilding the target collections, use:

```bash
python src/multigenomic_extractor/application/upload_to_mongo.py \
    --input ./output/json \
    --schemas ./src/multigenomic_extractor/domain/schemas \
    --mongo-url "mongodb://localhost:27017" \
    --database Multigenomic_TESTING \
    --drop-collections
```

`--drop-collections` removes the supported target collections before recreating them from their schemas.

It does not remove the `identifiers` or `sequences` collections.

### Batch size

The default batch size is:

```text
1000 documents
```

It can be changed with:

```bash
--batch-size 2000
```

For example:

```bash
python src/multigenomic_extractor/application/upload_to_mongo.py \
    --mongo-url "mongodb://localhost:27017" \
    --database Multigenomic_TESTING \
    --batch-size 2000 \
    --drop-collections
```

### Upload progress

During a normal upload, the script keeps the progress information on a single terminal line:

```text
Uploading [██████████████----------------] 47% | 185320/392450 docs | genes | genes_CP010829.json
```

If MongoDB rejects a document, the progress line is cleared and the uploader reports the source file, collection, batch, and MongoDB error details.

## Recommended clean extraction

When changing the rules used by `propertiesToMakeId`, existing identifiers are no longer necessarily compatible with newly generated objects.

For a complete test regeneration:

1. Remove old generated JSON files from `./output/json/`.
2. Remove the test identifiers generated using the previous rules.
3. Reset the corresponding test sequence counters.
4. Run the extractor again.
5. Run the MongoDB uploader with `--drop-collections`.

This prevents identifiers generated using different uniqueness rules from being mixed in the same test dataset.

## Tests

Install development dependencies:

```bash
pip install -e .[dev]
```

Run:

```bash
pytest
```

Or, without installing the project:

```bash
PYTHONPATH=src pytest
```