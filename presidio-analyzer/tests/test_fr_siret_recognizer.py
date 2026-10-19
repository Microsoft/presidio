import time
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import FrSiretRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

REGISTRY_CONF = """
supported_languages:
  - {language}
recognizers:
  - name: FrSiretRecognizer
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
    return FrSiretRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity under test."""
    return ["FR_SIRET"]


def load_registry(tmp_path, language):
    """Load the recognizer the way users do: enabled in a registry YAML."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(REGISTRY_CONF.format(language=language), encoding="utf-8")
    return RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()


@pytest.mark.parametrize(
    "text, expected",
    [
        # fmt: off
        # Head office of INSEE
        ("12002701600563", [(0, 14, 0.05)]),
        ("120 027 016 00563", [(0, 17, 0.3)]),
        # SIREN and NIC written as two groups
        ("120027016 00563", [(0, 15, 0.1)]),
        # A SIREN followed by a postal code is not a SIRET
        ("120027016 92120 Montrouge", []),
        ("120 027 016 92120 Montrouge", []),
        ("120027016\u00a000563", [(0, 15, 0.1)]),
        ("120027016\u202f00563", [(0, 15, 0.1)]),
        # No-break space and narrow no-break space
        ("120\u00a0027\u00a0016\u00a000563", [(0, 17, 0.3)]),
        ("120\u202f027\u202f016\u202f00563", [(0, 17, 0.3)]),
        # Embedded in text
        ("Établissement 120 027 016 00563, Montrouge.", [(14, 31, 0.3)]),
        # La Poste: head office passes Luhn, the Rennes establishment does not
        # but its digits sum to a multiple of 5
        ("35600000000048", [(0, 14, 0.05)]),
        ("35600000009075", [(0, 14, 0.05)]),
        ("356 000 000 09075", [(0, 17, 0.3)]),
        # La Poste: a number other than the head office passing Luhn only
        ("35600000012852", [(0, 14, 0.05)]),
        # La Poste: neither check passes
        ("35600000009076", []),
        # The multiple-of-5 rule applies to La Poste only
        ("12002701600006", []),
        # Lookalike: a 14-digit timestamp, fails the checksum
        ("20251231235959", []),
        # One digit off
        ("12002701600564", []),
        # Passes Luhn over 14 digits but the SIREN part does not
        ("12002700000005", []),
        # All zeros
        ("00000000000000", []),
        # Passes Luhn over 14 digits but the SIREN part is all zeros
        ("00000000000018", []),
        # Full-width digits: identifiers are written in ASCII digits
        (
            "\uff11\uff12\uff10\uff10\uff12\uff17\uff10\uff11\uff16\uff10\uff10\uff15\uff16\uff13",
            [],
        ),
        # Wrong length or separator
        ("1200270160056", []),
        ("120027016005630", []),
        ("120-027-016-00563", []),
        # Neighbouring digit groups do not hide the number
        ("9 120 027 016 00563", [(2, 19, 0.3)]),
        ("120 027 016 00563 2024", [(0, 17, 0.3)]),
        ("120 027 016 00563 356 000 000 09075", [(0, 17, 0.3), (18, 35, 0.3)]),
        # fmt: on
    ],
)
def test_when_siret_in_text_then_exact_spans_and_scores(
    text, expected, recognizer, entities
):
    """Spans and scores are exact; invalid or lookalike values are dropped."""
    results = recognizer.analyze(text, entities)

    assert [(r.start, r.end) for r in results] == [(s, e) for s, e, _ in expected]
    assert [r.score for r in results] == [pytest.approx(s) for *_, s in expected]
    assert all(r.entity_type == "FR_SIRET" for r in results)


def test_when_long_digit_groups_then_no_match(recognizer, entities):
    """A long adversarial input is handled without backtracking blow-up."""
    start = time.perf_counter()

    results = recognizer.analyze("123 " * 50_000, entities)

    assert results == []
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize(
    "text, expected_score",
    [
        ("12002701600563", 0.05),
        ("SIRET 12002701600563", 0.4),
        ("SIRET 120 027 016 00563", 0.65),
        ("SIRET 120027016 00563", 0.45),
        # Context is looked up before the match only
        ("12002701600563 SIRET", 0.05),
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

    assert [r.entity_type for r in results] == ["FR_SIRET"]
    assert results[0].score == pytest.approx(expected_score)


def test_when_loaded_from_yaml_for_french_then_recognizer_is_french(tmp_path):
    """The top-level language filter must list ``fr`` for a French analyzer."""
    registry = load_registry(tmp_path, "fr")

    assert [type(r).__name__ for r in registry.recognizers] == ["FrSiretRecognizer"]
    assert registry.recognizers[0].supported_language == "fr"
    results = registry.recognizers[0].analyze("120 027 016 00563", ["FR_SIRET"])
    assert [(r.start, r.end) for r in results] == [(0, 17)]


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


def test_when_both_french_recognizers_then_spaced_siret_holds_a_siren(tmp_path):
    """A spaced SIRET is also reported as the SIREN it starts with."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        REGISTRY_CONF.format(language="fr").replace(
            "recognizers:\n",
            "recognizers:\n"
            "  - name: FrSirenRecognizer\n"
            "    supported_languages:\n"
            "      - fr\n"
            "    type: predefined\n"
            "    enabled: true\n"
            "    country_code: fr\n",
        ),
        encoding="utf-8",
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    text = "SIRET 120 027 016 00563, SIREN 120 027 016"

    found = sorted(
        (r.entity_type, r.start, r.end)
        for recognizer in registry.recognizers
        for r in recognizer.analyze(text, recognizer.supported_entities)
    )

    assert found == [
        ("FR_SIREN", 6, 17),
        ("FR_SIREN", 31, 42),
        ("FR_SIRET", 6, 23),
    ]


def test_when_enabled_in_shipped_yaml_then_loads(tmp_path):
    """The entry shipped in ``default_recognizers.yaml`` loads once enabled."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "FrSiretRecognizer"]
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
    assert {type(r).__name__ for r in registry.recognizers} == {"FrSiretRecognizer"}


def test_when_context_is_empty_list_then_context_is_disabled():
    """An explicit empty context is kept, not replaced by the default."""
    assert FrSiretRecognizer(context=[]).context == []
    assert FrSiretRecognizer(context=None).context == FrSiretRecognizer.CONTEXT


def test_when_yaml_sets_empty_context_per_language_then_no_boost(spacy_nlp_engine):
    """An empty context set per language in the YAML disables the boost."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "FrSiretRecognizer",
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

    results = analyzer.analyze("SIRET 12002701600563", language="en")

    assert registry.recognizers[0].context == []
    assert [r.entity_type for r in results] == ["FR_SIRET"]
    assert results[0].score == pytest.approx(0.05)


def test_when_both_recognizers_in_analyzer_then_siren_is_inside_siret(
    spacy_nlp_engine,
):
    """AnalyzerEngine returns the SIRET and, inside its span, the SIREN."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": name,
                    "type": "predefined",
                    "enabled": True,
                    "country_code": "fr",
                    "supported_languages": ["fr", "en"],
                }
                for name in ("FrSirenRecognizer", "FrSiretRecognizer")
            ],
        }
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze("120 027 016 00563", language="en")

    found = sorted((r.entity_type, r.start, r.end, r.score) for r in results)
    assert found == [
        ("FR_SIREN", 0, 11, pytest.approx(0.1)),
        ("FR_SIRET", 0, 17, pytest.approx(0.3)),
    ]
