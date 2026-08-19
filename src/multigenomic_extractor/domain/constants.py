SUPPORTED_EXTENSIONS = {
    ".gb",
    ".gbk",
    ".gbff",
    ".genbank",
}

PRODUCT_TYPE_BY_FEATURE_TYPE = {
    "CDS": "polypeptide",
    "rRNA": "rRNA",
    "tRNA": "tRNAs",
    "tmRNA": "tmRNA",
}

COLLECTION_MAPPING = {
    "source": {
        "collectionName": "organisms",
        "subClassAcronym": "OR",
    },
    "gene": {
        "collectionName": "genes",
        "subClassAcronym": "GN",
    },
    "CDS": {
        "collectionName": "products",
        "subClassAcronym": "PD",
    },
    "rRNA": {
        "collectionName": "products",
        "subClassAcronym": "PD",
    },
    "tRNA": {
        "collectionName": "products",
        "subClassAcronym": "PD",
    },
    "tmRNA": {
        "collectionName": "products",
        "subClassAcronym": "PD",
    },
}

ORGANISM_ACRONYMS = {
    "Escherichia coli": "ECOLI",
    "Shigella boydii": "SBOYD",
    "Shigella flexneri": "SFLEX",
    "Shigella sonnei": "SSONN",
}

def get_organism_acronym(
    organism_name: str,
) -> str:
    normalized_name = organism_name.strip()

    for name, acronym in (
        ORGANISM_ACRONYMS.items()
    ):
        if (
            normalized_name == name
            or normalized_name.startswith(
                f"{name} "
            )
        ):
            return acronym

    raise ValueError(
        "No organism acronym configured for "
        f"{organism_name!r}"
    )