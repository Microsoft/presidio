# ruff: noqa: D103,E501
import pytest
from presidio_analyzer.predefined_recognizers.country_specific.japan import (
    JpCorporateNumberRecognizer,
)

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return JpCorporateNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["JP_CORPORATE_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid Corporate Numbers (Checksum pass) ---
        ("1130001011420", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("1-1300-0101-1420", 1, ((0, 16),), ((1.0, 1.0),), ),
        ("1 1300 0101 1420", 1, ((0, 16),), ((1.0, 1.0),), ),
        ("5010401067252", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("1180301018771", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("法人番号: 1-1300-0101-1420", 1, ((6, 22),), ((1.0, 1.0),), ),
        ("Company corporate number is 5010401067252", 1, ((28, 41),), ((1.0, 1.0),), ),

        # Invalid Corporate Numbers (Checksum fail or Invalid format) ---
        # Correct format but wrong checksum
        ("2130001011420", 0, (), (), ),
        ("2-1300-0101-1420", 0, (), (), ),
        # Too short
        ("113000101142", 0, (), (), ),
        ("1-1300-0101-142", 0, (), (), ),
        # Too long
        ("11300010114200", 0, (), (), ),
        ("1-1300-0101-14200", 0, (), (), ),
        # Contains non-digit
        ("1-1300-0101-142A", 0, (), (), ),
        # Random string
        ("abcdefghijklm", 0, (), (), ),
        # fmt: on
    ],
)
def test_when_all_corporate_numbers_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
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
