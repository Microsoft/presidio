"""
Tests for CzBirthNumberRecognizer (rodné číslo).

All test numbers are fictitious/generated and do not represent real persons.
Valid numbers satisfy the official mod 11 rule of § 13 zákona č. 133/2000 Sb.
(10-digit numbers divisible by 11, or the 1954-1985 historical exception
where the first 9 digits mod 11 equal 10 and the check digit is 0).
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzBirthNumberRecognizer

# Pattern scores from CzBirthNumberRecognizer.PATTERNS. A failed checksum
# returns None from validate_result (see docstring there), so those
# matches keep the base pattern score and context words decide.
_SLASH_SCORE = 0.5
_NO_SLASH_SCORE = 0.3


@pytest.fixture(scope="module")
def recognizer():
    return CzBirthNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CZ_BIRTH_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_fn",
    [
        # fmt: off
        # Valid checksum -> MAX_SCORE
        ("780123/0107", 1, ((0, 11),), lambda max_score: max_score),
        ("855612/0111", 1, ((0, 11),), lambda max_score: max_score),  # female month (+50)
        ("990131/0111", 1, ((0, 11),), lambda max_score: max_score),
        ("Moje rodné číslo je 780123/0107.", 1, ((20, 31),), lambda max_score: max_score),
        # Valid checksum without separator -> MAX_SCORE
        ("RČ 8556120111 bylo ověřeno.", 1, ((3, 13),), lambda max_score: max_score),
        # Historical exception (first 9 digits mod 11 == 10, check digit 0)
        ("780123/1010", 1, ((0, 11),), lambda max_score: max_score),
        # Date part is plausible but the checksum fails -> pattern score
        ("850412/0003", 1, ((0, 11),), lambda max_score: _SLASH_SCORE),
        ("8504120003", 1, ((0, 10),), lambda max_score: _NO_SLASH_SCORE),
        # 9-digit pre-1954 number (no check digit defined) -> pattern score
        ("530101/123", 1, ((0, 10),), lambda max_score: _SLASH_SCORE),
        # Invalid month (13) -> no match
        ("781323/0107", 0, (), None),
        # Invalid day (00) -> no match
        ("780100/0107", 0, (), None),
        # Serial suffix 000 was never assigned -> dropped by validation
        ("780123/000", 0, (), None),
        # Bank account shaped strings must not match (month/day impossible)
        ("19-123456789/0800", 0, (), None),
        # Embedded in a longer digit run -> no match
        ("77805041200031", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_cz_birth_numbers_then_succeed(
    text, expected_len, expected_positions, expected_score_fn,
    recognizer, entities, max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(
            res, entities[0], st_pos, fn_pos, expected_score_fn(max_score)
        )


@pytest.mark.parametrize(
    "number, expected",
    [
        # Valid 10-digit numbers (divisible by 11)
        ("7801230107", True),
        ("780123/0107", True),
        ("8556120111", True),
        # Historical exception (1954-1985)
        ("7801231010", True),
        # Plausible but failing checksum -> None (context decides)
        ("8504120003", None),
        ("850412/0003", None),
        # 9-digit pre-1954 numbers carry no check digit -> None
        ("530101123", None),
        # Serial suffix 000 -> False
        ("780123000", False),
        ("780123/000", False),
        # Wrong length / non-numeric -> False
        ("78012301", False),
        ("78012301070", False),
        ("78O123O107", False),
    ],
)
def test_when_cz_birth_number_validated_then_checksum_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected
