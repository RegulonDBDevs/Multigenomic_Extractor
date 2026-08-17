import pytest

from multigenomic_extractor.domain.helpers import (
    build_class_acronym,
    calculate_centisome_position,
    generate_dynamic_id,
    remove_empty,
    sequence_to_gc,
)


def test_build_class_acronym_uses_two_genus_and_three_species_letters():
    assert build_class_acronym("Escherichia coli") == "ESCOL"
    assert build_class_acronym("Bacillus subtilis") == "BASUB"


def test_build_class_acronym_returns_five_chars_for_single_word():
    assert build_class_acronym("Unknown") == "UNKNO"


def test_sequence_to_gc_returns_percentage():
    assert sequence_to_gc("ATGC") == 50.0


def test_calculate_centisome_position():
    assert calculate_centisome_position(0, 50, 100) == 25.0


def test_calculate_centisome_position_rejects_non_numeric_values():
    with pytest.raises(ValueError):
        calculate_centisome_position("x", 50, 100)


def test_generate_dynamic_id_joins_values_and_lists():
    dynamic_id = generate_dynamic_id(
        "organism",
        {
            "organism": ["Escherichia coli"],
            "strain": ["536"],
        },
        ["organism", "strain"],
    )

    assert dynamic_id == "organism_Escherichia_coli_536"


def test_remove_empty_removes_empty_nested_values():
    assert remove_empty({"a": None, "b": "x", "c": [], "d": {"e": ""}}) == {"b": "x"}
