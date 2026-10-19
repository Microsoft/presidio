"""Tests for the conversational prompt recognizer sample. Synthetic values only."""

import pytest
from conversational_prompt_recognizer import (
    ConversationalPromptRecognizer,
    luhn_valid,
    normalize_spoken_digits,
)
from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
from presidio_analyzer.nlp_engine import NoOpNlpEngine

# Synthetic numbers: a made-up card body with a computed Luhn check digit,
# and a structurally valid SSN that is not a published sample.
CARD = "4539148803436467"
SSN = "512437788"


@pytest.fixture(scope="module")
def analyzer():
    """Build an AnalyzerEngine with only this recognizer and no NLP model."""
    registry = RecognizerRegistry()
    registry.add_recognizer(ConversationalPromptRecognizer())
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "none"}]),
    )


def found(analyzer, transcript):
    """(entity, score, matched text) for each result, in order."""
    return [
        (r.entity_type, r.score, transcript[r.start : r.end])
        for r in sorted(
            analyzer.analyze(transcript, language="en"), key=lambda r: r.start
        )
    ]


def test_synthetic_values_are_what_they_claim():
    """The synthetic card passes Luhn; the Stugum-style bad entry does not."""
    assert luhn_valid(CARD)
    assert not luhn_valid("5555666677778888")


@pytest.mark.parametrize(
    "text, normalized",
    [
        ("four five three nine", "4539"),
        ("one oh double five triple two", "1055222"),
        ("oh, it's one two", "oh, it's 12"),
        ("5 1 2, 4 3, 7 7 8 8.", "512437788."),
        ("four five uh three nine", "4539"),
        ("512437788#", "512437788"),
        ("press # now", "press # now"),
    ],
)
def test_normalize_spoken_digits(text, normalized):
    """Spoken and keyed forms normalize to digits."""
    norm, mapping = normalize_spoken_digits(text)
    assert norm == normalized
    assert len(mapping) == len(norm)


def test_normalized_offsets_map_back_to_the_words():
    """A normalized span maps back to the spoken words."""
    text = "it's four five three nine"
    norm, mapping = normalize_spoken_digits(text)
    start = norm.index("4539")
    assert text[mapping[start][0] : mapping[start + 3][1]] == "four five three nine"


def test_keyed_ssn_after_an_ivr_prompt(analyzer):
    """Nine keyed digits after an SSN prompt are an SSN."""
    transcript = (
        "BOT: Please enter or say your nine digit Social Security number.\n"
        f"CUSTOMER: {SSN}#"
    )
    assert found(analyzer, transcript) == [("US_SSN", 0.85, SSN)]


def test_spoken_card_split_across_turns_with_a_backchannel(analyzer):
    """A card read over two turns, with "mm-hmm" between."""
    transcript = "\n".join(
        [
            "AGENT: Okay, what is the number on the card?",
            "CUSTOMER: four five three nine, one four eight eight,",
            "AGENT: mm-hmm",
            "CUSTOMER: oh three four three, six four six seven.",
        ]
    )
    assert found(analyzer, transcript) == [
        ("CREDIT_CARD", 0.85, "four five three nine, one four eight eight"),
        ("CREDIT_CARD", 0.85, "oh three four three, six four six seven"),
    ]


def test_an_answer_that_fails_its_check_is_still_flagged_with_a_low_score(analyzer):
    """A Luhn-failing card after a card prompt: flagged, low score."""
    transcript = (
        "BOT: Please enter your credit card number, then press pound.\n"
        "CUSTOMER: 5555666677778888#"
    )
    assert found(analyzer, transcript) == [("CREDIT_CARD", 0.3, "5555666677778888")]


def test_without_a_prompt_nothing_is_flagged(analyzer):
    """The same digits after another prompt are not flagged."""
    transcript = (
        f"BOT: Please enter your order number, then press pound.\nCUSTOMER: {SSN}#"
    )
    assert found(analyzer, transcript) == []


def test_a_prompt_applies_to_the_next_answer_only(analyzer):
    """A prompt is used up by the answer that follows it."""
    transcript = "\n".join(
        [
            "BOT: Please enter your nine digit Social Security number.",
            f"CUSTOMER: {SSN}#",
            "BOT: Thank you. How many tickets would you like?",
            "CUSTOMER: 123456789",
        ]
    )
    assert found(analyzer, transcript) == [("US_SSN", 0.85, SSN)]


def test_entities_filter(analyzer):
    """The entities argument is honored."""
    transcript = (
        f"BOT: Please enter your nine digit Social Security number.\nCUSTOMER: {SSN}#"
    )
    results = analyzer.analyze(transcript, language="en", entities=["CREDIT_CARD"])
    assert results == []


def test_explanation_says_why(analyzer):
    """The explanation names the prompt."""
    transcript = "BOT: What is your SSN?\nCUSTOMER: " + SSN
    [result] = analyzer.analyze(transcript, language="en", return_decision_process=True)
    assert "prompt for US_SSN" in result.analysis_explanation.textual_explanation
