from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import PkCnicRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)

from tests import assert_result


@pytest.fixture(scope="module")
def recognizer() -> PkCnicRecognizer:
    return PkCnicRecognizer()


@pytest.fixture(scope="module")
def entities() -> list[str]:
    return ["PK_CNIC"]


@pytest.mark.parametrize(
    "text, expected_len, expected_position, expected_score",
    [
        # fmt: off
        # --- Valid CNICs, dashed format (strong pattern) ---
        ("35202-1234567-1", 1, (0, 15), 0.65),
        ("61101-1234567-8", 1, (0, 15), 0.65),
        (
            "My CNIC number is 35202-1234567-1 with a lot of text beyond it",
            1,
            (18, 33),
            0.65,
        ),
        # --- Valid CNICs, continuous format (weak pattern) ---
        ("3520212345671", 1, (0, 13), 0.3),
        ("6110112345678", 1, (0, 13), 0.3),
        # --- Invalid: first digit is not a province or region code (1 to 7) ---
        ("05202-1234567-1", 0, (0, 0), 0),
        ("95202-1234567-1", 0, (0, 0), 0),
        ("8520212345671", 0, (0, 0), 0),
        # --- Invalid: wrong digit counts ---
        ("35202-123456-1", 0, (0, 0), 0),
        ("352021234567", 0, (0, 0), 0),
        ("35202123456711", 0, (0, 0), 0),
        # --- Lookalikes: same shape, but not a CNIC ---
        ("3333333333333", 0, (0, 0), 0),
        ("11111-1111111-1", 0, (0, 0), 0),
        ("1234567890123", 0, (0, 0), 0),
        ("7654321098765", 0, (0, 0), 0),
        ("Order number 8520212345671 was shipped", 0, (0, 0), 0),
        # fmt: on
    ],
)
def test_when_cnic_in_text_then_all_cnics_found(
    text,
    expected_len,
    expected_position,
    expected_score,
    recognizer,
    entities,
) -> None:
    results = recognizer.analyze(text, entities)
    print(results)

    assert len(results) == expected_len
    if results:
        assert_result(
            results[0],
            entities[0],
            expected_position[0],
            expected_position[1],
            expected_score,
        )


sequential_test_set = [
    ["1234567890123", True],
    ["9876543210987", True],
    ["3520212345671", False],
    ["6110112345678", False],
]


@pytest.mark.parametrize("input_text, expected_output", sequential_test_set)
def test_is_sequential(input_text, expected_output):
    """Test the sequential digit run check used to invalidate trivial CNICs."""
    assert PkCnicRecognizer._is_sequential(input_text) == expected_output


def test_invalidate_result(recognizer):
    """Sanity checks reject trivial numbers and accept real CNIC shapes."""
    assert recognizer.invalidate_result("35202-1234567-1") is False
    assert recognizer.invalidate_result("3520212345671") is False
    assert recognizer.invalidate_result("11111-1111111-1") is True
    assert recognizer.invalidate_result("1234567890123") is True
    assert recognizer.invalidate_result("05202-1234567-1") is True


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, taking down construction of the whole registry.
    """
    recognizer = PkCnicRecognizer(name="CustomPkCnic")
    assert recognizer.name == "CustomPkCnic"


def test_context_word_boosts_score(mock_nlp_engine):
    """A context word around a CNIC raises its score above the pattern score."""
    registry = RecognizerRegistry()
    registry.add_recognizer(PkCnicRecognizer())
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)

    plain = analyzer.analyze(
        text="35202-1234567-1", language="en", entities=["PK_CNIC"]
    )
    with_context = analyzer.analyze(
        text="35202-1234567-1",
        language="en",
        entities=["PK_CNIC"],
        context=["cnic"],
    )

    assert len(plain) == 1
    assert plain[0].score == 0.65
    assert len(with_context) == 1
    assert with_context[0].score > plain[0].score


def test_loads_from_default_recognizers_yaml(mock_nlp_engine):
    """Recognizer is registered in the default YAML and detects once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "PkCnicRecognizer"]
    assert len(entries) == 1, "PkCnicRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "pk"
    assert entry["enabled"] is False
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["PkCnicRecognizer"]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "PK_CNIC" in entities

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=mock_nlp_engine)
    results = analyzer.analyze(
        text="My CNIC is 35202-1234567-1", language="en", entities=["PK_CNIC"]
    )
    assert [result.entity_type for result in results] == ["PK_CNIC"]
