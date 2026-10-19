"""
Tests for CzDriverLicenseRecognizer (číslo řidičského průkazu).

Format: 2 uppercase letters + 6-9 digits, optionally space-separated.
No public check digit algorithm exists, so validate_result only rejects
clearly-invalid inputs (lowercase prefix such as ordinary words before a
number, all-zero digits). Context words drive final confidence.

All test numbers are fictitious.
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzDriverLicenseRecognizer

# Pattern score from CzDriverLicenseRecognizer.PATTERNS.
_PATTERN_SCORE = 0.3


@pytest.fixture(scope="module")
def recognizer():
    return CzDriverLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CZ_DRIVER_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        ("ED994127", 1, ((0, 8),)),
        ("ED 994127", 1, ((0, 9),)),
        ("CZ123456789", 1, ((0, 11),)),
        ("Řidičský průkaz č. CZ123456789", 1, ((19, 30),)),
        # Lowercase prefix (ordinary Czech words) -> dropped by validation
        ("je 123456", 0, ()),
        ("na 1234567", 0, ()),
        ("cz123456789", 0, ()),
        # All-zero digits -> dropped by validation
        ("CZ000000", 0, ()),
        # Too few digits -> no match
        ("ED 99412", 0, ()),
        # Embedded in a longer run -> no match
        ("CZ1234567890", 0, ()),
        # Glued to a slash/hyphen-delimited identifier -> no match
        ("19-CZ123456789", 0, ()),
        ("spis/CZ123456789", 0, ()),
        # fmt: on
    ],
)
def test_when_all_cz_driver_licenses_then_succeed(
    text, expected_len, expected_positions, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, _PATTERN_SCORE)


@pytest.mark.parametrize(
    "number, expected",
    [
        ("ED994127", None),
        ("ED 994127", None),
        ("CZ123456789", None),
        ("je 123456", False),
        ("ed994127", False),
        ("CZ000000", False),
        ("E1994127", False),
    ],
)
def test_when_cz_driver_license_validated_then_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected
