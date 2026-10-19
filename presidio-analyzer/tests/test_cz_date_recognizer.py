"""
Tests for CzDateRecognizer (Czech date notation, DATE_TIME entity).

Covers numeric day-first dates with ordinal dots ("12. 4. 1985",
"12.4.1985") and dates with Czech month names in genitive or nominative
form ("12. dubna 1985"). Emits the standard DATE_TIME entity.
"""
import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CzDateRecognizer

# Pattern scores from CzDateRecognizer.PATTERNS.
_FULL_DATE_SCORE = 0.6
_NO_YEAR_SCORE = 0.2


@pytest.fixture(scope="module")
def recognizer():
    return CzDateRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DATE_TIME"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # Textual month (genitive, as used in running text)
        ("12. dubna 1985", 1, ((0, 14),), _FULL_DATE_SCORE),
        ("Narodil se 1. ledna 2000.", 1, ((11, 24),), _FULL_DATE_SCORE),
        ("5. července 2020", 1, ((0, 16),), _FULL_DATE_SCORE),
        ("15. září 2021", 1, ((0, 13),), _FULL_DATE_SCORE),
        ("31. prosince 1999", 1, ((0, 17),), _FULL_DATE_SCORE),
        # Numeric day-first with ordinal dots
        ("12. 4. 1985", 1, ((0, 11),), _FULL_DATE_SCORE),
        ("12.4.1985", 1, ((0, 9),), _FULL_DATE_SCORE),
        ("3. 12. 2023", 1, ((0, 11),), _FULL_DATE_SCORE),
        # Day + month without a year (weak evidence)
        ("12. dubna", 1, ((0, 9),), _NO_YEAR_SCORE),
        # Impossible day or month -> no match
        ("32. dubna 1985", 0, (), None),
        ("12. 13. 1985", 0, (), None),
        # English/ISO formats are left to the generic DateRecognizer
        ("2023-04-12", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_cz_dates_then_succeed(
    text, expected_len, expected_positions, expected_score,
    recognizer, entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)
