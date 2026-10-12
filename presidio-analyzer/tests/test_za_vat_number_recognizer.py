import pytest

from presidio_analyzer.predefined_recognizers import ZaVatNumberRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaVatNumberRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_VAT_NUMBER"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("4020269678", 1, ((0, 10),)),
        ("4170229407", 1, ((0, 10),)),
        ("VAT number 4250281542 on invoice.", 1, ((11, 21),)),
        ("SARS vat registration 4100168758", 1, ((22, 32),)),
        ("3020269678", 0, ()),
        ("402026967", 0, ()),
        ("40202696789", 0, ()),
        ("1234567890", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_vat_numbers(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "vat_number, expected",
    [
        ("4020269678", True),
        ("4170229407", True),
        ("3020269678", False),
        ("402026967", False),
        ("40202696789", False),
    ],
)
def test_validate_result(vat_number, expected, recognizer):
    assert recognizer.validate_result(vat_number) is expected
