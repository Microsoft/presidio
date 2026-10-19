"""Tests for Turkish Tax ID (VKN) recognizer."""

import pytest
from presidio_analyzer.predefined_recognizers import TrTaxIdRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a Turkish VKN recognizer instance for testing."""
    return TrTaxIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Turkish VKN entity type for testing."""
    return ["TR_TAX_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid VKNs with correct checksum
        ("5260181599", 1, ((0, 10),), ((0.5, 1.0),),),
        ("0830166136", 1, ((0, 10),), ((0.5, 1.0),),),
        ("1860913903", 1, ((0, 10),), ((0.5, 1.0),),),
        ("9960308245", 1, ((0, 10),), ((0.5, 1.0),),),
        ("6281948215", 1, ((0, 10),), ((0.5, 1.0),),),
        ("9935181908", 1, ((0, 10),), ((0.5, 1.0),),),
        ("9378657978", 1, ((0, 10),), ((0.5, 1.0),),),
        ("5432319485", 1, ((0, 10),), ((0.5, 1.0),),),
        # Valid VKNs in sentences
        (
            "Vergi Kimlik No: 5260181599",
            1,
            ((17, 27),),
            ((0.5, 1.0),),
        ),
        (
            "Sirketin VKN numarasi 0830166136 olarak tescil edilmistir.",
            1,
            ((22, 32),),
            ((0.5, 1.0),),
        ),
        # Multiple valid VKNs
        (
            "Birinci firma: 5260181599, ikinci firma: 0830166136",
            2,
            ((15, 25), (41, 51),),
            ((0.5, 1.0), (0.5, 1.0),),
        ),
        # Invalid VKNs - wrong checksum
        ("5260181598", 0, (), (),),
        ("0830166130", 0, (), (),),
        ("6281948210", 0, (), (),),
        ("9378657970", 0, (), (),),
        # Invalid VKNs - wrong length
        ("123456789", 0, (), (),),
        ("12345678901", 0, (), (),),
        # Invalid VKNs - non-digits
        ("abcdefghij", 0, (), (),),
        # Context enhancement
        (
            "Turkish tax id 1860913903",
            1,
            ((15, 25),),
            ((0.5, 1.0),),
        ),
        (
            "Mukellef vergi numarasi 9960308245",
            1,
            ((24, 34),),
            ((0.5, 1.0),),
        ),
    ],
)
def test_when_vkn_in_text_then_all_vkns_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Test that Turkish VKN recognizer correctly identifies VKNs."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_validate_result_with_valid_vkn(recognizer):
    """Test validate_result method with valid VKNs."""
    assert recognizer.validate_result("5260181599") is True
    assert recognizer.validate_result("0830166136") is True
    assert recognizer.validate_result("1860913903") is True
    assert recognizer.validate_result("9960308245") is True
    assert recognizer.validate_result("6281948215") is True
    assert recognizer.validate_result("9935181908") is True
    assert recognizer.validate_result("9378657978") is True
    assert recognizer.validate_result("5432319485") is True


def test_validate_result_with_leading_zero(recognizer):
    """Unlike the 11-digit TCKN, a VKN may legitimately start with 0."""
    assert recognizer.validate_result("0830166136") is True


def test_validate_result_with_wrong_checksum(recognizer):
    """Test validate_result method with wrong checksum."""
    assert recognizer.validate_result("5260181598") is False
    assert recognizer.validate_result("0830166130") is False
    assert recognizer.validate_result("6281948210") is False
    assert recognizer.validate_result("9378657970") is False


def test_validate_result_with_wrong_length(recognizer):
    """Test validate_result method with wrong length."""
    assert recognizer.validate_result("123456789") is False
    assert recognizer.validate_result("12345678901") is False


def test_validate_result_with_non_digits(recognizer):
    """Test validate_result method with non-digit characters."""
    assert recognizer.validate_result("abcdefghij") is False


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "vergi kimlik",
        "vergi kimlik no",
        "vergi kimlik numarası",
        "vkn",
        "vergi no",
        "vergi numarası",
        "mükellef",
        "tax id",
        "tax number",
        "turkish tax",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["TR_TAX_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "tr"


def test_country_code(recognizer):
    """Test that the country code is correctly set."""
    assert recognizer.COUNTRY_CODE == "tr"
