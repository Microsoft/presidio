import pytest

from presidio_analyzer.predefined_recognizers.country_specific.tw import (
    TwNationalIdRecognizer,
)


@pytest.fixture(scope="module")
def recognizer():
    return TwNationalIdRecognizer()


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # Valid Taiwan IDs (Verified with Modulus-10 checksum)
        ("My ID is A123456789.", 1, ((9, 19),)),
        ("B120000008", 1, ((0, 10),)),
        ("F120000002", 1, ((0, 10),)),
        ("H120000004", 1, ((0, 10),)),
        # Adjacent to Chinese characters
        ("身分證A123456789", 1, ((3, 13),)),
        # Invalid Formats / Non-Matches / Checksum Failures
        ("A323456789", 0, ()),  # Invalid gender code (3)
        ("A12345678", 0, ()),  # Too short
        ("A1234567890", 0, ()),  # Too long
        ("1123456789", 0, ()),  # Missing letter
        ("a123456789", 0, ()),  # Lowercase prefix rejected
        ("A123456780", 0, ()),  # Checksum failure
    ],
)
def test_tw_national_id_recognizer(
    text, expected_len, expected_positions, recognizer
):
    results = recognizer.analyze(text, entities=["TW_NATIONAL_ID"])
    assert len(results) == expected_len
    if expected_len > 0:
        assert (results[0].start, results[0].end) == expected_positions[0]
