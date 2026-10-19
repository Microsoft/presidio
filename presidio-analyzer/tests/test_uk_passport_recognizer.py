from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import UkPassportRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests.assertions import assert_result

PATTERN_SCORE = 0.05

# 0.05 base + the 0.35 LemmaContextAwareEnhancer factor, raised to the
# enhancer's 0.4 floor.
CONTEXT_SCORE = 0.4


@pytest.fixture(scope="module")
def recognizer():
    """Create a UkPassportRecognizer instance."""
    return UkPassportRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the list of entities to detect."""
    return ["UK_PASSPORT"]


@pytest.fixture(scope="module")
def analyze_uk_passport(spacy_nlp_engine):
    """Return an analyzer over this recognizer with real spaCy tokenization."""

    def analyze(text, recognizer, score_threshold=0):
        registry = RecognizerRegistry()
        registry.add_recognizer(recognizer)
        analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
        return analyzer.analyze(
            text=text,
            language="en",
            entities=["UK_PASSPORT"],
            score_threshold=score_threshold,
        )

    return analyze


@pytest.mark.parametrize(
    "text, expected_positions",
    [
        # fmt: off
        # A passport number on its own.
        ("123456789", ((0, 9),)),
        ("533401372", ((0, 9),)),
        # Embedded in text.
        ("My passport number is 707797979 and it expires soon", ((22, 31),)),
        ("Passport No. 987654321.", ((13, 22),)),
        # Two numbers in one line.
        ("Passports: 123456789 and 987654321", ((11, 20), (25, 34))),
        # fmt: on
    ],
)
def test_when_passport_in_text_then_all_uk_passports_found(
    text, expected_positions, recognizer, entities
):
    """Nine digits is the format HM Passport Office issues."""
    results = recognizer.analyze(text, entities)
    assert len(results) == len(expected_positions)

    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entities[0], start, end, PATTERN_SCORE)


@pytest.mark.parametrize(
    "text",
    [
        # fmt: off
        # Two letters and seven digits: what this recognizer used to match.
        # It is not a UK passport number in any series, so it is a negative now.
        "AB1234567",
        "ab1234567",
        # The serial on the thin film patch over the photo, 3 letters and 4
        # digits. gov.uk warns not to confuse it with the passport number, so
        # it is pinned here. It is not the lookalike a nine-digit pattern has
        # to live with, though: that is a nine-digit number which is not a
        # passport, and the threshold test below is where it lives.
        "ABC1234",
        # Wrong length.
        "12345678",
        "1234567890",
        # Digits broken up or glued to something else.
        "1234 56789",
        "123-456-789",
        "REF123456789X",
        # fmt: on
    ],
)
def test_when_not_a_passport_number_then_no_result(text, recognizer, entities):
    """Shapes that are not nine standalone digits must not be returned."""
    assert recognizer.analyze(text, entities) == []


def test_context_word_raises_the_score(recognizer, analyze_uk_passport):
    """A passport word before the number raises the score to the enhancer's floor."""
    without_context = analyze_uk_passport("Reference 123456789", recognizer)
    with_context = analyze_uk_passport("Passport number 123456789", recognizer)
    # The enhancer reads the five words before the match and none after it, so
    # the same words behind the number leave the score alone.
    context_after = analyze_uk_passport("123456789 passport number", recognizer)

    assert len(without_context) == 1
    assert without_context[0].score == pytest.approx(PATTERN_SCORE)

    assert len(with_context) == 1
    assert with_context[0].score == pytest.approx(CONTEXT_SCORE)

    assert len(context_after) == 1
    assert context_after[0].score == pytest.approx(PATTERN_SCORE)


def test_only_the_contextual_match_survives_a_threshold(
    recognizer, analyze_uk_passport
):
    """A nine-digit order number is the lookalike this pattern has to live with.

    Nothing in the shape separates it from a passport number, so both match and
    the score is what carries the difference: only the contextual one is left
    once a caller sets a threshold.
    """
    order_number = "Your order 400512773 has shipped"
    passport = "Her UK passport is 400512773"

    assert analyze_uk_passport(order_number, recognizer, score_threshold=0.4) == []

    surviving = analyze_uk_passport(passport, recognizer, score_threshold=0.4)
    assert len(surviving) == 1
    assert surviving[0].score == pytest.approx(CONTEXT_SCORE)


def test_loads_from_default_recognizers_yaml_and_detects(spacy_nlp_engine):
    """Detection has to work through the path users actually configure.

    The shipped entry has enabled: false, so flipping that flag is the one way
    anybody reaches this recognizer. That entry is read here rather than
    retyped, so dropping it or mistyping the country code turns this red.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "UkPassportRecognizer"]
    assert len(entries) == 1, "UkPassportRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "uk"
    assert "en" in entry["supported_languages"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(rec).__name__ for rec in registry.recognizers] == [
        "UkPassportRecognizer"
    ]

    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
    results = analyzer.analyze("Passport number 123456789", language="en")

    assert len(results) == 1
    assert_result(results[0], "UK_PASSPORT", 16, 25, CONTEXT_SCORE)
