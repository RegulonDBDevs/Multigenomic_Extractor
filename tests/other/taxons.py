import json
import csv
import time
from pathlib import Path
from Bio import Entrez
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# =========================
# CONFIG
# =========================

INPUT_FOLDER = Path("../../output/json/")
OUTPUT_FILE = Path("organisms_taxon.tsv")

Entrez.email = "betanfig@ccg.unam.mx"


# =========================
# HELPERS
# =========================

def extract_taxon(db_cross_reference):
    if not isinstance(db_cross_reference, list):
        return None

    for value in db_cross_reference:
        if isinstance(value, str) and value.startswith("taxon:"):
            return value.replace("taxon:", "").strip()

    return None


taxon_cache = {}


def get_parent_taxon_name(taxid):
    """
    Obtiene el nombre científico del taxon padre
    desde NCBI Taxonomy.
    """

    if taxid in taxon_cache:
        return taxon_cache[taxid]

    try:
        # Obtener taxon actual
        with Entrez.efetch(
            db="taxonomy",
            id=taxid,
            retmode="xml"
        ) as handle:

            records = Entrez.read(handle)

        if not records:
            return None

        record = records[0]

        parent_taxid = str(
            record.get("ParentTaxId", "")
        )

        # Obtener información del padre
        with Entrez.efetch(
            db="taxonomy",
            id=parent_taxid,
            retmode="xml"
        ) as handle:

            parent_records = Entrez.read(handle)

        if not parent_records:
            return None

        parent_name = parent_records[0].get(
            "ScientificName"
        )

        taxon_cache[taxid] = parent_name

        time.sleep(0.34)

        return parent_name

    except Exception as e:
        print(f"[ERROR] TaxID {taxid}: {e}")
        return None


def process_file(file_path):
    results = []

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    collection_data = data.get("collectionData", [])

    for item in collection_data:

        name = item.get("name")

        strain = (
            item.get("strainName")
            or data.get("strain")
        )

        taxon = extract_taxon(
            item.get("dbCrossReference")
        )

        if not (name and strain and taxon):
            continue

        parent_taxon = get_parent_taxon_name(taxon)

        results.append(
            (
                name,
                strain,
                taxon,
                parent_taxon
            )
        )

    return results


# =========================
# MAIN
# =========================

def main():

    unique_results = set()

    for file_path in INPUT_FOLDER.glob("organisms*.json"):

        print(f"Procesando: {file_path.name}")

        rows = process_file(file_path)

        unique_results.update(rows)

    sorted_results = sorted(unique_results)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
        newline=""
    ) as f:

        writer = csv.writer(
            f,
            delimiter="\t"
        )

        writer.writerow(
            [
                "name",
                "strain",
                "taxon",
                "parent_taxon"
            ]
        )

        writer.writerows(sorted_results)

    print(f"\nTSV generado: {OUTPUT_FILE}")
    print(f"Registros únicos: {len(sorted_results)}")


if __name__ == "__main__":
    main()