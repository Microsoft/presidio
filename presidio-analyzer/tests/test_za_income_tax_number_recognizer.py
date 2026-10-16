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
        ("0123456782", 1, ((0, 10),)),
        ("1234567897", 1, ((0, 10),)),
        ("9123456783", 1, ((0, 10),)),
        # Example from the SARS TIN description published by the OECD
        ("0001339050", 1, ((0, 10),)),
        ("SARS tax reference 2987654320 on file.", 1, ((19, 29),)),
        # Wrong check digit, e.g. a phone number
        ("0123456789", 0, ()),
        ("Call me on 0821234567.", 0, ()),
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
        ("0123456782", True),
        ("1234567897", True),
        ("9123456783", True),
        ("0001339050", True),
        ("0123456789", False),
        ("0821234567", False),
        ("4020269678", False),
        ("5123456789", False),
        ("012345678", False),
    ],
)
def test_validate_result(tax_number, expected, recognizer):
    assert recognizer.validate_result(tax_number) is expected
