import pytest

from tests import assert_result
from presidio_analyzer.predefined_recognizers import CreditCardRecognizer

# https://www.datatrans.ch/showcase/test-cc-numbers
# https://www.freeformatter.com/credit-card-number-generator-validator.html


@pytest.fixture(scope="module")
def cc_recognizer():
    return CreditCardRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CREDIT_CARD"]


@pytest.mark.parametrize(
    "text, expected_len, expected_scores, expected_res",
    [
        # fmt: off
        (
            "4012888888881881 4012-8888-8888-1881 4012 8888 8888 1881",
            3, (), ((0, 16), (17, 36), (37, 56),),
        ),
        ("1748503543012", 0, (), (),),
        ("122000000000003", 1, (), ((0, 15),),),
        ("my credit card: 122000000000003", 1, (), ((16, 31),),),
        ("371449635398431", 1, (), ((0, 15),),),
        ("5555555555554444", 1, (), ((0, 16),),),
        ("5019717010103742", 1, (), ((0, 16),),),
        ("30569309025904", 1, (), ((0, 14),),),
        ("6011000400000000", 1, (), ((0, 16),),),
        ("3528000700000000", 1, (), ((0, 16),),),
        ("6759649826438453", 1, (), ((0, 16),),),
        ("5555555555554444", 1, (), ((0, 16),),),
        ("4111111111111111", 1, (), ((0, 16),),),
        ("4917300800000000", 1, (), ((0, 16),),),
        ("4484070000000000", 1, (1.0,), ((0, 16),),),
        # Mastercard 2-series (BINs 2221-2720, live since 2017).
        ("2221000000000009", 1, (1.0,), ((0, 16),),),
        ("2720990000000007", 1, (1.0,), ((0, 16),),),
        ("2223000048400011", 1, (1.0,), ((0, 16),),),
        ("my credit card: 2221000000000009", 1, (), ((16, 32),),),
        # 18-19 digit PANs (ISO/IEC 7812, e.g. UnionPay/Maestro).
        ("4109906958483040118", 1, (1.0,), ((0, 19),),),
        ("6298036494205552661", 1, (1.0,), ((0, 19),),),
        ("675919345145061238", 1, (1.0,), ((0, 18),),),
        # Luhn-invalid 2-series PAN is still rejected.
        ("2221000000000001", 0, (), (),),
        ("4012-8888-8888-1882", 0, (), (),),
        ("my credit card number is 4012-8888-8888-1882", 0, (), (),),
        ("36168002586008", 0, (), (),),
        ("my credit card number is 36168002586008", 0, (), (),),
        # fmt: on
    ],
)
def test_when_all_credit_cards_then_succeed(
    text,
    expected_len,
    expected_scores,
    expected_res,
    cc_recognizer,
    entities,
    max_score,
):
    results = cc_recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, expected_score in zip(results, expected_scores):
        assert res.score == expected_score
    for res, (start, end) in zip(results, expected_res):
        assert_result(res, entities[0], start, end, max_score)
