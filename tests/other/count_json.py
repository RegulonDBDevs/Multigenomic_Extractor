
import json
from collections import Counter
from pathlib import Path

OUTPUT_DIR = Path("../../output/json")

COLLECTIONS = {
    "ORG": "organisms",
    "GNC": "genes",
    "PDC": "products",
    "OPR": "operons",
    "TUC": "transcriptionUnits",
}

documents = Counter()
files = Counter()
errors = []

for path in OUTPUT_DIR.rglob("*.json"):
    try:
        with path.open("r", encoding="utf-8") as file:
            wrapper = json.load(file)

        collection_code = wrapper.get("subClassAcronym")
        collection = COLLECTIONS.get(collection_code, collection_code)

        data = wrapper.get("collectionData")

        if not isinstance(data, list):
            errors.append(f"{path}: collectionData no es una lista")
            continue

        documents[collection] += len(data)
        files[collection] += 1

    except (OSError, json.JSONDecodeError) as error:
        errors.append(f"{path}: {error}")

print("\nRESULTADOS DE LA EXTRACCIÓN")
print("-" * 55)

for collection in sorted(documents):
    print(
        f"{collection:22} "
        f"{documents[collection]:>12,} documentos "
        f"{files[collection]:>6,} archivos"
    )

print("-" * 55)
print(f"{'TOTAL':22} {sum(documents.values()):>12,} documentos")
print(f"{'ARCHIVOS JSON':22} {sum(files.values()):>12,}")

if errors:
    print(f"\nADVERTENCIAS: {len(errors)}")
    for error in errors[:20]:
        print(error)
