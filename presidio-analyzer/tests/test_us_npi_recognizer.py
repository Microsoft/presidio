import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import UsNpiRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return UsNpiRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_NPI"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid NPI passes Luhn check → score becomes MAX
        ("1234567893", 1, ((0, 10),), (("max", "max"),),),
        # Another valid NPI
        ("1245319599", 1, ((0, 10),), (("max", "max"),),),
        # Valid NPI (Type 1 = individual)
        ("1003000126", 1, ((0, 10),), (("max", "max"),),),
        # Valid NPI starting with 2 (Type 2 = organization)
        ("2123456784", 1, ((0, 10),), (("max", "max"),),),
        # Invalid: starts with 2 (Type 2) but fails Luhn check → filtered out
        ("2123456783", 0, (), (),),
        # Formatted NPI with dashes — Luhn validates after stripping → MAX
        ("1234-567-893", 1, ((0, 12),), (("max", "max"),),),
        # Formatted NPI with spaces — Luhn validates after stripping → MAX
        ("1234 567 893", 1, ((0, 12),), (("max", "max"),),),
        # NPI in context
        (
            "NPI: 1234567893",
            1, ((5, 15),), (("max", "max"),),
        ),
        # NPI with provider context
        (
            "Provider identifier 1245319599",
            1, ((20, 30),), (("max", "max"),),
        ),
        # Multiple NPIs in text
        (
            "NPI 1234567893 and NPI 1245319599",
            2, ((4, 14), (23, 33),), (("max", "max"), ("max", "max"),),
        ),
        # Invalid: starts with 0
        ("0234567893", 0, (), (),),
        # Invalid: starts with 3
        ("3234567893", 0, (), (),),
        # Invalid: starts with 9
        ("9234567893", 0, (), (),),
        # Invalid: too short (9 digits)
        ("123456789", 0, (), (),),
        # Invalid: too long (11 digits)
        ("12345678934", 0, (), (),),
        # Invalid: degenerate body (all body digits identical) → invalidated
        ("1111111112", 0, (), (),),
        # Invalid: fails Luhn check → filtered out
        ("1234567890", 0, (), (),),
        # fmt: on
    ],
)
def test_when_npi_in_text_then_all_us_npis_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if st_score == "max":
            st_score = max_score
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_npi_recognizer_supported_entity(recognizer):
    """Test that recognizer supports the correct entity."""
    assert recognizer.supported_entities == ["US_NPI"]


def test_npi_recognizer_supported_language(recognizer):
    """Test that recognizer supports English by default."""
    assert recognizer.supported_language == "en"


def test_npi_recognizer_context_words(recognizer):
    """Test that recognizer has appropriate context words."""
    expected_context = [
        "npi",
        "national provider",
        "provider",
        "npi number",
        "provider id",
        "provider identifier",
        "taxonomy",
    ]
    assert recognizer.context == expected_context
