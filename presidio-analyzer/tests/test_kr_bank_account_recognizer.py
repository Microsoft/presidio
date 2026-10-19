from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers.country_specific.korea import (
    KrBankAccountRecognizer,
)
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return KrBankAccountRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["KR_BANK_ACCOUNT"]


# Patterns overlap by design (an NH account also matches the generic layouts),
# so positive cases assert on the best-scoring match instead of result counts.
@pytest.mark.parametrize(
    "text, start, end, score",
    [
        # NH (NongHyup) 302-prefixed 4-segment personal account
        ("302-1234-5678-91", 0, 16, 0.6),
        ("이체 계좌: 302-0123-4567-89", 7, 23, 0.6),
        # Common hyphenated 3-segment layouts
        ("110-234-567890", 0, 14, 0.3),
        ("457-910-012345", 0, 14, 0.3),
        # KB Kookmin / Korea Post 6-2-6 layout
        ("123456-78-901234", 0, 16, 0.3),
        # Mixed/plain digit runs (9-16 digits, excluding the 13-digit RRN shape)
        ("987654321012", 0, 12, 0.15),
        ("1002-123-456789", 0, 15, 0.15),
    ],
)
def test_when_account_like_then_best_match_found(
    text, start, end, score, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert results
    best = max(results, key=lambda r: r.score)
    assert_result_within_score_range(best, entities[0], start, end, score, score)


@pytest.mark.parametrize(
    "text",
    [
        # Korean mobile / VoIP phone numbers must not match
        "010-1234-5678",
        "070-1234-5678",
        "01012345678",
        "07012345678",
        "018-123-4567",
        # Landline, safe-number (050X) and toll-free phone numbers
        "02-1234-5678",
        "031-123-4567",
        "0212345678",
        "0504-1234-5678",
        "080-123-4567",
        # Resident registration number shapes must not match
        "960121-1234567",
        "9601211234567",
        # Any 13-digit pure run is left to KR_RRN's domain
        "9876543210123",
        # Business registration number shape is left to KR_BRN
        "123-45-67890",
        # Dates must not match
        "2024-03-10",
        # Part of a longer hyphenated number, e.g. a card number
        "1234-5678-9012-3456",
        # Too short
        "45000",
        "12345678",
    ],
)
def test_when_look_alike_then_no_match(text, recognizer, entities):
    assert recognizer.analyze(text, entities) == []


@pytest.mark.parametrize(
    "text",
    [
        # IBK 3-6-2-3 and NongHyup 351-prefixed 3-4-4-2 accounts
        "123-456789-01-234",
        "351-1234-5678-91",
        # KB Kookmin / Korea Post 6-2-6 account
        "123456-78-901234",
    ],
)
def test_when_account_has_more_segments_then_only_whole_number_matches(
    text, recognizer, entities
):
    results = recognizer.analyze(text, entities)
    assert {(r.start, r.end) for r in results} == {(0, len(text))}


NOOP_KO = {"lang_code": "ko", "model_name": "no_op"}


def shipped_yaml_entry():
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "KrBankAccountRecognizer"]
    assert len(entries) == 1, "KrBankAccountRecognizer missing from YAML"
    return entries[0]


def test_when_enabled_in_yaml_then_loads_and_detects_through_analyzer():
    """Detection must work through the path users actually configure.

    The shipped entry is enabled, loaded by ``RecognizerRegistryProvider`` and
    exercised through ``AnalyzerEngine`` so the language routing runs too. The
    generic loader test already proves the entry instantiates; this pins that
    the instance built from configuration detects with the same score as one
    built directly. ``NoOpNlpEngine`` stands in for a Korean NLP model.

    Note that ``ko`` has to be declared in three places for this to work: the
    registry's top-level ``supported_languages``, the NLP engine's models and
    the analyzer engine's ``supported_languages``. Missing any of them fails
    quietly or with an unrelated-looking error.
    """
    entry = shipped_yaml_entry()
    assert entry["supported_languages"] == ["ko"]
    assert entry["country_code"] == "kr"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["ko"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[NOOP_KO]),
        supported_languages=["ko"],
    )

    results = analyzer.analyze("이체 계좌: 302-0123-4567-89", language="ko")

    assert [r.entity_type for r in results] == ["KR_BANK_ACCOUNT"]
    assert_result_within_score_range(results[0], "KR_BANK_ACCOUNT", 7, 23, 0.6, 0.6)


def test_when_top_level_languages_left_at_default_then_entry_loads_nothing():
    """The shipped top-level ``supported_languages`` is ``["en"]``.

    Flipping only ``enabled: true`` therefore loads nothing, with no error,
    which is why enabling this entry also requires adding ``ko`` at the top.
    """
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(shipped_yaml_entry(), enabled=True)],
        }
    ).create_recognizer_registry()

    assert registry.recognizers == []


def test_when_korean_context_word_is_supplied_then_score_is_boosted(
    recognizer, entities
):
    """The Korean context words must be wired into the context enhancer.

    Context taken from the surrounding text needs a Korean NLP model, which
    the test environment does not ship, so the boost is exercised through the
    explicit ``context`` argument, the same way ``test_context_support`` does.
    """
    text = "302-1234-5678-91"
    engine = NoOpNlpEngine(models=[NOOP_KO])
    engine.load()
    nlp_artifacts = engine.process_text(text, "ko")
    raw = recognizer.analyze(text, entities, nlp_artifacts)
    enhancer = LemmaContextAwareEnhancer()

    without = enhancer.enhance_using_context(text, raw, nlp_artifacts, [recognizer])
    boosted = enhancer.enhance_using_context(
        text, raw, nlp_artifacts, [recognizer], ["계좌번호"]
    )

    assert max(r.score for r in without) == 0.6
    best = max(boosted, key=lambda r: r.score)
    assert best.score == pytest.approx(0.95)
    assert best.analysis_explanation.supportive_context_word in recognizer.context


@pytest.mark.parametrize(
    "text, start, end",
    [
        # context word before the account: the default prefix window
        ("계좌번호 302-1234-5678-91 로 입금", 5, 21),
        # context word after the account: the suffix window, off by default
        ("302-1234-5678-91 계좌로 이체 부탁드립니다", 0, 16),
    ],
)
def test_when_context_word_on_either_side_then_pattern_match_is_kept(
    text, start, end, recognizer, entities
):
    """Context text on either side must not disturb the pattern match itself."""
    results = recognizer.analyze(text, entities)
    best = max(results, key=lambda r: r.score)
    assert_result_within_score_range(best, entities[0], start, end, 0.6, 0.6)
