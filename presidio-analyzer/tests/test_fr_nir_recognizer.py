import pytest
from presidio_analyzer.predefined_recognizers import FrNirRecognizer

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Return an instance of the FrNirRecognizer."""
    return FrNirRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return entities to analyze."""
    return ["FR_NIR"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Valid NIRs — checksum = 97 - (first_13_digits % 97). See
        # https://www.insee.fr/fr/metadonnees/definition/c1409
        # Compact, no separators
        ("291059933807692", 1, ((0, 15),),),
        # Space delimited
        ("1 85 05 78 120 123 27", 1, ((0, 21),),),
        # Dot delimited
        ("2.96.01.12.345.678.59", 1, ((0, 21),),),
        # With context
        ("mon numéro de sécurité sociale est 2 91 05 99 338 076 92", 1, ((35, 56),),),
        # Corsican department code (2A -> 19 for checksum purposes)
        ("185032A03411208", 1, ((0, 15),),),

        # --- Invalid: checksum failure ---
        ("291059933807693", 0, (),),
        ("185032A03411209", 0, (),),

        # --- Invalid: regex rejects illegal month encoding (13-19) ---
        ("291139933807692", 0, (),),

        # --- Invalid: wrong length ---
        ("29105993380769", 0, (),),
        ("2910599338076920", 0, (),),

        # --- Invalid: hyphen-separated groups are not a supported NIR format ---
        ("2-91-05-99-338-076-92", 0, (),),
        # fmt: on
    ],
)
def test_when_nir_in_text_then_all_fr_nirs_are_found(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    """Test that valid NIRs are found where expected and invalid ones are not."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "nir, expected",
    [
        # Valid, checksum-correct NIRs
        ("291059933807692", True),
        ("1850578120123 27".replace(" ", ""), True),
        ("185032A03411208", True),
        # Wrong check digits
        ("291059933807693", False),
        ("185032A03411209", False),
        # Wrong length
        ("29105993380769", False),
        ("2910599338076920", False),
        # Non-digit noise beyond the supported letter-department codes
        ("29105993380769X", False),
    ],
)
def test_validate_result_checksum(nir, expected, recognizer):
    """Test the INSEE checksum validation on well-formed and malformed NIRs."""
    assert recognizer.validate_result(nir) is expected
