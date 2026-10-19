import pytest

from presidio_analyzer.predefined_recognizers import BrCpfRecognizer
from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return BrCpfRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["BR_CPF"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # valid, formatted
        ("529.982.247-25", 1, ((0, 14),), ((1.0, "max"),)),
        # valid, digits only
        ("52998224725", 1, ((0, 11),), ((1.0, "max"),)),
        # valid, inside a sentence
        ("O titular, CPF 168.995.350-09, assina.", 1, ((15, 29),), ((1.0, "max"),)),
        # valid, spaces instead of dots
        ("529 982 247 25", 1, ((0, 14),), ((1.0, "max"),)),
        # wrong check digit
        ("529.982.247-24", 0, (), ()),
        # repeated digits pass the formula but are never issued
        ("111.111.111-11", 0, (), ()),
        # too short / too long
        ("529.982.247-2", 0, (), ()),
        ("529982247255", 0, (), ()),
        # fmt: on
    ],
)
def test_when_cpf_in_text_then_expected_results(
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
