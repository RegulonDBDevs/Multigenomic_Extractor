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
