import re


def safe_get_first(values, default=None):
    return values[0] if values else default


def remove_empty(data):
    if isinstance(data, dict):
        cleaned = {
            key: remove_empty(value)
            for key, value in data.items()
        }

        return {
            key: value
            for key, value in cleaned.items()
            if value not in (None, "", [], {})
        }

    if isinstance(data, list):
        cleaned = [remove_empty(item) for item in data]

        return [
            item for item in cleaned
            if item not in (None, "", [], {})
        ]

    return data


def sequence_to_gc(sequence: str) -> float:
    if not sequence:
        return 0.0

    gc_count = sum(
        base in {"G", "C"}
        for base in sequence.upper()
    )

    return round(
        (gc_count / len(sequence)) * 100,
        2,
    )


def calculate_centisome_position(lend, rend, genome_length):
    try:
        lend = float(lend)
        rend = float(rend)
        genome_length = float(genome_length)

        if genome_length == 0:
            raise ZeroDivisionError(
                "Genome size cannot be zero"
            )

        midpoint = (lend + rend) / 2.0

        return round(
            (midpoint / genome_length) * 100,
            2,
        )

    except (TypeError, ValueError) as error:
        raise ValueError(
            "lend, rend and genome_length must be numeric"
        ) from error


def set_gene_type(qualifiers):
    if "pseudo" in qualifiers:
        return "pseudo"

    if "phantom" in qualifiers:
        return "phantom"

    return None


def prefixed_values(qualifiers, keys):
    values = []

    for key in keys:
        for value in qualifiers.get(key, []):
            values.append(f"{key}:{value}")

    return values


def joined_description(qualifiers, keys):
    parts = []

    for key in keys:
        values = qualifiers.get(key, [])

        if values:
            parts.append("; ".join(values))

    return "; ".join(parts)


def join_clean_values(*values, separator="_"):
    valid_values = []

    for value in values:
        if value:
            if isinstance(value, list):
                cleaned_items = [
                    str(item).strip().replace(" ", "_")
                    for item in value
                    if item
                ]

                internal_str = separator.join(cleaned_items)

                if internal_str:
                    valid_values.append(internal_str)

            else:
                cleaned_value = str(value).strip().replace(" ", "_")
                valid_values.append(cleaned_value)

    return separator.join(valid_values)


def normalize_acronym_part(value):
    return "".join(
        char
        for char in str(value).upper()
        if char.isalnum()
    )


def build_class_acronym(organism_name):
    if not organism_name:
        return "UNKNO"

    organism_name_lower = organism_name.lower()

    specific_acronyms = {
        "escherichia coli": "ECOLI",
        "shigella boydii": "SBOYD",
        "shigella flexneri": "SFLEX",
        "shigella sonnei": "SSONN",
    }

    for organism, acronym in specific_acronyms.items():
        if organism in organism_name_lower:
            return acronym

    words = organism_name.split()

    if len(words) >= 2:
        genus = normalize_acronym_part(words[0])
        species = normalize_acronym_part(words[1])

        acronym = genus[:2] + species[:3]

    else:
        acronym = normalize_acronym_part(
            organism_name
        )[:5]

    return acronym.ljust(5, "X")[:5]


def generate_dynamic_id(feature_type, data_dict, keys, separator="_"):
    valid_values = [feature_type]

    for key in keys:
        value = data_dict.get(key)

        if value:
            valid_values.append(
                join_clean_values(value, separator=separator)
            )

    return separator.join(valid_values)

def build_org_name(org_name, strain):
    org_names = [
        "Escherichia coli",
        "Shigella boydii",
        "Shigella flexneri",
        "Shigella sonnei"
    ]

    organism = next(
        (org for org in org_names if org.lower() in org_name.lower()),
        None
    )

    if organism is None:
        return org_name

    patterns = [
        rf"\bstr\.\s*{re.escape(strain)}\b",
        rf"\bstrain\s+{re.escape(strain)}\b",
    ]

    for pattern in patterns:
        org_name = re.sub(pattern, "", org_name, flags=re.IGNORECASE)

    pattern = rf"({re.escape(organism)})\s+{re.escape(strain)}\b"
    org_name = re.sub(
        pattern,
        r"\1",
        org_name,
        flags=re.IGNORECASE
    )

    return re.sub(r"\s+", " ", org_name).strip()

