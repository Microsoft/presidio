import pytest
from presidio_analyzer.predefined_recognizers import PhPassportRecognizer

from tests.assertions import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a PhPassportRecognizer instance."""
    return PhPassportRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the list of entities to detect."""
    return ["PH_PASSPORT"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid: 1 letter + 7 digits + 1 letter
        ("P1234567A", 1, ((0, 9),), ((0.1, 0.1),)),
        ("Z0000000Z", 1, ((0, 9),), ((0.1, 0.1),)),
        # Valid: 2 letters + 7 digits
        ("EB1234567", 1, ((0, 9),), ((0.1, 0.1),)),
        ("AA0000000", 1, ((0, 9),), ((0.1, 0.1),)),
        # Lowercase should still match (PatternRecognizer uses re.IGNORECASE)
        ("p1234567a", 1, ((0, 9),), ((0.1, 0.1),)),
        ("eb1234567", 1, ((0, 9),), ((0.1, 0.1),)),
        # Embedded in text
        ("My Philippine passport number is P1234567A.", 1, ((33, 42),), ((0.1, 0.1),)),
        ("Passport: EB1234567 is valid.", 1, ((10, 19),), ((0.1, 0.1),)),
        # Multiple matches
        ("P1234567A and EB1234567", 2, ((0, 9), (14, 23)), ((0.1, 0.1), (0.1, 0.1))),
        # Invalid formats
        ("P123456A", 0, (), ()),  # too short
        ("P12345678A", 0, (), ()),  # too long
        ("E1234567", 0, (), ()),  # 1 letter + 7 digits (missing trailing letter)
        ("EB12345678", 0, (), ()),  # 2 letters + 8 digits
        ("EB 1234567", 0, (), ()),  # spaces not supported
        ("P1234567 A", 0, (), ()),  # spaces not supported
        ("1234567A", 0, (), ()),  # missing prefix letter(s)
        ("", 0, (), ()),  # empty string
        # fmt: on
    ],
)
def test_when_passport_in_text_then_all_ph_passports_found(  # noqa: D103
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
