import pytest

from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import UsSsnRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return UsSsnRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_SSN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # very weak match
        ("078-051121 07805-1121", 2, ((0, 10), (11, 21),), ((0.0, 0.3), (0.0, 0.3),),),
        # weak match
        ("078051121", 1, ((0, 9),), ((0.0, 0.4),),),
        # medium match
        ("078-05-1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("078.05.1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("078 05 1123", 1, ((0, 11),), ((0.5, 0.6),),),
        ("abc 078 05 1123 abc", 1, ((4, 15),), ((0.5, 0.6),),),
        # 899 is the upper boundary before the never-issued 900 series
        ("899-12-3456", 1, ((0, 11),), ((0.5, 0.6),),),
        # a normal valid SSN is still detected
        ("219-09-9999", 1, ((0, 11),), ((0.5, 0.6),),),
        # no match
        ("0780511201", 0, (), (),),
        ("078051120", 0, (), (),),
        ("000000000", 0, (), (),),
        ("666000000", 0, (), (),),
        ("078-05-0000", 0, (), (),),
        ("078 00 1123", 0, (), (),),
        ("693-09.4444", 0, (), (),),
        # all 900-series area numbers are never issued by the SSA
        ("90012-3456", 0, (), (),),
        ("900-123456", 0, (), (),),
        ("900123456", 0, (), (),),
        ("900-12-3456", 0, (), (),),
        ("987-65-4320", 0, (), (),),
        ("987-65-4321", 0, (), (),),
        ("999-12-3456", 0, (), (),),
        # canonical sample SSNs stay invalidated via exact match
        ("078-05-1120", 0, (), (),),
        ("123-45-6789", 0, (), (),),
        # never-issued area numbers (000/666) stay invalidated via the area check
        ("000-12-3456", 0, (), (),),
        ("666-12-3456", 0, (), (),),
        # fmt: on
    ],
)
def test_when_snn_in_text_than_all_us_ssns_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
