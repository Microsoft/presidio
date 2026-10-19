import pytest

from presidio_analyzer.predefined_recognizers import BrCnpjRecognizer
from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return BrCnpjRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["BR_CNPJ"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # official Receita Federal example, alphanumeric (July 2026 format)
        ("12.ABC.345/01DE-35", 1, ((0, 18),), ((1.0, "max"),)),
        # same, compact and lowercase
        ("12abc34501de35", 1, ((0, 14),), ((1.0, "max"),)),
        # numeric CNPJ, formatted and compact
        ("11.222.333/0001-81", 1, ((0, 18),), ((1.0, "max"),)),
        ("11222333000181", 1, ((0, 14),), ((1.0, "max"),)),
        # inside a sentence
        ("Empresa CNPJ 11.222.333/0001-81 ltda", 1, ((13, 31),), ((1.0, "max"),)),
        # wrong check digits
        ("12.ABC.345/01DE-36", 0, (), ()),
        ("11.222.333/0001-80", 0, (), ()),
        # check digit can never be a letter
        ("12ABC34501DE3A", 0, (), ()),
        # repeated digits
        ("00.000.000/0000-00", 0, (), ()),
        # fmt: on
    ],
)
def test_when_cnpj_in_text_then_expected_results(
    text, expected_len, expected_positions, expected_score_ranges, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(results, expected_positions, expected_score_ranges):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(res, entities[0], st_pos, fn_pos, st_score, fn_score)


def test_country_code(recognizer):
    assert recognizer.COUNTRY_CODE == "br"
    assert recognizer.supported_language == "pt"


@pytest.mark.parametrize(
    "value",
    [
        # fmt: off
        "123",                # too short
        "112223330001811",    # too long
        "11222333000 1AB",    # check digits are not numeric
        "12@BC34501DE35",     # character outside 0-9 and A-Z
        # fmt: on
    ],
)
def test_when_value_is_malformed_then_validation_fails(value, recognizer):
    # validate_result is public API, so it is called directly with input the
    # regex would never produce
    assert recognizer.validate_result(value) is False
