"""
Tests for AtSvnrRecognizer (Austrian Versicherungsnummer, AT_SVNR).

Format: LLLPTTMMJJ, a 3-digit serial (first digit 1-9), a check digit, and six
digits that usually hold the date of birth (DDMMYY).

Check digit: weights 3, 7, 9 on the serial and 5, 8, 4, 2, 1, 6 on the six date
digits, sum mod 11. A remainder of 10 is never issued.

All numbers below are synthetic and none is taken from a real document: the
check digits were computed for these tests, and the date parts are impossible
calendar dates (30 February, 31 April, ...) or fictitious-date values (months
13 to 15 per the official sources; days above 31 per Wikipedia de).

  4131300271  serial 413, 30.02.71               check 1
  2603310605  serial 260, 31.06.05               check 3
  5046310963  serial 504, 31.09.63               check 6
  1895311188  serial 189, 31.11.88               check 5
  3339310407  serial 333, 31.04.07               check 9
  3421471461  serial 342, day 47, month 14       check 1
  6152391554  serial 615, day 39, month 15       check 2

Never issued (remainder 10): serial 958 with 310492, serial 731 with 290226.
"""

from pathlib import Path

import presidio_analyzer
import pytest
import spacy
import yaml
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.predefined_recognizers import AtSvnrRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result
from tests.mocks import NlpEngineMock

COMPACT_SCORE = 0.05
SPACED_SCORE = 0.2
# Pattern scores after LemmaContextAwareEnhancer's defaults
# (context_similarity_factor 0.35, min_score_with_context_similarity 0.4).
COMPACT_WITH_CONTEXT_SCORE = 0.4
SPACED_WITH_CONTEXT_SCORE = 0.55

YAML_CONFIG = """
supported_languages:
  - de
recognizers:
  - name: AtSvnrRecognizer
    supported_languages:
      - de
    type: predefined
    enabled: true
    country_code: at
"""

# spaCy's rule-based German tokenizer, the one the trained German pipelines
# use; no model is downloaded. It keeps "SV-Nr", "SV-Nummer" and "e-card" as
# single tokens, which the hyphenated context words rely on.
GERMAN_NLP = spacy.blank("de")


@pytest.fixture(scope="module")
def recognizer():
    """Return a recognizer built with its defaults."""
    return AtSvnrRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity list passed to ``analyze``."""
    return ["AT_SVNR"]


def _nlp_artifacts(text):
    """German tokens, with lower-cased tokens standing in for lemmas."""
    doc = GERMAN_NLP(text)
    return NlpArtifacts(
        entities=[],
        tokens=doc,
        tokens_indices=[token.idx for token in doc],
        lemmas=[token.text.lower() for token in doc],
        nlp_engine=NlpEngineMock(),
        language="de",
    )


def _analyze_with_context(text, recognizer, entities):
    nlp_artifacts = _nlp_artifacts(text)
    raw_results = recognizer.analyze(text, entities, nlp_artifacts)
    return LemmaContextAwareEnhancer().enhance_using_context(
        text, raw_results, nlp_artifacts, [recognizer]
    )


def _load_registry_from_yaml(tmp_path):
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(YAML_CONFIG, encoding="utf-8")
    return RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()


def _analyze_de(registry, text):
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NlpEngineMock(nlp_artifacts=_nlp_artifacts(text)),
        supported_languages=["de"],
    )
    results = analyzer.analyze(text, language="de")
    return sorted(results, key=lambda result: result.start)


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score",
    [
        # fmt: off
        # Compact 10 digits (very weak pattern)
        ("4131300271", 1, ((0, 10),), COMPACT_SCORE),
        ("1895311188", 1, ((0, 10),), COMPACT_SCORE),
        # Non-calendar date parts (month 13-15, day above 31) are not rejected
        ("3421471461", 1, ((0, 10),), COMPACT_SCORE),
        # Written as LLLP TTMMJJ and LLLP TT MM JJ (weak pattern)
        ("2603 310605", 1, ((0, 11),), SPACED_SCORE),
        ("3339 310407", 1, ((0, 11),), SPACED_SCORE),
        ("6152 391554", 1, ((0, 11),), SPACED_SCORE),
        ("5046 31 09 63", 1, ((0, 13),), SPACED_SCORE),
        # The same written forms with a no-break space (U+00A0)
        ("2603 310605", 1, ((0, 11),), SPACED_SCORE),
        ("5046 31 09 63", 1, ((0, 13),), SPACED_SCORE),
        # Embedded in text
        ("Meine SVNR ist 2603 310605, bitte prüfen.", 1, ((15, 26),), SPACED_SCORE),
        ("4131300271 und 1895311188", 2, ((0, 10), (15, 25)), COMPACT_SCORE),
        # Wrong check digit
        ("4132300271", 0, (), None),
        ("2604 310605", 0, (), None),
        ("5047 31 09 63", 0, (), None),
        # Check-digit remainder 10: never issued, whatever the check digit
        ("9580310492", 0, (), None),
        ("9589 310492", 0, (), None),
        ("7315 29 02 26", 0, (), None),
        # Serial starting with 0 (check digit would be valid)
        ("0413300271", 0, (), None),
        ("0413 300271", 0, (), None),
        # Too short / too long
        ("413130027", 0, (), None),
        ("41313002711", 0, (), None),
        # Valid number embedded in a longer digit or alphanumeric run
        ("94131300271", 0, (), None),
        ("41313002719", 0, (), None),
        ("AT4131300271", 0, (), None),
        ("4131300271X", 0, (), None),
        # Other groupings, double space, line break
        ("413 1300271", 0, (), None),
        ("4131 3002 71", 0, (), None),
        ("4131  300271", 0, (), None),
        ("4131\n300271", 0, (), None),
        # Lookalikes: a phone number with area code and an order reference
        ("Tel. +43 2742 12 34 56", 0, (), None),
        ("Bestellung 2024 123456", 0, (), None),
        # fmt: on
    ],
)
def test_when_all_at_svnrs_then_succeed(
    text, expected_len, expected_positions, expected_score, recognizer, entities
):
    """Valid numbers match with exact positions and scores; others do not."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, expected_score)


def test_valid_check_digit_does_not_promote_to_max_score(recognizer, entities):
    """A passing check digit filters; it must not lift a match to 1.0.

    About 1 in 11 random 10-digit runs pass the check, so the pattern score
    stands and only context raises it.
    """
    compact = recognizer.analyze("4131300271", entities)
    spaced = recognizer.analyze("2603 310605", entities)

    assert [r.score for r in compact] == [COMPACT_SCORE]
    assert [r.score for r in spaced] == [SPACED_SCORE]
    assert EntityRecognizer.MAX_SCORE not in [r.score for r in compact + spaced]


@pytest.mark.parametrize(
    "number, expected",
    [
        # Valid (synthetic)
        ("4131300271", False),
        ("2603310605", False),
        ("5046310963", False),
        ("1895311188", False),
        ("3339310407", False),
        ("3421471461", False),
        ("6152391554", False),
        # Valid with the spaces of the written forms
        ("4131 300271", False),
        ("4131 30 02 71", False),
        # Wrong check digit
        ("4130300271", True),
        ("4132300271", True),
        ("2600310605", True),
        # Serial starting with 0
        ("0413300271", True),
        # Wrong length or not only digits
        ("413130027", True),
        ("41313002711", True),
        ("41313002A1", True),
        ("", True),
    ],
)
def test_when_at_svnr_invalidated_then_result_is_correct(number, expected, recognizer):
    """``invalidate_result`` drops exactly the numbers that cannot be issued."""
    assert recognizer.invalidate_result(number) is expected


@pytest.mark.parametrize(
    "serial, date_part, accepted_check_digits",
    [
        ("413", "300271", [1]),
        ("260", "310605", [3]),
        ("342", "471461", [1]),
        # Remainder 10 is never issued, so no check digit is accepted
        ("958", "310492", []),
        ("731", "290226", []),
    ],
)
def test_when_check_digit_varies_then_only_the_computed_one_is_accepted(
    serial, date_part, accepted_check_digits, recognizer
):
    """Of the ten possible check digits, only the computed one passes."""
    accepted = [
        digit
        for digit in range(10)
        if not recognizer.invalidate_result(f"{serial}{digit}{date_part}")
    ]

    assert accepted == accepted_check_digits


@pytest.mark.parametrize(
    "text, expected_score",
    [
        # fmt: off
        ("SVNR: 4131300271", COMPACT_WITH_CONTEXT_SCORE),
        ("VSNR 4131300271", COMPACT_WITH_CONTEXT_SCORE),
        ("VNR 4131300271", COMPACT_WITH_CONTEXT_SCORE),
        ("Versicherungsnummer 4131300271", COMPACT_WITH_CONTEXT_SCORE),
        ("Sozialversicherungsnummer 2603 310605", SPACED_WITH_CONTEXT_SCORE),
        ("SV-Nummer: 2603 310605", SPACED_WITH_CONTEXT_SCORE),
        ("SV-Nr. 5046 31 09 63", SPACED_WITH_CONTEXT_SCORE),
        ("e-card 2603 310605", SPACED_WITH_CONTEXT_SCORE),
        # fmt: on
    ],
)
def test_when_context_word_precedes_then_score_is_raised(
    text, expected_score, recognizer, entities
):
    """A context word before the number raises the pattern score."""
    results = _analyze_with_context(text, recognizer, entities)

    assert len(results) == 1
    assert results[0].entity_type == "AT_SVNR"
    assert results[0].score == pytest.approx(expected_score)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        # fmt: off
        ("4131300271", COMPACT_SCORE),
        ("Kundennummer 4131300271", COMPACT_SCORE),
        # Context is prefix-only by default (context_suffix_count=0)
        ("4131300271 ist die SVNR", COMPACT_SCORE),
        ("2603 310605 (Versicherungsnummer)", SPACED_SCORE),
        # fmt: on
    ],
)
def test_when_context_word_is_absent_or_follows_then_score_is_unchanged(
    text, expected_score, recognizer, entities
):
    """Without a preceding context word the pattern score stands."""
    results = _analyze_with_context(text, recognizer, entities)

    assert len(results) == 1
    assert results[0].entity_type == "AT_SVNR"
    assert results[0].score == pytest.approx(expected_score)


def test_default_recognizers_yaml_entry_ships_disabled():
    """The shipped entry is tagged ``at``, German-only and disabled by default."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "AtSvnrRecognizer"]

    assert len(entries) == 1, "AtSvnrRecognizer missing from YAML"
    assert entries[0]["enabled"] is False
    assert entries[0]["country_code"] == "at"
    assert entries[0]["supported_languages"] == ["de"]
    assert AtSvnrRecognizer.COUNTRY_CODE == "at"


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path, recognizer):
    """Detection must work through the path users actually configure.

    The top-level ``supported_languages`` must include ``de``: it defaults to
    ``["en"]`` and would silently filter this German-only recognizer out.
    """
    registry = _load_registry_from_yaml(tmp_path)

    assert [type(r).__name__ for r in registry.recognizers] == ["AtSvnrRecognizer"]
    loaded = registry.recognizers[0]
    # YAML loading and direct construction build the same recognizer.
    assert loaded.supported_language == recognizer.supported_language == "de"
    assert loaded.supported_entities == recognizer.supported_entities
    assert loaded.context == recognizer.context
    assert [(p.name, p.regex, p.score) for p in loaded.patterns] == [
        (p.name, p.regex, p.score) for p in recognizer.patterns
    ]

    results = _analyze_de(registry, "SVNR: 2603 310605")

    assert [(r.entity_type, r.start, r.end) for r in results] == [("AT_SVNR", 6, 17)]
    assert results[0].score == pytest.approx(SPACED_WITH_CONTEXT_SCORE)


@pytest.mark.parametrize(
    "text, expected_start, expected_end, expected_score",
    [
        ("SVNR: 2603 310605", 6, 17, SPACED_WITH_CONTEXT_SCORE),
        ("Kundennummer 4131300271", 13, 23, COMPACT_SCORE),
    ],
)
def test_when_added_via_add_recognizer_then_results_match_yaml_path(
    tmp_path, text, expected_start, expected_end, expected_score
):
    """``add_recognizer()`` and YAML loading must give the same results."""
    direct_registry = RecognizerRegistry(supported_languages=["de"])
    direct_registry.add_recognizer(AtSvnrRecognizer())

    direct = _analyze_de(direct_registry, text)
    from_yaml = _analyze_de(_load_registry_from_yaml(tmp_path), text)

    expected = [
        ("AT_SVNR", expected_start, expected_end, pytest.approx(expected_score))
    ]
    assert [(r.entity_type, r.start, r.end, r.score) for r in direct] == expected
    assert [(r.entity_type, r.start, r.end, r.score) for r in from_yaml] == expected


def test_when_built_with_loader_kwargs_then_they_are_applied():
    """The constructor accepts the kwargs the YAML loader passes."""
    custom = AtSvnrRecognizer(
        name="CustomAtSvnr",
        supported_entity="AT_SVNR",
        supported_language="de",
        context=["versicherungsnummer"],
    )

    assert custom.name == "CustomAtSvnr"
    assert custom.context == ["versicherungsnummer"]
    assert custom.patterns == AtSvnrRecognizer.PATTERNS
