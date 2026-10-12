"""Tests for South African telephone number (ZA_TELEPHONE_NUMBER) recognizer."""

import pytest

from presidio_analyzer.predefined_recognizers import ZaTelephoneNumberRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a ZaTelephoneNumberRecognizer instance for testing."""
    return ZaTelephoneNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the ZA_TELEPHONE_NUMBER entity type for testing."""
    return ["ZA_TELEPHONE_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        ("011 262 5500", 1, ((0, 12),), ((0.4, 1.0),)),
        ("021 447 1234", 1, ((0, 12),), ((0.4, 1.0),)),
        ("010 222 0057", 1, ((0, 12),), ((0.4, 1.0),)),
        ("(011) 390-9872", 1, ((0, 14),), ((0.4, 1.0),)),
        ("0800 123 456", 1, ((0, 12),), ((0.4, 1.0),)),
        ("0860 123 456", 1, ((0, 12),), ((0.4, 1.0),)),
        ("H(011)3909872", 1, ((1, 13),), ((0.4, 1.0),)),
        (
            "Landline (011) 262-5500 on file.",
            1,
            ((9, 23),),
            ((0.4, 1.0),),
        ),
        (
            "H(011)3909872 B(011)4517333",
            2,
            ((1, 13), (15, 27)),
            ((0.4, 1.0), (0.4, 1.0)),
        ),
        ("082 560 9352", 0, (), ()),
        ("+27632118258", 0, (), ()),
        ("+14155550132", 0, (), ()),
        ("1234567890", 0, (), ()),
        ("hello world", 0, (), ()),
    ],
)
def test_when_telephone_in_text_then_all_telephone_numbers_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Test that ZA telephone recognizer identifies landline and service numbers."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["ZA_TELEPHONE_NUMBER"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"
