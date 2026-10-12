import pytest

from presidio_analyzer.predefined_recognizers import CaPostalCodeRecognizer
from tests.assertions import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return CaPostalCodeRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["CA_POSTAL_CODE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid, with space (strict pattern, higher score)
        ("K1A 0A1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Valid, no space (weak pattern, lower score)
        ("K1A0A1", 1, ((0, 6),), ((0.1, 0.1),),),
        # Valid, lowercase, with space
        ("k1a 0a1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Valid, mixed case, with space
        ("K1a 0A1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Valid, leading zero digit (rural FSA), with space
        ("K0A 0A1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Valid: W in third-letter position (LDU, not first letter), with space
        ("K1A 1W1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Valid: Z in third-letter position (LDU, not first letter), with space
        ("K1A 1Z1", 1, ((0, 7),), ((0.3, 0.3),),),
        # Embedded in text, with space
        ("My postal code is K1A 0A1 thanks", 1, ((18, 25),), ((0.3, 0.3),),),
        # Multiple postal codes, with space
        ("From K1A 0A1 to M5V 3A8", 2, ((5, 12), (16, 23)), ((0.3, 0.3), (0.3, 0.3)),),  # noqa: E501
        # Invalid: D as first letter
        ("D1A 1A1", 0, (), (),),
        # Invalid: F as first letter
        ("F1A 1A1", 0, (), (),),
        # Invalid: I as first letter
        ("I1A 1A1", 0, (), (),),
        # Invalid: O as first letter
        ("O1A 1A1", 0, (), (),),
        # Invalid: Q as first letter
        ("Q1A 1A1", 0, (), (),),
        # Invalid: U as first letter
        ("U1A 1A1", 0, (), (),),
        # Invalid: W as first letter (valid elsewhere)
        ("W1A 1A1", 0, (), (),),
        # Invalid: Z as first letter (valid elsewhere)
        ("Z1A 1A1", 0, (), (),),
        # Invalid: D in FSA third-letter position
        ("K1D 1A1", 0, (), (),),
        # Invalid: D in LDU letter position
        ("K1A 1D1", 0, (), (),),
        # Invalid: starts with digit
        ("1A1 1A1", 0, (), (),),
        # No match across a newline
        ("K1A\n0A1", 0, (), (),),
        # No partial match embedded in a larger alphanumeric token
        ("XK1A0A1Y", 0, (), (),),
        # No match, empty string
        ("", 0, (), (),),
        # Two-space gap does not match either pattern (not a valid postal code)
        ("K1A  0A1", 0, (), (),),
        # fmt: on
    ],
)
def test_when_postal_code_in_text_then_all_ca_postal_codes_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len

    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )
