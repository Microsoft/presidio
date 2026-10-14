from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers.country_specific.korea.kr_passport_recognizer import (
    KrPassportRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return KrPassportRecognizer()

@pytest.fixture(scope="module")
def entities():
    return ["KR_PASSPORT"]

@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid current format passports (M + 3 digits + 1 letter + 4 digits)
        ("M123A4567", 1, ((0, 9),), ((0.1, 0.1),)),
        ("m456B7890", 1, ((0, 9),), ((0.1, 0.1),)),
        ("d789C1234", 1, ((0, 9),), ((0.1, 0.1),)),
        ("S012D5678", 1, ((0, 9),), ((0.1, 0.1),)),
        ("M345E9012", 1, ((0, 9),), ((0.1, 0.1),)),
        ("M678f3456", 1, ((0, 9),), ((0.1, 0.1),)),
        ("M901g7890", 1, ((0, 9),), ((0.1, 0.1),)),
        ("My passport number is M123A4567", 1, ((22, 31),), ((0.1, 0.1),)),
        ("Korean passport: M456B7890", 1, ((17, 26),), ((0.1, 0.1),)),
        ("여권번호는 M789C1234입니다", 1, ((6, 15),), ((0.1, 0.1),)),

        # Valid previous format passports (M + 8 digits)
        ("M12345678", 1, ((0, 9),), ((0.05, 0.05),)),
        ("m87654321", 1, ((0, 9),), ((0.05, 0.05),)),
        ("d11223344", 1, ((0, 9),), ((0.05, 0.05),)),
        ("s99887766", 1, ((0, 9),), ((0.05, 0.05),)),
        ("My old passport M12345678", 1, ((16, 25),), ((0.05, 0.05),)),
        ("대한민국 여권 S87654321", 1, ((8, 17),), ((0.05, 0.05),)),

        # Multiple passport numbers
        ("M123A4567 and M456B7890", 2, ((0, 9), (14, 23)), ((0.1, 0.1), (0.1, 0.1))),

        # Invalid formats - should not match
        ("A123B4567", 0, (), ()),  # Wrong first letter
        ("M12A4567", 0, (), ()),   # Too few digits before letter
        ("M1234A567", 0, (), ()),  # Too many digits before letter
        ("M123AB567", 0, (), ()),  # Two letters
        ("M123A456", 0, (), ()),   # Too few final digits
        ("M123A45678", 0, (), ()), # Too many final digits
        ("M1234567", 0, (), ()),   # Missing letter in current format
        ("M123456789", 0, (), ()), # Too many digits for old format
        ("M1234567", 0, (), ()),   # Too few digits for old format
        ("123A4567", 0, (), ()),   # Missing M
        ("MM123A4567", 0, (), ()), # Double M
        ("M123 A4567", 0, (), ()), # Space in number
        ("M123-A4567", 0, (), ()), # Hyphen in number
        ("", 0, (), ()),           # Empty string
        ("passport", 0, (), ()),   # Just text
        ("M123a456", 0, (), ()),   # Wrong number of digits after letter
    ],
)
def test_when_all_passports_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )

def test_when_passport_with_context_then_succeed(recognizer, entities):
    """Test passport recognition with context keywords"""
    text = "Korean passport number: M123A4567"
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert results[0].start == 24
    assert results[0].end == 33
    assert results[0].entity_type == "KR_PASSPORT"

def test_when_passport_korean_context_then_succeed(recognizer, entities):
    """Test passport recognition with Korean context"""
    text = "대한민국 여권번호: M456B7890"
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert results[0].start == 11
    assert results[0].end == 20
    assert results[0].entity_type == "KR_PASSPORT"

def test_when_no_passport_then_no_results(recognizer, entities):
    """Test that invalid formats return no results"""
    invalid_texts = [
        "This is just text",
        "A123B4567",  # Wrong prefix
        "M12A4567",   # Wrong format
        "M123456789", # Too long for old format
        "123A4567",   # Missing M prefix
    ]

    for text in invalid_texts:
        results = recognizer.analyze(text, entities)
        assert len(results) == 0, f"Expected no results for text: {text}"


def test_default_supported_language_is_ko():
    """Default language must be ``ko``, like the other Korean recognizers.

    It was previously ``kr``, which registered the recognizer under a language
    code that an AnalyzerEngine running ``ko`` never queried.
    """
    assert KrPassportRecognizer().supported_language == "ko"


def test_accepts_name_kwarg():
    """Constructor must accept the ``name`` kwarg the YAML loader passes.

    Without it, loading the recognizer from a registry YAML raises
    ``TypeError``, which is why it could not be listed there before.
    """
    recognizer = KrPassportRecognizer(name="CustomKrPassport")
    assert recognizer.name == "CustomKrPassport"


@pytest.mark.parametrize("language", ["ko", "kr"])
def test_loads_from_default_recognizers_yaml(language):
    """Recognizer is registered in the default YAML and loads once enabled.

    The constructor default is ``ko`` (see above), but the shipped entry also
    advertises ``kr`` as a deprecated alias, kept because the class defaulted to
    ``kr`` until #2170 (2026-08-05) and a registry configured against that
    default would otherwise go quiet. Both codes are asserted here so the alias
    cannot be dropped without this test noticing.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "KrPassportRecognizer"]
    assert len(entries) == 1, "KrPassportRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "kr"
    assert language in entry["supported_languages"]

    # Handed to the provider in memory rather than written to a temporary file:
    # ``registry_configuration`` takes the same mapping the YAML parses to, so a
    # round trip through the filesystem would only add a directory to clean up.
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["KrPassportRecognizer"]
    entities = {e for rec in registry.recognizers for e in rec.supported_entities}
    assert "KR_PASSPORT" in entities
