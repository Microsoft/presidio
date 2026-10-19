import time
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import FrSirenRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

REGISTRY_CONF = """
supported_languages:
  - {language}
recognizers:
  - name: FrSirenRecognizer
    supported_languages:
      - fr
      - en
    type: predefined
    enabled: true
    country_code: fr
"""


@pytest.fixture(scope="module")
def recognizer():
    """Build the recognizer directly."""
    return FrSirenRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity under test."""
    return ["FR_SIREN"]


def load_registry(tmp_path, language):
    """Load the recognizer the way users do: enabled in a registry YAML."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(REGISTRY_CONF.format(language=language), encoding="utf-8")
    return RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()


@pytest.mark.parametrize(
    "text, expected",
    [
        # fmt: off
        # INSEE's own SIREN, and the example of the INSEE schema documentation
        ("120027016", [(0, 9, 0.05)]),
        ("422260208", [(0, 9, 0.05)]),
        ("120 027 016", [(0, 11, 0.1)]),
        # No-break space and narrow no-break space
        ("120\u00a0027\u00a0016", [(0, 11, 0.1)]),
        ("120\u202f027\u202f016", [(0, 11, 0.1)]),
        # Embedded in text
        ("Immatriculée sous le numéro 120 027 016.", [(28, 39, 0.1)]),
        ("FR 85 120027016", [(6, 15, 0.05)]),
        ("120027016 et 422260208", [(0, 9, 0.05), (13, 22, 0.05)]),
        # Lookalike: counter-example given by INSEE, fails the checksum
        ("123456789", []),
        ("Commande 123 456 789", []),
        # One digit off
        ("120027017", []),
        # Passes Luhn but is not an assigned number
        ("000000000", []),
        # Wrong length or separator
        ("12002701", []),
        ("1200270160", []),
        ("120-027-016", []),
        ("120.027.016", []),
        # A shorter neighbouring digit group does not hide the number
        ("1 120 027 016", [(2, 13, 0.1)]),
        ("120 027 016 2", [(0, 11, 0.1)]),
        ("120 027 016 422 260 208", [(0, 11, 0.1), (12, 23, 0.1)]),
        ("SIREN 120 027 016 15 rue de la Paix", [(6, 17, 0.1)]),
        ("SIREN 120 027 016 92120 Montrouge", [(6, 17, 0.1)]),
        # Known limit: a 3-digit group before the number is tried first,
        # fails the checksum, and the scan resumes past the real start
        ("422 120 027 016", []),
        # The first 9 digits of a spaced SIRET are a SIREN
        ("120 027 016 00563", [(0, 11, 0.1)]),
        ("120 027 016 12346", [(0, 11, 0.1)]),
        ("120027016 00563", [(0, 9, 0.05)]),
        ("120027016 92120 Montrouge", [(0, 9, 0.05)]),
        # A compact SIRET holds no separate SIREN
        ("12002701600563", []),
        # Full-width digits: identifiers are written in ASCII digits
        ("\uff11\uff12\uff10\uff10\uff12\uff17\uff10\uff11\uff16", []),
        # fmt: on
    ],
)
def test_when_siren_in_text_then_exact_spans_and_scores(
    text, expected, recognizer, entities
):
    """Spans and scores are exact; invalid or lookalike values are dropped."""
    results = recognizer.analyze(text, entities)

    assert [(r.start, r.end) for r in results] == [(s, e) for s, e, _ in expected]
    assert [r.score for r in results] == [pytest.approx(s) for *_, s in expected]
    assert all(r.entity_type == "FR_SIREN" for r in results)


def test_when_long_digit_groups_then_no_match(recognizer, entities):
    """A long adversarial input is handled without backtracking blow-up."""
    start = time.perf_counter()

    results = recognizer.analyze("123 " * 50_000, entities)

    assert results == []
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize(
    "text, expected_score",
    [
        ("120027016", 0.05),
        ("SIREN 120027016", 0.4),
        ("SIREN 120 027 016", 0.45),
        # Context is looked up before the match only
        ("120027016 SIREN", 0.05),
    ],
)
def test_when_loaded_from_yaml_then_detects_and_uses_context(
    text, expected_score, tmp_path, spacy_nlp_engine
):
    """Detection works through the YAML path and context raises the score."""
    registry = load_registry(tmp_path, "en")
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze(text, language="en")

    assert [r.entity_type for r in results] == ["FR_SIREN"]
    assert results[0].score == pytest.approx(expected_score)


def test_when_loaded_from_yaml_for_french_then_recognizer_is_french(tmp_path):
    """The top-level language filter must list ``fr`` for a French analyzer."""
    registry = load_registry(tmp_path, "fr")

    assert [type(r).__name__ for r in registry.recognizers] == ["FrSirenRecognizer"]
    assert registry.recognizers[0].supported_language == "fr"
    results = registry.recognizers[0].analyze("120 027 016", ["FR_SIREN"])
    assert [(r.start, r.end) for r in results] == [(0, 11)]


def test_when_built_directly_then_same_as_yaml(tmp_path, recognizer):
    """Direct construction and YAML loading produce the same recognizer."""
    loaded = load_registry(tmp_path, "fr").recognizers[0]

    assert loaded.supported_language == recognizer.supported_language
    assert loaded.country_code() == recognizer.country_code() == "fr"
    assert loaded.supported_entities == recognizer.supported_entities
    assert loaded.context == recognizer.context
    assert [p.to_dict() for p in loaded.patterns] == [
        p.to_dict() for p in recognizer.patterns
    ]


def test_when_enabled_in_shipped_yaml_then_loads(tmp_path):
    """The entry shipped in ``default_recognizers.yaml`` loads once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "FrSirenRecognizer"]
    assert len(entries) == 1
    assert entries[0]["enabled"] is False
    assert entries[0]["country_code"] == "fr"
    assert entries[0]["supported_languages"] == ["fr", "en"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["fr", "en"],
            "recognizers": [dict(entries[0], enabled=True)],
        }
    ).create_recognizer_registry()

    assert sorted(r.supported_language for r in registry.recognizers) == ["en", "fr"]
    assert {type(r).__name__ for r in registry.recognizers} == {"FrSirenRecognizer"}


def test_when_context_is_empty_list_then_context_is_disabled():
    """An explicit empty context is kept, not replaced by the default."""
    assert FrSirenRecognizer(context=[]).context == []
    assert FrSirenRecognizer(context=None).context == FrSirenRecognizer.CONTEXT


def test_when_yaml_sets_empty_context_per_language_then_no_boost(spacy_nlp_engine):
    """An empty context set per language in the YAML disables the boost."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "FrSirenRecognizer",
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "fr",
                    "supported_languages": [{"language": "en", "context": []}],
                }
            ],
        }
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze("SIREN 120027016", language="en")

    assert registry.recognizers[0].context == []
    assert [r.entity_type for r in results] == ["FR_SIREN"]
    assert results[0].score == pytest.approx(0.05)
