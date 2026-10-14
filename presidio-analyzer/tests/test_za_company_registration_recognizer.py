import pytest

from presidio_analyzer.predefined_recognizers import ZaCompanyRegistrationRecognizer
from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    return ZaCompanyRegistrationRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["ZA_COMPANY_REGISTRATION"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        ("2009/199240/23", 1, ((0, 14),)),
        ("2014/256030/07", 1, ((0, 14),)),
        ("CIPC registration 2020/804826/07", 1, ((18, 32),)),
        ("CK2001/123456", 1, ((0, 13),)),
        ("Close corporation CK1998/654321 registered.", 1, ((18, 31),)),
        ("99/199240/23", 0, ()),
        ("2009/19924/23", 0, ()),
        ("2009/199240/234", 0, ()),
        ("hello world", 0, ()),
    ],
)
def test_analyze_valid_and_invalid_za_company_registrations(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "registration_number, expected",
    [
        ("2009/199240/23", True),
        ("2014/256030/07", True),
        ("CK2001/123456", True),
        ("K2010/654321", True),
        ("99/199240/23", False),
        ("2009/19924/23", False),
        ("AB2001/123456", False),
    ],
)
def test_validate_result(registration_number, expected, recognizer):
    assert recognizer.validate_result(registration_number) is expected
