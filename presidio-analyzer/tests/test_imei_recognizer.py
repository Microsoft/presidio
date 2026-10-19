import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import ImeiRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return ImeiRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["IMEI"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        ("49-015420-323751-8", 1, ((0, 18),), ((0.5, 0.81),)),
        ("49 015420 323751 8", 1, ((0, 18),), ((0.5, 0.81),)),
        ("handset IMEI: 49-015420-323751-8", 1, ((14, 32),), ((0.5, 0.81),)),
        # Bare 15-digit strings are not matched (avoids CREDIT_CARD collisions)
        ("490154203237518", 0, (), ()),
        ("device imei 490154203237518", 0, (), ()),
        # Invalid: checksum failure
        ("490154203237519", 0, (), ()),
        ("49-015420-323751-9", 0, (), ()),
        # AMEX-style 15-digit Luhn number should not be detected as IMEI
        ("378282246310005", 0, (), ()),
        # Invalid: wrong length
        ("49015420323751", 0, (), ()),
        ("4901542032375180", 0, (), ()),
        # Invalid: mismatched delimiters
        ("49-01 5420-323751-8", 0, (), ()),
        # fmt: on
    ],
)
def test_when_imei_in_text_then_detected(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "imei, invalidated",
    [
        ("490154203237518", False),
        ("49-015420-323751-8", False),
        ("490154203237519", True),
        ("123456789012345", True),
    ],
)
def test_invalidate_result(imei, invalidated, recognizer):
    assert recognizer.invalidate_result(imei) is invalidated


def test_invalidate_result_respects_custom_replacement_pairs():
    recognizer = ImeiRecognizer(replacement_pairs=[("-", ""), (".", "")])
    assert recognizer.invalidate_result("49.015420.323751.8") is False
    assert recognizer.invalidate_result("49.015420.323751.9") is True
