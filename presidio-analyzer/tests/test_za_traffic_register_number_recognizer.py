import pytest

from presidio_analyzer.predefined_recognizers import ZaTrafficRegisterNumberRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaTrafficRegisterNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_TRAFFIC_REGISTER_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        (
            "Traffic register number 1234567890123 is on file.",
            1,
            ((24, 37),),
        ),
        (
            "eNaTIS TRN 6001015000076 recorded.",
            1,
            ((11, 24),),
        ),
        ("8001015009087", 0, ()),
        ("123456789012", 0, ()),
        ("12345678901234", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_traffic_register_numbers(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "trn, expected",
    [
        ("1234567890123", True),
        ("6001015000076", True),
        ("8001015009087", False),
        ("123456789012", False),
        ("12345678901234", False),
    ],
)
def test_validate_result(trn, expected, recognizer):
    assert recognizer.validate_result(trn) is expected
