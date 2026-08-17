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
        "subClassAcronym": "ORG",
    },
    "gene": {
        "collectionName": "genes",
        "subClassAcronym": "GNC",
    },
    "CDS": {
        "collectionName": "products",
        "subClassAcronym": "PDC",
    },
    "rRNA": {
        "collectionName": "products",
        "subClassAcronym": "PDC",
    },
    "tRNA": {
        "collectionName": "products",
        "subClassAcronym": "PDC",
    },
    "tmRNA": {
        "collectionName": "products",
        "subClassAcronym": "PDC",
    },
}
