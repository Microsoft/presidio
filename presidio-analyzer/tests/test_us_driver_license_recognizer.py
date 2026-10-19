import pytest

from presidio_analyzer.predefined_recognizers import UsLicenseRecognizer
from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return UsLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_DRIVER_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        ("H12234567", 1, ((0, 9),), ((0.3, 0.4),),),
        ("C12T345672", 0, (), (),),
        # invalid license that should fail, but doesn't do to context
        # ("my driver's license is C12T345672", 0, (), (),),
        # Other states license very weak tests
        (
            "123456789 1234567890 12345679012 123456790123 1234567901234 1234",
            5,
            ((0, 9), (10, 20), (21, 32), (33, 45), (46, 59),),
            ((0.0, 0.02), (0.0, 0.02), (0.0, 0.02), (0.0, 0.02), (0.0, 0.02),),
        ),
        # Two-letter prefix + two digits (previously missed due to malformed regex)
        ("AB12", 1, ((0, 4),), ((0.3, 0.4),),),
        # Malformed literal that the broken regex used to match
        ("A-Z]]12", 0, (), (),),
        ("ABCDEFG ABCDEFGH ABCDEFGHI", 0, (), (),),
        ("ABCD ABCDEFGHIJ", 0, (), (),),
        # The following fails due to keyphrases not yet supported
        # ("my driver license: ABCDEFG", 1, ((19, 25),), ((0.5, 0.91),),),
        # fmt: on
    ],
)
def test_when_driver_licenes_in_text_then_all_us_driver_licenses_found(
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
