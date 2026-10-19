import pytest
from presidio_analyzer.predefined_recognizers import DkCprRecognizer

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the DkCprRecognizer."""
    return DkCprRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["DK_CPR_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # Checksum-valid CPR numbers -> promoted to max score.
        ("0101900002", 1, ((0, 10),), 1.0),
        ("010190-0002", 1, ((0, 11),), 1.0),
        ("Mit cpr-nummer er 010190-0002.", 1, ((18, 29),), 1.0),
        # 29 Feb 1904 is a valid leap day; checksum also valid.
        ("2902040008", 1, ((0, 10),), 1.0),
        # Structurally valid date but checksum fails (post-2007 style):
        # still detected, at the pattern score (0.3 contiguous, 0.5 hyphenated).
        ("0101900000", 1, ((0, 10),), 0.3),
        ("010190-0000", 1, ((0, 11),), 0.5),
        # Hyphenated checksum-fail embedded in a sentence is still detected at
        # the hyphenated pattern score.
        (
            "CPR: 010190-0000 mangler gyldigt kontrolciffer.",
            1,
            ((5, 16),),
            0.5,
        ),
        # Space-separated form (DDMMYY SSSS) is intentionally not supported.
        ("010190 0000", 0, (), None),
        # Invalid month (13), invalid day (32), and 29 Feb on a non-leap year
        # (1903) are rejected regardless of checksum.
        ("011390-0000", 0, (), None),
        ("320190-0000", 0, (), None),
        ("2902030002", 0, (), None),
        # Wrong length and non-digit content do not match / are rejected.
        ("123456-789", 0, (), None),
        ("01019x0002", 0, (), None),
        # A 10-digit run embedded in a longer digit string is not matched
        # (word boundary), avoiding false positives on long numeric IDs.
        ("120000101900021234", 0, (), None),
    ],
)
def test_when_all_dk_cpr_then_succeed(
    text, expected_len, expected_positions, expected_score, recognizer, entities
):
    """Test the recognizer against valid and invalid Danish CPR numbers."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)
