def normalize_strand(
    strand: int | None,
) -> str | None:
    if strand == 1:
        return "forward"

    if strand == -1:
        return "reverse"

    return None


def build_feature_context(
    record,
    feature,
    source_file: str,
    organism_id: str = None,
):
    dna_seq = str(
        feature.extract(record.seq)
    )

    start = int(
        feature.location.start
    )

    end = int(
        feature.location.end
    )

    return {
        "record": record,
        "feature": feature,
        "source_file": source_file,
        "organism_id": organism_id,
        "qualifiers": feature.qualifiers,
        "dna_seq": dna_seq,
        "start": start,
        "end": end,
        "strand": normalize_strand(
            feature.location.strand
        ),
        "feature_type": feature.type,
    }