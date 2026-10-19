"""Tests for per-entity-type context words (issue #1711).

A recognizer supporting multiple entities can define its context words as a
dict mapping each entity type to its own list of words, so that context
words for one entity do not boost detections of another entity from the
same recognizer. A flat list keeps the previous shared behavior.
"""

import pytest

from presidio_analyzer import (
    AnalysisExplanation,
    EntityRecognizer,
    RecognizerResult,
)
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


class TwoEntityTestRecognizer(EntityRecognizer):
    """Test recognizer supporting two entities with low pattern scores."""

    def __init__(self, context=None):
        super().__init__(
            supported_entities=["FAKE_ACCOUNT", "FAKE_ITIN"],
            name="TwoEntityTestRecognizer",
            supported_language="en",
            context=context,
        )

    def load(self):  # noqa: D102
        pass

    def analyze(self, text, entities, nlp_artifacts=None):
        results = []
        for token, entity_type in (
            ("ACC999", "FAKE_ACCOUNT"),
            ("TXN888", "FAKE_ITIN"),
        ):
            start = text.find(token)
            if start >= 0 and entity_type in entities:
                results.append(
                    RecognizerResult(
                        entity_type=entity_type,
                        start=start,
                        end=start + len(token),
                        score=0.3,
                        analysis_explanation=AnalysisExplanation(
                            recognizer=self.name, original_score=0.3
                        ),
                        recognition_metadata={
                            RecognizerResult.RECOGNIZER_IDENTIFIER_KEY: self.id
                        },
                    )
                )
        return results


@pytest.fixture(scope="module")
def per_entity_recognizer():
    return TwoEntityTestRecognizer(
        context={
            "FAKE_ACCOUNT": ["account", "bank"],
            "FAKE_ITIN": ["tax", "itin"],
        }
    )


@pytest.fixture(scope="module")
def lemma_enhancer():
    return LemmaContextAwareEnhancer()


def test_context_words_selected_per_entity_type():
    """Dict context returns only the words registered for the entity type."""
    context = {"A": ["word1"], "B": ["word2"]}
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(context, "A") == [
        "word1"
    ]
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(context, "B") == [
        "word2"
    ]
    # entity type with no entry gets no context words
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(context, "C") == []


def test_flat_context_list_shared_by_all_entities():
    """A flat list keeps the previous behavior for every entity type."""
    context = ["word1", "word2"]
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(context, "A") == [
        "word1",
        "word2",
    ]
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(context, "B") == [
        "word1",
        "word2",
    ]
    assert LemmaContextAwareEnhancer._get_context_words_for_entity(None, "A") == []


def test_invalid_context_raises():
    """Malformed context configurations fail fast at construction time."""
    with pytest.raises(TypeError):
        TwoEntityTestRecognizer(context=123)
    with pytest.raises(ValueError):
        TwoEntityTestRecognizer(context=["ok", 123])
    with pytest.raises(ValueError):
        TwoEntityTestRecognizer(context={"": ["word"]})
    with pytest.raises(ValueError):
        TwoEntityTestRecognizer(context={"FAKE_ACCOUNT": "notalist"})


def test_no_context_defaults_to_empty_list():
    assert TwoEntityTestRecognizer().context == []


def test_matching_entity_boosted_with_per_entity_context(
    spacy_nlp_engine, lemma_enhancer, per_entity_recognizer
):
    """Context words for FAKE_ACCOUNT boost a FAKE_ACCOUNT result (issue #1711).

    Fails on the old code: it iterated the dict keys (entity type names),
    which never match surrounding words, so no boost ever happened.
    """
    text = "Please verify your bank account for ACC999 today"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = per_entity_recognizer.analyze(
        text, ["FAKE_ACCOUNT", "FAKE_ITIN"], nlp_artifacts
    )
    assert len(results) == 1

    enhanced = lemma_enhancer.enhance_using_context(
        text, results, nlp_artifacts, [per_entity_recognizer]
    )
    assert enhanced[0].score == pytest.approx(0.3 + 0.35)
    assert enhanced[0].analysis_explanation.supportive_context_word in (
        "account",
        "bank",
    )


def test_other_entity_not_boosted_by_unrelated_context_words(
    spacy_nlp_engine, lemma_enhancer, per_entity_recognizer
):
    """Words registered for FAKE_ACCOUNT must not boost a FAKE_ITIN result."""
    text = "Please verify your bank account for TXN888 today"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = per_entity_recognizer.analyze(
        text, ["FAKE_ACCOUNT", "FAKE_ITIN"], nlp_artifacts
    )
    assert len(results) == 1
    assert results[0].entity_type == "FAKE_ITIN"

    enhanced = lemma_enhancer.enhance_using_context(
        text, results, nlp_artifacts, [per_entity_recognizer]
    )
    # "bank"/"account" belong to FAKE_ACCOUNT; "tax"/"itin" are absent.
    assert enhanced[0].score == pytest.approx(0.3)


def test_other_entity_boosted_by_own_context_words(
    spacy_nlp_engine, lemma_enhancer, per_entity_recognizer
):
    """Each entity is boosted only by its own registered words."""
    text = "Please submit the tax form with TXN888 today"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = per_entity_recognizer.analyze(
        text, ["FAKE_ACCOUNT", "FAKE_ITIN"], nlp_artifacts
    )
    assert len(results) == 1

    enhanced = lemma_enhancer.enhance_using_context(
        text, results, nlp_artifacts, [per_entity_recognizer]
    )
    assert enhanced[0].score == pytest.approx(0.3 + 0.35)
    assert enhanced[0].analysis_explanation.supportive_context_word == "tax"


def test_yaml_config_with_per_entity_context_reaches_recognizer():
    """Configuration path: a dict context from YAML lands on the recognizer."""
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "PerEntityTitles",
                    "supported_entity": "TITLE",
                    "deny_list": ["Mr.", "Mrs."],
                    "context": {"TITLE": ["sir", "madam"]},
                }
            ],
        }
    )
    recognizer = provider.create_recognizer_registry().recognizers[0]
    assert recognizer.context == {"TITLE": ["sir", "madam"]}
