"""Tests for Saudi Arabia National ID and Iqama recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, EntityRecognizer
from presidio_analyzer.predefined_recognizers import SaNationalIdRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result

MAX_SCORE = EntityRecognizer.MAX_SCORE


@pytest.fixture(scope="module")
def recognizer():
    """Create a Saudi National ID recognizer instance for testing."""
    return SaNationalIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Saudi National ID entity type for testing."""
    return ["SA_NATIONAL_ID"]


# Valid fixtures are computed with the Luhn checksum, not copied blindly.
# Example, base 110179827: digits in odd positions are doubled and the digits
# of each product summed (2+0+5+7+5), the other digits taken as is
# (1+1+9+2), giving 32, so the check digit is (10 - (32 % 10)) % 10 = 8 and
# 1101798278 is valid. 1101798278 is also the worked example used by the
# luhn-validator and luhncheck packages for Saudi national and resident IDs.
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # Valid citizen IDs (first digit 1, correct checksum)
        ("1101798278", 1, (0, 10), MAX_SCORE),
        ("1047846314", 1, (0, 10), MAX_SCORE),
        # Valid Iqama numbers (first digit 2, correct checksum)
        ("2054789637", 1, (0, 10), MAX_SCORE),
        ("2123456788", 1, (0, 10), MAX_SCORE),
        # Valid IDs in sentences, with context words before the number
        ("Iqama number is 2054789637 for the employee", 1, (16, 26), MAX_SCORE),
        ("The Saudi national id 1047846314 was verified", 1, (22, 32), MAX_SCORE),
        # Multiple valid IDs
        ("IDs: 1047846314 and 2054789637", 2, (5, 15), MAX_SCORE),
        # Invalid IDs: wrong check digit
        ("1101798279", 0, (0, 0), 0),
        ("1047846315", 0, (0, 0), 0),
        ("2054789638", 0, (0, 0), 0),
        # Invalid IDs: leading digit is not 1 or 2
        ("3047846314", 0, (0, 0), 0),
        ("0101798278", 0, (0, 0), 0),
        # Lookalikes: same shape, but not a Saudi national ID
        ("2222222222", 0, (0, 0), 0),  # passes raw Luhn, all digits the same
        ("1234567890", 0, (0, 0), 0),  # sequential run, fails the checksum
        # Invalid IDs: wrong length
        ("104784631", 0, (0, 0), 0),
        ("10478463144", 0, (0, 0), 0),
        # Invalid IDs: non-digits
        ("abcdefghij", 0, (0, 0), 0),
    ],
)
def test_when_saudi_id_in_text_then_all_ids_found(
    text, expected_len, expected_position, expected_score, recognizer, entities
):
    """Test that the recognizer finds valid IDs and rejects invalid ones."""
    results = recognizer.analyze(text, entities)

    assert len(results) == expected_len
    if expected_len > 0:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


def test_multiple_ids_positions(recognizer, entities):
    """Both IDs in one text are found at their exact positions."""
    results = recognizer.analyze("IDs: 1047846314 and 2054789637", entities)

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 15, MAX_SCORE)
    assert_result(results[1], entities[0], 20, 30, MAX_SCORE)


def test_validate_result_with_valid_ids(recognizer):
    """Test validate_result method with valid IDs."""
    assert recognizer.validate_result("1101798278") is True
    assert recognizer.validate_result("1047846314") is True
    assert recognizer.validate_result("2054789637") is True
    assert recognizer.validate_result("2123456788") is True


def test_validate_result_with_wrong_checksum(recognizer):
    """Test validate_result method with a wrong check digit."""
    assert recognizer.validate_result("1101798279") is False
    assert recognizer.validate_result("1047846315") is False
    assert recognizer.validate_result("2054789638") is False


def test_validate_result_with_invalid_first_digit(recognizer):
    """Test validate_result with IDs not starting with 1 or 2."""
    assert recognizer.validate_result("3047846314") is False
    assert recognizer.validate_result("0101798278") is False
    assert recognizer.validate_result("9047846314") is False


def test_validate_result_with_trivial_values(recognizer):
    """All-same-digit values are rejected even when Luhn passes."""
    assert recognizer.validate_result("2222222222") is False
    assert recognizer.validate_result("1111111111") is False


def test_validate_result_with_wrong_length(recognizer):
    """Test validate_result method with wrong length."""
    assert recognizer.validate_result("104784631") is False
    assert recognizer.validate_result("10478463144") is False


def test_validate_result_with_non_digits(recognizer):
    """Test validate_result method with non-digit characters."""
    assert recognizer.validate_result("abcdefghij") is False


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "iqama",
        "national id",
        "national identification number",
        "residence permit",
        "saudi",
        "kingdom of saudi arabia",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["SA_NATIONAL_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = SaNationalIdRecognizer(name="CustomSaNationalId")
    assert recognizer.name == "CustomSaNationalId"


def test_context_does_not_override_checksum(mock_nlp_engine):
    """Context words never rescue a number with a bad check digit.

    A checksum-valid ID is promoted to MAX_SCORE by validate_result, so
    context cannot raise it further; a checksum-invalid ID stays dropped
    even when a context word surrounds it.
    """
    registry = RecognizerRegistry()
    registry.add_recognizer(SaNationalIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="2054789637", language="en", entities=["SA_NATIONAL_ID"]
    )
    assert len(plain) == 1
    assert plain[0].score == MAX_SCORE

    with_context = analyzer.analyze(
        text="Iqama 2054789637", language="en", entities=["SA_NATIONAL_ID"]
    )
    assert len(with_context) == 1
    assert with_context[0].score == MAX_SCORE

    invalid_with_context = analyzer.analyze(
        text="Iqama 2054789638", language="en", entities=["SA_NATIONAL_ID"]
    )
    assert invalid_with_context == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "SaNationalIdRecognizer"]
    assert len(entries) == 1, "SaNationalIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "sa"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "SaNationalIdRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "SA_NATIONAL_ID" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My Iqama is 2054789637", language="en", entities=["SA_NATIONAL_ID"]
    )
    assert [result.entity_type for result in results] == ["SA_NATIONAL_ID"]
