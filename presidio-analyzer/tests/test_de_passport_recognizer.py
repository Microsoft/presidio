"""
Tests for DePassportRecognizer (Reisepassnummer).

German passport numbers follow ICAO Doc 9303: 9 characters from the
restricted uppercase charset (excludes A, B, D, E, I, O, Q, S, U) and
digits, as printed on the data page. The ICAO check digit (weights 7,3,1;
letters A=10…Z=35; sum mod 10) is not part of the printed number: it
follows the number in the MRZ, e.g. the specimen passport reads
C01X00T478D<<...

Legal basis: Passgesetz (PassG) § 4, Passverordnung (PassV).

Scoring contract (see DePassportRecognizer.PATTERNS):
  number + valid MRZ check digit → validate_result True → MAX_SCORE (1.0)
  printed number (no check digit) → validate_result None → pattern score 0.4
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import DePassportRecognizer

_PATTERN_SCORE = 0.4  # printed number, validate_result=None


@pytest.fixture(scope="module")
def recognizer():
    return DePassportRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DE_PASSPORT"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, validated",
    [
        # fmt: off
        # Printed number (specimen C01X00T47) → pattern score
        ("C01X00T47", 1, ((0, 9),), False),
        ("F12345671", 1, ((0, 9),), False),
        ("Reisepass C01234565 ausgestellt am 01.01.2020.", 1, ((10, 19),), False),
        ("Pass-Nr.: F12345671", 1, ((10, 19),), False),
        ("c01234565", 1, ((0, 9),), False),
        # Number + MRZ check digit → validated
        ("C01X00T478", 1, ((0, 10),), True),
        ("F123456712", 1, ((0, 10),), True),
        # MRZ line 2: nationality D follows the check digit
        ("C01X00T478D<<6408125F2702283<<<<<<<<<<<<<<<4", 1, ((0, 10),), True),
        # Number followed by a wrong MRZ check digit — dropped
        ("C01X00T470", 0, (), False),
        ("F123456719", 0, (), False),
        # Too short (8 chars) / too long (11 chars)
        ("C0123456",  0, (), False),
        ("C0123456789", 0, (), False),
        # Digits only → no match (first char must be letter)
        ("901234567", 0, (), False),
        # fmt: on
    ],
)
def test_when_all_de_passports_then_succeed(
    text, expected_len, expected_positions, validated, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        expected_score = max_score if validated else _PATTERN_SCORE
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


@pytest.mark.parametrize(
    "number, expected",
    [
        # Printed number: no check digit to verify
        ("C01X00T47", None),
        ("C01X00T41", None),
        ("c01234565", None),
        # Number + valid MRZ check digit
        ("C01X00T478", True),
        ("F123456712", True),
        ("C012345650", True),
        # Lowercase — upper() path
        ("c01x00t478", True),
        # Number + wrong MRZ check digit
        ("C01X00T470", False),
        ("C012345651", False),
        # Wrong length
        ("C0123456", False),
        ("C0123456789", False),
        # MRZ check digit must be a digit
        ("C01X00T47A", False),
        # ICAO-forbidden letters must never be accepted
        ("A01234567", False),
        ("IOQSUBDE15", False),
    ],
)
def test_when_de_passport_validated_then_checksum_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected
