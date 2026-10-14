import pytest

from presidio_analyzer.predefined_recognizers import UkNinoRecognizer
from tests.assertions import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return UkNinoRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["UK_NINO"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid National Insurance Numbers
        ("AA 12 34 56 B", 1, ((0, 13),), ((0.5, 0.5),), ),
        ("hh 01 02 03 d", 1, ((0, 13),), ((0.5, 0.5),), ),
        ("tw987654a", 1, ((0, 9),), ((0.5, 0.5),), ),
        ("nino: PR 123612C", 1, ((6, 16),), ((0.5, 0.5),), ),
        ("Here is my National Insurance Number YZ 61 48 68 B", 1, ((37, 50),), ((0.5, 0.5),), ),
        # The span starts at the NINO, never at a preceding space.
        ("my AB123456C", 1, ((3, 12),), ((0.5, 0.5),), ),
        ("contact AB 12 34 56 C now", 1, ((8, 21),), ((0.5, 0.5),), ),
        # Invalid National Insurance Numbers
        ("AA 12 34 56 H", 0, (), (), ),
        # The suffix must be a letter A-D; a numeric suffix is never valid.
        ("AB 12 34 56 1", 0, (), (), ),
        ("ab1234561", 0, (), (), ),
        ("FQ 00 00 00 C", 0, (), (), ),
        ("BG123612A", 0, (), (), ),
        # Excluded prefixes must stay excluded when the NINO follows a word.
        ("my BG123612A", 0, (), (), ),
        ("nino BG 12 36 12 A", 0, (), (), ),
        ("nino: nt 99 88 77 a", 0, (), (), ),
        ("This isn't a valid national insurance number UV 98 76 54 B", 0, (), (), ),
        # fmt: on
    ]
)
def test_when_nino_in_text_then_all_uk_ninos_found(
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
