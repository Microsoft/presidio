import time
from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import PlNipRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

# The valid NIPs below are made-up digits completed with their check digit,
# not values from a register: 1234563218 is 123456321 and its check digit 8.
HYPHENS = 0.3
DIGITS = 0.05
# LemmaContextAwareEnhancer defaults: a context word adds 0.35, to at least 0.4
HYPHENS_WITH_CONTEXT = 0.65
DIGITS_WITH_CONTEXT = 0.4


@pytest.fixture(scope="module")
def recognizer():
    return PlNipRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["PL_NIP"]


def shipped_entry():
    """Return the PlNipRecognizer entry of ``default_recognizers.yaml``."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "PlNipRecognizer"]
    assert len(entries) == 1
    return entries[0]


def load_registry(recognizer_conf, language):
    return RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": [language],
            "recognizers": [recognizer_conf],
        }
    ).create_recognizer_registry()


@pytest.mark.parametrize(
    "text, expected",
    [
        # Valid: 10 digits, and both hyphen groupings
        ("1234563218", [(0, 10, DIGITS)]),
        ("1020304057", [(0, 10, DIGITS)]),
        ("9876543210", [(0, 10, DIGITS)]),
        ("123-456-32-18", [(0, 13, HYPHENS)]),
        ("123-45-63-218", [(0, 13, HYPHENS)]),
        ("555-444-33-34", [(0, 13, HYPHENS)]),
        # Valid: in Polish sentences
        ("Faktura dla firmy o NIP 1234563218 została wystawiona.", [(24, 34, DIGITS)]),
        (
            "Sprzedawca: Przykład sp. z o.o., NIP: 123-45-63-218, ul. Testowa 1",
            [(38, 51, HYPHENS)],
        ),
        (
            "NIP sprzedawcy 1234563218, NIP nabywcy 555-444-33-34",
            [(15, 25, DIGITS), (39, 52, HYPHENS)],
        ),
        # Valid: the VAT-EU prefix and a label glued to the number are not
        # part of the result
        ("Nabywca (VAT UE): PL1234563218", [(20, 30, DIGITS)]),
        ("NIP PL 123-456-32-18", [(7, 20, HYPHENS)]),
        ("NIP1234563218", [(3, 13, DIGITS)]),
        # Invalid: check digit off by one
        ("1234563217", []),
        ("123-456-32-19", []),
        # Invalid: the first 9 digits give a remainder of 10, so no check
        # digit completes them, including the placeholder 1234567890
        ("1234567890", []),
        ("1234567895", []),
        ("123-45-67-890", []),
        # Invalid: part of a longer number
        ("12345632180", []),
        ("91234563218", []),
        ("123456321812", []),
        ("1123-456-32-18", []),
        ("123-456-32-181", []),
        # Lookalikes: a PESEL, a Polish IBAN and a mobile number
        ("44051401458", []),
        ("PL61109010140000071219812874", []),
        ("600-123-456", []),
        # Lookalike: a Unix timestamp that fails the checksum is dropped; one
        # in 11 passes and keeps the very weak score
        ("1700000000", []),
        ("1700000008", [(0, 10, DIGITS)]),
        # Not NIP layouts: other groupings, spaces, mixed separators
        ("1234-56-32-18", []),
        ("12-345-632-18", []),
        ("123-456-3218", []),
        ("123 456 32 18", []),
        ("123-456 32-18", []),
        # Non-ASCII digits: never part of a NIP, but still a neighbouring digit
        ("\uff11\uff12\uff13\uff14\uff15\uff16\uff13\uff12\uff11\uff18", []),
        ("\u06631234563218", []),
    ],
)
def test_when_nip_in_text_then_exact_spans_and_scores(
    text, expected, recognizer, entities
):
    results = sorted(recognizer.analyze(text, entities), key=lambda r: r.start)

    assert [(r.start, r.end) for r in results] == [(s, e) for s, e, _ in expected]
    assert [r.score for r in results] == [pytest.approx(s) for *_, s in expected]
    assert all(r.entity_type == "PL_NIP" for r in results)


@pytest.mark.parametrize(
    "nip, invalid",
    [
        # Worked example of the European TIN Portal sheet for Poland
        ("2234567895", False),
        ("1234563218", False),
        ("123-456-32-18", False),
        ("123-45-63-218", False),
        ("1000000006", False),
        ("2234567894", True),
        # All ten candidates for a 9-digit prefix with remainder 10 fail
        *[(f"123456789{d}", True) for d in range(10)],
        # Wrong length
        ("123456321", True),
        ("12345632180", True),
        ("", True),
    ],
)
def test_invalidate_result_checks_length_and_checksum(nip, invalid, recognizer):
    assert recognizer.invalidate_result(nip) is invalid


def test_when_long_digit_groups_then_no_match_quickly(recognizer, entities):
    """A long adversarial input is handled without backtracking blow-up."""
    start = time.perf_counter()

    results = recognizer.analyze("123-" * 50_000 + "1" * 50_000, entities)

    assert results == []
    assert time.perf_counter() - start < 5


def test_when_shipped_entry_enabled_then_polish_analyzer_detects_nip():
    """The shipped entry must load and detect once a user enables it.

    The top-level ``supported_languages`` defaults to ``["en"]`` and would
    silently filter out this ``pl``-only recognizer, so it is set to ``pl``.
    CI has no Polish spaCy model; the no-op NLP engine stands in for it, so
    context can only come from the ``context`` argument here.
    """
    entry = shipped_entry()
    assert entry["enabled"] is False
    assert entry["country_code"] == "pl"
    assert entry["supported_languages"] == ["pl"]

    registry = load_registry(dict(entry, enabled=True), "pl")
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "pl", "model_name": "no_op"}]),
        supported_languages=["pl"],
    )
    text = "Sprzedawca: Przykład sp. z o.o., NIP: 123-45-63-218"

    results = analyzer.analyze(text, language="pl")
    boosted = analyzer.analyze(text, language="pl", context=["nip"])

    assert [(r.entity_type, r.start, r.end) for r in results] == [("PL_NIP", 38, 51)]
    assert results[0].score == pytest.approx(HYPHENS)
    assert boosted[0].score == pytest.approx(HYPHENS_WITH_CONTEXT)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        ("Numer 1234563218", DIGITS),
        ("NIP 1234563218", DIGITS_WITH_CONTEXT),
        ("NIP: 123-456-32-18", HYPHENS_WITH_CONTEXT),
        ("Numer identyfikacji podatkowej: 1234563218", DIGITS_WITH_CONTEXT),
        ("VAT UE: PL1234563218", DIGITS_WITH_CONTEXT),
        ("NIP1234563218", DIGITS_WITH_CONTEXT),
        # Context is looked up before the match only
        ("1234563218 to NIP", DIGITS),
    ],
)
def test_when_context_word_precedes_nip_then_score_is_raised(
    text, expected_score, spacy_nlp_engine
):
    """Context words in the text raise the score.

    Without a Polish spaCy model in CI, the recognizer is enabled for English
    through the YAML instead, which a user analyzing English documents that
    carry Polish NIPs would also do.
    """
    registry = load_registry(
        {
            "name": "PlNipRecognizer",
            "type": "predefined",
            "enabled": True,
            "country_code": "pl",
            "supported_languages": ["en"],
        },
        "en",
    )
    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=spacy_nlp_engine, supported_languages=["en"]
    )

    results = analyzer.analyze(text, language="en")

    assert [r.entity_type for r in results] == ["PL_NIP"]
    assert results[0].score == pytest.approx(expected_score)


def test_when_built_directly_then_same_as_yaml(recognizer):
    loaded = load_registry(dict(shipped_entry(), enabled=True), "pl").recognizers[0]

    assert type(loaded) is PlNipRecognizer
    assert loaded.supported_language == recognizer.supported_language == "pl"
    assert loaded.country_code() == recognizer.country_code() == "pl"
    assert loaded.supported_entities == recognizer.supported_entities == ["PL_NIP"]
    assert loaded.context == recognizer.context
    assert [p.to_dict() for p in loaded.patterns] == [
        p.to_dict() for p in recognizer.patterns
    ]


def test_when_context_is_empty_list_then_context_is_disabled():
    assert PlNipRecognizer(context=[]).context == []
    assert PlNipRecognizer(context=None).context == PlNipRecognizer.CONTEXT
