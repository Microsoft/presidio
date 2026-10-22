"""Tests for United Arab Emirates Emirates ID recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import AeEmiratesIdRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer():
    """Create an Emirates ID recognizer instance for testing."""
    return AeEmiratesIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Emirates ID entity type for testing."""
    return ["AE_EMIRATES_ID"]


# Fixtures are synthetic numbers built to the published format
# (784 + plausible year part + non-sequential serial + one digit), because
# the recognizer implements no checksum: the verification digit algorithm
# is not published in an authoritative source and no worked example with a
# full number could be found to test one against (see the recognizer
# docstring). The serial 1234567 used by published format examples, for
# example 784-2015-1234567-8, is treated as a trivial lookalike and must be
# rejected by the sanity checks.
@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid IDs, dashed format (strong pattern) ---
        ("784-1985-4029175-3", 1, (0, 18), 0.65),
        ("784-2001-5839204-7", 1, (0, 18), 0.65),
        (
            "Emirates ID number is 784-1985-4029175-3 for the employee",
            1,
            (22, 40),
            0.65,
        ),
        # --- Valid IDs, continuous format (weak pattern) ---
        ("784199276401839", 1, (0, 15), 0.3),
        ("784201830475629", 1, (0, 15), 0.3),
        (
            "The emirates id 784199276401839 was verified",
            1,
            (16, 31),
            0.3,
        ),
        # --- Invalid: does not start with the 784 country code ---
        ("785-1985-4029175-3", 0, (0, 0), 0),
        ("785199276401839", 0, (0, 0), 0),
        # --- Invalid: wrong digit counts ---
        ("784-1985-402917-3", 0, (0, 0), 0),
        ("78419854029175", 0, (0, 0), 0),
        ("7841985402917531", 0, (0, 0), 0),
        # --- Invalid: trivial serial part (sanity check) ---
        ("784-2015-1234567-8", 0, (0, 0), 0),
        ("784-2015-7654321-8", 0, (0, 0), 0),
        ("784201512345678", 0, (0, 0), 0),
        # --- Invalid: implausible year part (sanity check) ---
        ("784-1234-4029175-3", 0, (0, 0), 0),
        ("784-9999-4029175-3", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not an Emirates ID ---
        ("Order number 7842018304756291 was shipped", 0, (0, 0), 0),
        ("abcdefghijklmno", 0, (0, 0), 0),
        # fmt: on
    ],
)
def test_when_emirates_id_in_text_then_all_ids_found(
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
    results = recognizer.analyze(
        "IDs: 784-1985-4029175-3 and 784-2001-5839204-7", entities
    )

    assert len(results) == 2
    assert_result(results[0], entities[0], 5, 23, 0.65)
    assert_result(results[1], entities[0], 28, 46, 0.65)


sequential_test_set = [
    ["1234567", True],
    ["7654321", True],
    ["4029175", False],
    ["5839204", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used on the serial part."""
    assert AeEmiratesIdRecognizer._is_sequential(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real ID shapes."""
    assert recognizer.invalidate_result("784-1985-4029175-3") is False
    assert recognizer.invalidate_result("784199276401839") is False
    assert recognizer.invalidate_result("784-2015-1234567-8") is True
    assert recognizer.invalidate_result("784-1234-4029175-3") is True
    assert recognizer.invalidate_result("784-9999-4029175-3") is True
    assert recognizer.invalidate_result("785-1985-4029175-3") is True
    assert recognizer.invalidate_result("78419854029175") is True


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "emirates id",
        "emirates identity card",
        "uae national id",
        "identity card number",
        "uid",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["AE_EMIRATES_ID"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "en"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = AeEmiratesIdRecognizer(name="CustomAeEmiratesId")
    assert recognizer.name == "CustomAeEmiratesId"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around an Emirates ID raises its pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(AeEmiratesIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="784-1985-4029175-3", language="en", entities=["AE_EMIRATES_ID"]
    )
    with_context = analyzer.analyze(
        text="784-1985-4029175-3",
        language="en",
        entities=["AE_EMIRATES_ID"],
        context=["emirates id"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.65
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_context_does_not_rescue_invalid_id(mock_nlp_engine):
    """A context word never rescues a number the sanity checks reject."""
    registry = RecognizerRegistry()
    registry.add_recognizer(AeEmiratesIdRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    results = analyzer.analyze(
        text="Emirates ID 784-2015-1234567-8",
        language="en",
        entities=["AE_EMIRATES_ID"],
    )
    assert results == []


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "AeEmiratesIdRecognizer"]
    assert len(entries) == 1, "AeEmiratesIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "ae"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "AeEmiratesIdRecognizer"
    ]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "AE_EMIRATES_ID" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My Emirates ID is 784-1985-4029175-3",
        language="en",
        entities=["AE_EMIRATES_ID"],
    )
    assert [result.entity_type for result in results] == ["AE_EMIRATES_ID"]
