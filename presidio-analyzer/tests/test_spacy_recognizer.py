
import pytest
from spacy.tokens import Span, Doc
from spacy.util import get_lang_class

from presidio_analyzer.nlp_engine import NlpArtifacts, SpacyNlpEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def entities():
    return ["PERSON", "DATE_TIME"]


@pytest.fixture(scope="module")
def nlp_recognizer(nlp_recognizers):
    return nlp_recognizers["spacy"]


@pytest.fixture(scope="module")
def mock_nlp_artifacts():
    en_vocab=get_lang_class("en")().vocab
    doc = Doc(en_vocab, words=["My", "name", "is", "Mitchell"])
    doc.ents = [Span(doc, 2, 3, label="PERSON")]

    nlp_artifacts = NlpArtifacts(
            entities=doc.ents,
            tokens=doc,
            tokens_indices=[token.idx for token in doc],
            lemmas=[token.lemma_ for token in doc],
            nlp_engine=None,
            language="en",
            scores=[0.9 for _ in doc.ents],
        )
    return nlp_artifacts


def prepare_and_analyze(nlp, recognizer, text, ents):
    nlp_artifacts = nlp.process_text(text, "en")
    results = recognizer.analyze(text, ents, nlp_artifacts)
    return results


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, entity_num",
    [
        # fmt: off
        # Test PERSON entity
        ("my name is Dan", 1, ((11, 14),), 0),
        ("Dan Tailor", 1, ((0, 10),), 0),
        ("John Oliver is a comedian.", 1, ((0, 11),), 0),
        ("Richard Milhous Nixon", 1, ((0, 21),), 0),
        ("Richard M. Nixon", 1, ((0, 16),), 0),
        ("Dan Bar has a bank account.", 1, ((0, 7),), 0),
        ("Mr. Mayers", 1, ((4, 10),), 0),
        ("They call me Mr. Mayers", 1, ((17, 23),), 0),
        # Test DATE_TIME Entity
        ("1972", 1, ((0, 4),), 1),
        ("I bought my car in 1972", 1, ((19, 23),), 1),
        ("I bought my car in May", 1, ((19, 22),), 1),
        ("May 1st", 1, ((0, 7),), 1),
        ("May 1st, 1977", 1, ((0, 13),), 1),
        ("I bought my car on May 1st, 1977", 1, ((19, 32),), 1),
        # fmt: on
    ],
)
def test_when_using_spacy_then_all_spacy_result_found(
    text,
    expected_len,
    expected_positions,
    entity_num,
    spacy_nlp_engine,
    nlp_recognizer,
    entities,
    ner_strength,
    max_score,
):
    results = prepare_and_analyze(spacy_nlp_engine, nlp_recognizer, text, entities)
    assert len(results) == expected_len
    entity_to_check = entities[entity_num]
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result_within_score_range(
            res, entity_to_check, st_pos, fn_pos, ner_strength, max_score
        )


def test_when_person_in_text_then_person_full_name_complex_found(
    spacy_nlp_engine, nlp_recognizer, entities
):
    text = "William Bill Alexander"
    results = prepare_and_analyze(spacy_nlp_engine, nlp_recognizer, text, entities)

    assert len(results) > 0

    # check that most of the text is covered
    covered_text = ""
    for result in results:
        sl = slice(result.start, result.end)
        covered_text += text[sl]

    assert len(text) - len(covered_text) < 5


def test_analyze_no_nlp_artifacts():
    spacy_recognizer = SpacyRecognizer()
    res = spacy_recognizer.analyze(text="text", nlp_artifacts=None, entities=["PERSON"])
    assert len(res) == 0


def test_entity_not_returned_if_not_in_supported_entities(mock_nlp_artifacts):
    spacy_recognizer = SpacyRecognizer(supported_entities=["NRP"])

    res = spacy_recognizer.analyze(
        text="text", nlp_artifacts=mock_nlp_artifacts, entities=["DATE_TIME"]
    )
    assert len(res) == 0


def test_default_explanation_is_used_when_given(mock_nlp_artifacts):
    """A caller-supplied default_explanation must reach the results.

    Regression test: the constructor stored the value in
    ``self.default_explanation`` while ``analyze`` formatted the class constant
    ``self.DEFAULT_EXPLANATION``, so the argument was silently discarded.
    """
    spacy_recognizer = SpacyRecognizer(
        supported_entities=["PERSON"], default_explanation="custom {} reason"
    )

    res = spacy_recognizer.analyze(
        text="My name is Mitchell", nlp_artifacts=mock_nlp_artifacts, entities=["PERSON"]
    )

    assert len(res) == 1
    assert (
        res[0].analysis_explanation.textual_explanation
        == "custom PERSON reason"
    )


def test_default_explanation_falls_back_to_the_class_default(mock_nlp_artifacts):
    """Without the argument, the built-in wording must still be produced."""
    spacy_recognizer = SpacyRecognizer(supported_entities=["PERSON"])

    res = spacy_recognizer.analyze(
        text="My name is Mitchell", nlp_artifacts=mock_nlp_artifacts, entities=["PERSON"]
    )

    assert len(res) == 1
    assert (
        res[0].analysis_explanation.textual_explanation
        == SpacyRecognizer.DEFAULT_EXPLANATION.format("PERSON")
    )
