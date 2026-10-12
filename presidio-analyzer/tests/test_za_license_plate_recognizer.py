import pytest

from presidio_analyzer.predefined_recognizers import ZaLicensePlateRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaLicensePlateRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_LICENSE_PLATE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("KD93GKGP", 1, ((0, 8),)),
        ("PMG017GP", 1, ((0, 8),)),
        ("BJ47HRZN", 1, ((0, 8),)),
        ("DK 28 LF GP", 1, ((0, 11),)),
        ("CC 75 CX ZN", 1, ((0, 11),)),
        ("GET 103 WP", 1, ((0, 10),)),
        ("015 SBZ EC", 1, ((0, 10),)),
        ("Licence plate MT77GJGP registered.", 1, ((14, 22),)),
        ("YES", 0, ()),
        ("1234567890", 0, ()),
        ("hello world", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_license_plates(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "plate, expected",
    [
        ("KD93GKGP", True),
        ("DK28LFGP", True),
        ("CC75CXZN", True),
        ("GET103WP", True),
        ("015SBZEC", True),
        ("YES", False),
        ("1234GP", False),
    ],
)
def test_validate_result(plate, expected, recognizer):
    assert recognizer.validate_result(plate) is expected
