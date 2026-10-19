"""
Tests for CzPassportRecognizer (číslo cestovního pasu).

Format: 2 uppercase letters + 6-7 digits (older series) or 7-8 digits
(current biometric series). No public check digit algorithm exists, so
validate_result only rejects clearly-invalid inputs (lowercase letter
prefix, all-zero digits). Context words drive final confidence.

All test numbers are fictitious.
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzPassportRecognizer

# Pattern scores from CzPassportRecognizer.PATTERNS.
_LETTER_SCORE = 0.3
_DIGITS_SCORE = 0.1


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # Letter-prefixed series
        ("AB123456", 1, ((0, 8),), _LETTER_SCORE),
        ("AB 123456", 1, ((0, 9),), _LETTER_SCORE),
        ("AB1234567", 1, ((0, 9),), _LETTER_SCORE),
        ("číslo cestovního pasu je AB123456.", 1, ((25, 33),), _LETTER_SCORE),
        # Digit-only biometric series (low base score, context-driven)
        ("39182634", 1, ((0, 8),), _DIGITS_SCORE),
        ("cestovní pas č. 39182634", 1, ((16, 24),), _DIGITS_SCORE),
        # Lowercase prefix (ordinary words) -> dropped by validation
        ("ab123456", 0, (), None),
        ("je 123456", 0, (), None),
        # All-zero digits -> dropped by validation
        ("AB000000", 0, (), None),
        # Too many digits for the letter-prefixed series -> no match
        ("AB123456789", 0, (), None),
        # Embedded in a longer digit run -> no match
        ("391826341234", 0, (), None),
        # Glued to a slash/hyphen-delimited identifier -> no match
        ("č. j. 123-AB123456", 0, (), None),
        ("spis/AB123456", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_cz_passports_then_succeed(
    text, expected_len, expected_positions, expected_score
):
    recognizer = CzPassportRecognizer()
    entities = ["CZ_PASSPORT"]
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


@pytest.mark.parametrize(
    "number, expected",
    [
        ("AB123456", None),
        ("AB 1234567", None),
        ("39182634", None),
        ("ab123456", False),
        ("Ab123456", False),
        ("AB000000", False),
        ("0000000", False),
    ],
)
def test_when_cz_passport_validated_then_result_is_correct(number, expected):
    recognizer = CzPassportRecognizer()
    assert recognizer.validate_result(number) == expected
