from typing import Callable, Dict

from multigenomic_extractor.domain.constants import PRODUCT_TYPE_BY_FEATURE_TYPE
from multigenomic_extractor.domain.feature_context import build_feature_context
from multigenomic_extractor.domain.helpers import (
    build_org_name,
    calculate_centisome_position,
    join_clean_values,
    joined_description,
    prefixed_values,
    remove_empty,
    safe_get_first,
    sequence_to_gc,
    set_gene_type,
)

FEATURE_BUILDERS: Dict[str, Callable] = {}


def register_feature_builder(feature_type: str):
    def decorator(func):
        FEATURE_BUILDERS[feature_type] = func
        return func

    return decorator


def build_default_id(ctx):
    qualifiers = ctx["qualifiers"]

    return (
        safe_get_first(qualifiers.get("ID"))
        or safe_get_first(qualifiers.get("protein_id"))
        or safe_get_first(qualifiers.get("locus_tag"))
        or safe_get_first(qualifiers.get("gene"))
        or f"{ctx['feature_type']}_{ctx['start']}_{ctx['end']}"
    )


def build_location(ctx):
    return {
        "start": ctx["start"],
        "end": ctx["end"],
        "strand": ctx["strand"],
        "length": len(ctx["dna_seq"]),
    }


def build_location_segments(ctx):
    location = ctx["feature"].location

    if hasattr(location, "parts") and location.parts:
        return [
            {
                "leftEndPosition": int(part.start),
                "rightEndPosition": int(part.end),
                "strand": part.strand,
            }
            for part in location.parts
        ]

    return [
        {
            "leftEndPosition": ctx["start"],
            "rightEndPosition": ctx["end"],
            "strand": ctx["strand"],
        }
    ]


def build_generic_feature(ctx):
    return {
        "_id": build_default_id(ctx),
        "sourceFile": ctx["source_file"],
        "location": build_location(ctx),
        "qualifiers": ctx["qualifiers"],
        "sequence": {
            "dna": ctx["dna_seq"],
        },
        "statistics": {
            "gcContent": sequence_to_gc(ctx["dna_seq"]),
        },
    }


@register_feature_builder("source")
def build_source_document(ctx):
    record = ctx["record"]
    qualifiers = ctx["qualifiers"]

    organism_id = ctx.get("organism_id")

    return {
        "_id": organism_id,
        "sourceFile": ctx.get("source_file"),
        "name": build_org_name(
            (
                safe_get_first(qualifiers.get("organism"))
                or record.annotations.get("organism")
            ),
            safe_get_first(
                qualifiers.get("strain")
            )
        ),
        "description": joined_description(
            qualifiers,
            [
                "note",
            ],
        ),
        "strainName": safe_get_first(
            qualifiers.get("strain")
        ),
        "synonyms": prefixed_values(
            qualifiers,
            [
                "culture_collection",
                "sub_strain",
                "sero_type",
                "serovar",
                "biotype",
                "sub_species",
            ],
        ),
        "dbCrossReference": qualifiers.get("db_xref"),
        "pgdbName": join_clean_values(
            qualifiers.get("plasmid"),
            ctx.get("source_file"),
        ),
        "plasmidName": safe_get_first(
            qualifiers.get("plasmid")
        ),
        "type": (
            "plasmid"
            if safe_get_first(qualifiers.get("plasmid")) is not None
            else "chromosome"
        ),
        "genomeVersion": record.id,
        "genomeSize": len(record.seq),
    }


@register_feature_builder("gene")
def build_gene_document(ctx):
    record = ctx["record"]
    qualifiers = ctx["qualifiers"]

    gene_name = safe_get_first(
        qualifiers.get("gene")
    )

    locus_tag = safe_get_first(
        qualifiers.get("locus_tag")
    )

    synonyms = []

    if gene_name:
        synonyms.append(gene_name)

    synonyms.extend(
        qualifiers.get("gene_synonym", [])
    )

    return {
        "_id": (
            locus_tag
            or gene_name
            or build_default_id(ctx)
        ),
        "name": gene_name,
        "bnumber": locus_tag,
        "leftEndPosition": ctx["start"],
        "rightEndPosition": ctx["end"],
        "strand": ctx["strand"],
        "sequence": ctx["dna_seq"],
        "gcContent": sequence_to_gc(
            ctx["dna_seq"]
        ),
        "centisomePosition": calculate_centisome_position(
            ctx["start"],
            ctx["end"],
            len(record.seq),
        ),
        "synonyms": synonyms,
        "note": safe_get_first(
            qualifiers.get("note")
        ),
        "type": set_gene_type(qualifiers),
        "organisms_id": ctx.get("organism_id"),
    }


def build_product_synonyms(qualifiers):
    synonyms = []

    for key in [
        "gene",
        "locus_tag",
        "protein_id",
    ]:
        for value in qualifiers.get(key, []):
            synonyms.append(f"{key}:{value}")

    return synonyms


def get_product_sequence(ctx):
    qualifiers = ctx["qualifiers"]

    if ctx["feature_type"] == "CDS":
        return safe_get_first(
            qualifiers.get("translation")
        )

    return ctx["dna_seq"]


def build_product_id(ctx):
    qualifiers = ctx["qualifiers"]

    return (
        safe_get_first(qualifiers.get("protein_id"))
        or (
            f"product_{safe_get_first(qualifiers.get('locus_tag'))}"
            if safe_get_first(qualifiers.get("locus_tag"))
            else None
        )
        or build_default_id(ctx)
    )


def build_product_name(ctx):
    qualifiers = ctx["qualifiers"]

    return (
        safe_get_first(qualifiers.get("product"))
        or safe_get_first(qualifiers.get("gene"))
        or safe_get_first(qualifiers.get("locus_tag"))
        or build_product_id(ctx)
    )


def build_product_document(ctx):
    qualifiers = ctx["qualifiers"]

    gene_name = safe_get_first(
        qualifiers.get("gene")
    )

    locus_tag = safe_get_first(
        qualifiers.get("locus_tag")
    )

    product_type = PRODUCT_TYPE_BY_FEATURE_TYPE.get(
        ctx["feature_type"]
    )

    return {
        "_id": build_product_id(ctx),
        "type": product_type,
        "name": build_product_name(ctx),
        "abbreviatedName": gene_name,
        "genes_id": (
            locus_tag
            or gene_name
        ),
        "note": safe_get_first(
            qualifiers.get("note")
        ),
        "sequence": get_product_sequence(ctx),
        "synonyms": build_product_synonyms(
            qualifiers
        ),
        "organisms_id": ctx.get("organism_id"),
    }


for feature_type in PRODUCT_TYPE_BY_FEATURE_TYPE:
    register_feature_builder(feature_type)(
        build_product_document
    )


def normalize_feature(
    record,
    feature,
    source_file: str,
    organism_id: str = None,
):
    ctx = build_feature_context(
        record=record,
        feature=feature,
        source_file=source_file,
        organism_id=organism_id,
    )

    builder = FEATURE_BUILDERS.get(
        feature.type,
        build_generic_feature,
    )

    document = builder(ctx)

    return remove_empty(document)
