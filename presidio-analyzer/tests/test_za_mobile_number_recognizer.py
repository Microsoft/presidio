"""Tests for South African mobile number (ZA_MOBILE_NUMBER) recognizer."""

import pytest

from presidio_analyzer.predefined_recognizers import ZaMobileNumberRecognizer
from presidio_analyzer.predefined_recognizers.country_specific.south_africa.za_phone_number_recognizer import (
    ZaPhoneNumberRecognizer,
)

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a ZaMobileNumberRecognizer instance for testing."""
    return ZaMobileNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the ZA_MOBILE_NUMBER entity type for testing."""
    return ["ZA_MOBILE_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        ("+27632118258", 1, ((0, 12),), ((0.4, 1.0),)),
        ("+27615889091", 1, ((0, 12),), ((0.4, 1.0),)),
        ("063 211 8258", 1, ((0, 12),), ((0.4, 1.0),)),
        ("082 560 9352", 1, ((0, 12),), ((0.4, 1.0),)),
        ("+27825609352", 1, ((0, 12),), ((0.4, 1.0),)),
        ("0825609352", 1, ((0, 10),), ((0.4, 1.0),)),
        (
            "My mobile number is +27632118258.",
            1,
            ((20, 32),),
            ((0.4, 1.0),),
        ),
        (
            "Cellphone: 082 560 9352",
            1,
            ((11, 23),),
            ((0.4, 1.0),),
        ),
        ("011 262 5500", 0, (), ()),
        ("021 447 1234", 0, (), ()),
        ("0800 123 456", 0, (), ()),
        ("+14155550132", 0, (), ()),
        ("1234567890", 0, (), ()),
        ("hello world", 0, (), ()),
    ],
)
def test_when_mobile_in_text_then_all_mobile_numbers_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    """Test that ZA mobile recognizer correctly identifies cellular numbers."""
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
    assert recognizer.supported_entities == ["ZA_MOBILE_NUMBER"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


@pytest.mark.parametrize(
    "nsn, expected",
    [
        ("632118258", "mobile"),
        ("825609352", "mobile"),
        ("881234567", "mobile"),
        ("891234567", "mobile"),
        ("800123456", "telephone"),
        ("861234567", "telephone"),
        ("871234567", "telephone"),
        ("112625500", "telephone"),
    ],
)
def test_classify_by_nsn_prefix(nsn, expected):
    """Test NSN fallback when python-phonenumbers returns UNKNOWN."""
    assert ZaPhoneNumberRecognizer._classify_by_nsn_prefix(nsn) == expected
