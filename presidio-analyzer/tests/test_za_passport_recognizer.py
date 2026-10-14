import pytest

from presidio_analyzer.predefined_recognizers import ZaPassportRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaPassportRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_PASSPORT"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("A34855903", 1, ((0, 9),)),
        ("D12345678", 1, ((0, 9),)),
        ("M87654321", 1, ((0, 9),)),
        ("T11223344", 1, ((0, 9),)),
        ("Passport number A19299317 on file.", 1, ((16, 25),)),
        ("DHA travel document T99887766", 1, ((20, 29),)),
        ("B12345678", 0, ()),
        ("A1234567", 0, ()),
        ("A123456789", 0, ()),
        ("X12345678", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_passports(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "passport_number, expected",
    [
        ("A34855903", True),
        ("D12345678", True),
        ("M87654321", True),
        ("T11223344", True),
        ("B12345678", False),
        ("A1234567", False),
        ("A123456789", False),
        ("X12345678", False),
    ],
)
def test_validate_result(passport_number, expected, recognizer):
    assert recognizer.validate_result(passport_number) is expected
