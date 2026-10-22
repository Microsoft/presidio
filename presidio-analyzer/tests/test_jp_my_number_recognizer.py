# ruff: noqa: D103,E501
import pytest
from presidio_analyzer.predefined_recognizers.country_specific.japan import (
    JpMyNumberRecognizer,
)

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return JpMyNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["JP_MY_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid My Numbers (Checksum pass) ---
        ("123456789018", 1, ((0, 12),), ((1.0, 1.0),), ),
        ("1234-5678-9018", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("1234 5678 9018", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("マイナンバーは 1234-5678-9018 です。", 1, ((8, 22),), ((1.0, 1.0),), ),
        ("個人番号 123456789018", 1, ((5, 17),), ((1.0, 1.0),), ),

        # Invalid My Numbers (Checksum fail or Invalid format) ---
        # Correct format but wrong checksum
        ("123456789019", 0, (), (), ),
        ("1234-5678-9019", 0, (), (), ),
        # Too short
        ("1234-5678-901", 0, (), (), ),
        ("12345678901", 0, (), (), ),
        # Too long
        ("1234567890188", 0, (), (), ),
        ("1234-5678-90188", 0, (), (), ),
        # Contains non-digit
        ("1234-5678-901A", 0, (), (), ),
        # Random non-number
        ("abcdefghijkl", 0, (), (), ),
        # fmt: on
    ],
)
def test_when_all_my_numbers_then_succeed(
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
