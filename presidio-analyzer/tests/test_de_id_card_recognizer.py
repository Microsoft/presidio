"""
Tests for DeIdCardRecognizer (Personalausweisnummer).

Covers two formats:
  - nPA (since Nov 2010): 9 chars from the ICAO charset, as printed on the
    card. The ICAO Doc 9303 check digit (weights 7,3,1; letters A=10…Z=35;
    sum mod 10) is not part of the printed number: it follows the number in
    the MRZ, e.g. the specimen card reads IDD<<L01X00T471.
  - Legacy (pre-Nov 2010): T + 8 digits, no check digit.

Scoring contract (see DeIdCardRecognizer.PATTERNS):
  nPA number + valid MRZ check digit → validate_result True → MAX_SCORE (1.0)
  printed nPA number (no check digit) → validate_result None → pattern score 0.4
  Legacy T+8d                          → validate_result None → pattern score 0.5
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import DeIdCardRecognizer

# Pattern scores as declared in DeIdCardRecognizer.PATTERNS.
_NPA_VALIDATED_SCORE = 1.0  # MAX_SCORE via validate_result=True
_NPA_PATTERN_SCORE = 0.4  # printed number, validate_result=None
_LEGACY_PATTERN_SCORE = 0.5  # "T + 8 Ziffern" pattern, validate_result=None


@pytest.fixture(scope="module")
def recognizer():
    return DeIdCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DE_ID_CARD"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # --- Printed nPA number (specimen L01X00T47) → pattern score ---
        ("L01X00T47", 1, ((0, 9),),  _NPA_PATTERN_SCORE),
        ("C01234565", 1, ((0, 9),),  _NPA_PATTERN_SCORE),
        ("Personalausweis: L01X00T47.", 1, ((17, 26),), _NPA_PATTERN_SCORE),
        ("l01x00t47",  1, ((0, 9),),  _NPA_PATTERN_SCORE),
        # --- Number + MRZ check digit → MAX_SCORE ---
        ("L01X00T471", 1, ((0, 10),), _NPA_VALIDATED_SCORE),
        ("CZ6311T036", 1, ((0, 10),), _NPA_VALIDATED_SCORE),
        ("G000000024", 1, ((0, 10),), _NPA_VALIDATED_SCORE),
        # Specimen MRZ line 1
        ("IDD<<L01X00T471<<<<<<<<<<<<<<<", 1, ((5, 15),), _NPA_VALIDATED_SCORE),
        # --- Legacy T-format → pattern score, no ICAO check ---
        ("T22000129", 1, ((0, 9),),  _LEGACY_PATTERN_SCORE),
        ("T00000000", 1, ((0, 9),),  _LEGACY_PATTERN_SCORE),
        ("T99999999", 1, ((0, 9),),  _LEGACY_PATTERN_SCORE),
        ("Ausweis Nr. T22000129 gültig bis 2025.",
                     1, ((12, 21),), _LEGACY_PATTERN_SCORE),
        ("t22000129", 1, ((0, 9),),  _LEGACY_PATTERN_SCORE),
        # --- Dropped matches (expected_score irrelevant) ---
        # Number followed by a wrong MRZ check digit
        ("L01X00T470", 0, (), None),
        ("IDD<<L01X00T479<<<<<<<<<<<<<<<", 0, (), None),
        # Too short / too long
        ("T2200012",  0, (), None),
        ("L01X00T4712", 0, (), None),
        # All digits in 9-char form → no first-letter match
        ("123456789", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_de_id_cards_then_succeed(
    text, expected_len, expected_positions, expected_score,
    recognizer, entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


@pytest.mark.parametrize(
    "number, expected",
    [
        # Printed number: no check digit to verify
        ("L01X00T47", None),
        ("L01X00T44", None),
        # Number + valid MRZ check digit
        ("L01X00T471", True),
        ("C012345650", True),
        ("CZ6311T036", True),
        ("G000000024", True),
        # Lowercase — upper() path
        ("l01x00t471", True),
        # Number + wrong MRZ check digit
        ("L01X00T470", False),
        ("C012345651", False),
        # Legacy T + 8 digits → None (accepted at pattern score only)
        ("T22000129", None),
        ("T00000000", None),
        # Wrong length
        ("L01X00T4",  False),
        ("L01X00T4712", False),
        # MRZ check digit must be a digit
        ("L01X00T47A", False),
    ],
)
def test_when_de_id_card_validated_then_checksum_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected
