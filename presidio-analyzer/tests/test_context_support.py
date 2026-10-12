import os

import pytest

from presidio_analyzer import PatternRecognizer, Pattern
from presidio_analyzer.predefined_recognizers import (
    AbaRoutingRecognizer,
    # CreditCardRecognizer,
    PhoneRecognizer,
    # DomainRecognizer,
    UsItinRecognizer,
    UsLicenseRecognizer,
    UsBankRecognizer,
    UsPassportRecognizer,
    IpRecognizer,
    UsSsnRecognizer,
    SgFinRecognizer,
    InPanRecognizer,
    InPassportRecognizer,
    PhTinRecognizer,
)
from presidio_analyzer.nlp_engine import NlpArtifacts
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer


@pytest.fixture(scope="module")
def recognizers_map():
    rec_map = {
        "IP_ADDRESS": IpRecognizer(),
        "US_SSN": UsSsnRecognizer(),
        "PHONE_NUMBER": PhoneRecognizer(),
        "ABA_ROUTING_NUMBER": AbaRoutingRecognizer(),
        "US_ITIN": UsItinRecognizer(),
        "US_DRIVER_LICENSE": UsLicenseRecognizer(),
        "US_BANK_NUMBER": UsBankRecognizer(),
        "US_PASSPORT": UsPassportRecognizer(),
        "FIN": SgFinRecognizer(),
        "IN_PAN": InPanRecognizer(),
        "IN_PASSPORT": InPassportRecognizer(),
        "PH_TIN": PhTinRecognizer(),
    }
    return rec_map


@pytest.fixture(scope="module")
def recognizers_list(recognizers_map):
    rec_list = []
    for item in recognizers_map:
        rec_list.append(recognizers_map[item])
    return rec_list


@pytest.fixture(scope="module")
def dataset(recognizers_map):
    """Loads up a group of sentences with relevant context words and creates
    a list of tuples of the sentence, a recognizer and entity types.
    """

    data_path = os.path.dirname(__file__) + "/data/context_sentences_tests.txt"
    with open(data_path, "r") as f:
        # get non-empty lines without comments
        lines = [line.strip() for line in f if line[0] != "#" and line.strip()]

    test_items = []
    for i in range(0, len(lines), 2):
        entity_type = lines[i].strip()
        item = lines[i + 1].strip()
        recognizer = recognizers_map.get(entity_type, None)
        if not recognizer:
            # will fail the test in its turn
            raise ValueError(f"bad entity type {entity_type}")

        test_items.append((item, recognizer, [entity_type]))
    # Currently we have 36 sentences, this is a sanity check
    if not len(test_items) == 36:
        raise ValueError(f"expected 36 context sentences but found {len(test_items)}")

    yield test_items


@pytest.fixture(scope="module")
def lemma_context():
    return LemmaContextAwareEnhancer()


@pytest.fixture(scope="function")
def mock_nlp_artifacts():
    return NlpArtifacts([], [], [], [], None, "en")


@pytest.fixture(scope="module")
def us_license_recognizer():
    return UsLicenseRecognizer()


def test_when_text_with_aditional_context_lemma_based_context_enhancer_then_analysis_explanation_include_correct_supportive_context_word(  # noqa: E501
    spacy_nlp_engine, lemma_context, us_license_recognizer
):
    """This test checks that LemmaContextAwareEnhancer uses supportive context
    word from analyze input as if it was in the text itself.

    when passing a word which doesn't appear in the text but is defined as context in
    the recognizer which recognized this the recognized entity, the enhancer should
    return that word as supportive_context_word instead of other recognizer context word
    """
    text = "John Smith license is AC432223"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    recognizer_results = us_license_recognizer.analyze(text, nlp_artifacts)
    results_without_additional_context = lemma_context.enhance_using_context(
        text, recognizer_results, nlp_artifacts, [us_license_recognizer]
    )
    results_with_additional_context = lemma_context.enhance_using_context(
        text,
        recognizer_results,
        nlp_artifacts,
        [us_license_recognizer],
        ["Drivers license"],
    )

    assert (
        results_without_additional_context[
            0
        ].analysis_explanation.supportive_context_word
        == "license"
    )
    assert (
        results_with_additional_context[0].analysis_explanation.supportive_context_word
        == "driver"
    )


def test_when_text_with_only_additional_context_lemma_based_context_enhancer_then_analysis_explanation_include_correct_supportive_context_word(  # noqa: E501
    spacy_nlp_engine, lemma_context, us_license_recognizer
):
    """This test checks that LemmaContextAwareEnhancer uses supportive context
    word from analyze input as if it was in the text itself but no other words appear
    in text to support context enhancement.

    when passing a word which doesn't appear in the text but is defined as context in
    the recognizer which recognized this the recognized entity and there's no other
    word in the text tp support context, the enhancer should
    return that word as supportive_context_word and raise the score.
    """
    text = "John Smith D.R is AC432223"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    recognizer_results = us_license_recognizer.analyze(text, nlp_artifacts)
    results_without_additional_context = lemma_context.enhance_using_context(
        text, recognizer_results, nlp_artifacts, [us_license_recognizer]
    )
    results_with_additional_context = lemma_context.enhance_using_context(
        text,
        recognizer_results,
        nlp_artifacts,
        [us_license_recognizer],
        ["Driver license"],
    )

    assert results_without_additional_context[0].score == 0.3
    assert (
        results_without_additional_context[
            0
        ].analysis_explanation.supportive_context_word
        == ""
    )
    assert (
        results_with_additional_context[0].analysis_explanation.supportive_context_word
        == "driver"
    )
    assert results_with_additional_context[0].score == pytest.approx(0.65)


def test_when_text_with_context_then_improves_score(
    dataset, spacy_nlp_engine, mock_nlp_artifacts, lemma_context, recognizers_list
):
    for item in dataset:
        text, recognizer, entities = item
        nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
        results_without_context = recognizer.analyze(text, entities, mock_nlp_artifacts)
        results_with_context = recognizer.analyze(text, entities, nlp_artifacts)

        results_without_context = lemma_context.enhance_using_context(
            text, results_without_context, mock_nlp_artifacts, recognizers_list
        )
        results_with_context = lemma_context.enhance_using_context(
            text, results_with_context, nlp_artifacts, recognizers_list
        )

        assert len(results_without_context) == len(results_with_context)
        for res_wo, res_w in zip(results_without_context, results_with_context):
            if res_wo.score != 1.0:
                assert res_wo.score < res_w.score
            else:
                assert res_wo.score <= res_w.score


def test_when_context_custom_recognizer_then_succeed(spacy_nlp_engine, mock_nlp_artifacts):
    """This test checks that a custom recognizer is also enhanced by context.

    However this test also verifies a specific case in which the pattern also
    includes a preceeding space (' rocket'). This in turn cause for a misalignment
    between the tokens and the regex match (the token will be just 'rocket').
    This misalignment is handled in order to find the correct context window.
    """
    rocket_recognizer = PatternRecognizer(
        supported_entity="ROCKET",
        name="rocketrecognizer",
        context=["cool"],
        patterns=[Pattern("rocketpattern", r"\\s+(rocket)", 0.3)],
    )
    text = "hi, this is a cool ROCKET"
    recognizer = rocket_recognizer
    entities = ["ROCKET"]
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results_without_context = recognizer.analyze(text, entities, mock_nlp_artifacts)
    results_with_context = recognizer.analyze(text, entities, nlp_artifacts)
    assert len(results_without_context) == len(results_with_context)
    for res_wo, res_w in zip(results_without_context, results_with_context):
        assert res_wo.score < res_w.score
