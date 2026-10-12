import pytest

from presidio_analyzer.predefined_recognizers import ZaIncomeTaxNumberRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaIncomeTaxNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_INCOME_TAX_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("0123456789", 1, ((0, 10),)),
        ("1234567890", 1, ((0, 10),)),
        ("9123456789", 1, ((0, 10),)),
        ("SARS tax reference 2987654321 on file.", 1, ((19, 29),)),
        ("4020269678", 0, ()),
        ("5123456789", 0, ()),
        ("012345678", 0, ()),
        ("01234567890", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_income_tax_numbers(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "tax_number, expected",
    [
        ("0123456789", True),
        ("1234567890", True),
        ("9123456789", True),
        ("4020269678", False),
        ("5123456789", False),
        ("012345678", False),
    ],
)
def test_validate_result(tax_number, expected, recognizer):
    assert recognizer.validate_result(tax_number) is expected
