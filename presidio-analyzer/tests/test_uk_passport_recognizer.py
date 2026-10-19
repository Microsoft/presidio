import pytest
from presidio_analyzer.predefined_recognizers import UkPassportRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests.assertions import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a UkPassportRecognizer instance."""
    return UkPassportRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the list of entities to detect."""
    return ["UK_PASSPORT"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid UK passport numbers (9 digits, all numeric)
        (
            "123456789",
            1,
            ((0, 9),),
            ((0.05, 0.05),),
        ),
        (
            "987654321",
            1,
            ((0, 9),),
            ((0.05, 0.05),),
        ),
        # Embedded in text
        (
            "My passport number is 123456789 and it expires soon",
            1,
            ((22, 31),),
            ((0.05, 0.05),),
        ),
        # Multiple passport numbers
        (
            "Passports: 123456789 and 987654321",
            2,
            (
                (11, 20),
                (25, 34),
            ),
            (
                (0.05, 0.05),
                (0.05, 0.05),
            ),
        ),
        # Invalid: old (incorrect) 2-letters + 7-digits format
        (
            "AB1234567",
            0,
            (),
            (),
        ),
        (
            "XY9876543",
            0,
            (),
            (),
        ),
        # Invalid: lowercase old format
        (
            "ab1234567",
            0,
            (),
            (),
        ),
        # Invalid: 1 letter + 8 digits
        (
            "A12345678",
            0,
            (),
            (),
        ),
        # Invalid: 3 letters + 6 digits
        (
            "ABC123456",
            0,
            (),
            (),
        ),
        # Invalid: 3 letters + 7 digits
        (
            "GBR1234567",
            0,
            (),
            (),
        ),
        # Invalid: too short (8 digits)
        (
            "12345678",
            0,
            (),
            (),
        ),
        # Invalid: too long (10 digits)
        (
            "1234567890",
            0,
            (),
            (),
        ),
        # Invalid: space in number
        (
            "AB 1234567",
            0,
            (),
            (),
        ),
        # Invalid: reversed order (digits then letters)
        (
            "1234567AB",
            0,
            (),
            (),
        ),
        # Invalid: embedded in alphanumeric word (no word boundary)
        (
            "XYZ123456789QRS",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_passport_in_text_then_all_uk_passports_found(  # noqa: D103
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


def test_recognizer_loads_and_detects_when_enabled_in_yaml():
    """Detection must work through the path users actually configure."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "UkPassportRecognizer",
                    "supported_languages": ["en"],
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "uk",
                }
            ],
        }
    ).create_recognizer_registry()

    recognizer = registry.get_recognizers(language="en", entities=["UK_PASSPORT"])
    assert len(recognizer) == 1

    results = recognizer[0].analyze("passport 123456789", entities=["UK_PASSPORT"])
    assert len(results) == 1
    assert results[0].entity_type == "UK_PASSPORT"
    assert (results[0].start, results[0].end) == (9, 18)
    assert results[0].score == pytest.approx(0.05)
