"""
Tests for CzIdCardRecognizer (číslo občanského průkazu).

Format: 9 digits (machine readable cards / eOP). No publicly documented
check digit exists, so validate_result only rejects clearly-invalid inputs
(wrong length, non-digit, all-zero) and returns None for every other
9-digit input. Context words drive final confidence via the enhancer.

All test numbers are fictitious.
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzIdCardRecognizer

# Pattern score from CzIdCardRecognizer.PATTERNS. validate_result returns
# None on all structurally-valid inputs, so matches keep this score.
_PATTERN_SCORE = 0.2


@pytest.fixture(scope="module")
def recognizer():
    return CzIdCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CZ_ID_CARD"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Structurally valid -> pattern score (context boosts in pipeline)
        ("123456789", 1, ((0, 9),)),
        ("987654321", 1, ((0, 9),)),
        ("Číslo OP: 123456789", 1, ((10, 19),)),
        ("číslo občanského průkazu je 123456789.", 1, ((28, 37),)),
        # Wrong length -> no match
        ("12345678", 0, ()),
        ("1234567890", 0, ()),
        # All-zero -> dropped by validation
        ("000000000", 0, ()),
        # Part of a bank account or letter-prefixed identifier -> no match
        ("19-123456789", 0, ()),
        ("123456789/0800", 0, ()),
        ("CZ123456789", 0, ()),
        # Decimal fraction -> no match
        ("3.123456789", 0, ()),
        # fmt: on
    ],
)
def test_when_all_cz_id_cards_then_succeed(
    text, expected_len, expected_positions, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, _PATTERN_SCORE)


@pytest.mark.parametrize(
    "number, expected",
    [
        ("123456789", None),
        ("987654321", None),
        ("000000000", False),
        ("12345678", False),
        ("1234567890", False),
        ("12345678A", False),
    ],
)
def test_when_cz_id_card_validated_then_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected
