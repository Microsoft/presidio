import pytest

from presidio_analyzer.predefined_recognizers import ZaDriverLicenseRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaDriverLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_DRIVER_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("60390002CGBV", 1, ((0, 12),)),
        ("4024048D4P60", 1, ((0, 12),)),
        ("30040008X6Z6", 1, ((0, 12),)),
        ("4046048YPC9T", 1, ((0, 12),)),
        ("Driving licence number 114500482HFF on file.", 1, ((23, 35),)),
        ("eNaTIS licence 40260039Y068", 1, ((15, 27),)),
        ("8001015009087", 0, ()),
        ("60390002", 0, ()),
        ("ABCDEFGHIJK", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_drivers_licences(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "licence_number, expected",
    [
        ("60390002CGBV", True),
        ("4024048D4P60", True),
        ("30040008X6Z6", True),
        ("8001015009087", False),
        ("60390002", False),
        ("ABCDEFGHIJK", False),
        ("ABC1234567890", False),
    ],
)
def test_validate_result(licence_number, expected, recognizer):
    assert recognizer.validate_result(licence_number) is expected
