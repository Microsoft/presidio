"""Tests adapted from the spacy_stanza repo"""

import warnings

from spacy.lang.en import EnglishDefaults


import pytest

from presidio_analyzer.nlp_engine.stanza_nlp_engine import (
    MultiWordTokenSurface,
    StanzaTokenizer,
    load_pipeline,
)


def tags_equal(act, exp):
    """Check if each actual tag in act is equal to one or more expected tags in exp."""
    return all(a == e if isinstance(e, str) else a in e for a, e in zip(act, exp))


@pytest.fixture(scope="module")
def stanza_pipeline():
    pytest.importorskip("stanza")
    import stanza

    lang = "en"
    stanza.download(lang)
    nlp = load_pipeline(lang)
    return nlp


@pytest.mark.skip_engine("stanza_en")
def test_spacy_stanza_english(stanza_pipeline):
    nlp = stanza_pipeline
    assert nlp.Defaults == EnglishDefaults
    lang = "en"
    doc = nlp("Hello world! This is a test.")

    # Expected POS tags. Note: Different versions of stanza result in different
    # POS tags.
    # fmt: off
    pos_exp = ["INTJ", "NOUN", "PUNCT", ("DET", "PRON"), ("VERB", "AUX"), "DET", "NOUN", "PUNCT"]

    assert [t.text for t in doc] == ["Hello", "world", "!", "This", "is", "a", "test", "."]
    assert [t.lemma_ for t in doc] == ["hello", "world", "!", "this", "be", "a", "test", "."]
    assert tags_equal([t.pos_ for t in doc], pos_exp)

    assert [t.is_sent_start for t in doc] == [True, False, False, True, False, False, False, False]
    assert any([t.is_stop for t in doc])
    # fmt: on
    assert len(list(doc.sents)) == 2
    assert doc.has_annotation("TAG")
    assert doc.has_annotation("SENT_START")

    docs = list(nlp.pipe(["Hello world", "This is a test"]))
    assert docs[0].text == "Hello world"
    assert docs[1].text == "This is a test"
    assert tags_equal([t.pos_ for t in docs[1]], pos_exp[3:-1])
    assert doc.ents == tuple()

    # Test NER
    doc = nlp("Barack Obama was born in Hawaii.")
    assert len(doc.ents) == 2
    assert doc.ents[0].text == "Barack Obama"
    assert doc.ents[0].label_ == "PERSON"
    assert doc.ents[1].text == "Hawaii"
    assert doc.ents[1].label_ == "GPE"

    # Test whitespace alignment
    doc = nlp(" Barack  Obama  was  born\n\nin Hawaii.\n")
    assert [t.pos_ for t in doc] == [
        "SPACE",
        "PROPN",
        "SPACE",
        "PROPN",
        "SPACE",
        "AUX",
        "SPACE",
        "VERB",
        "SPACE",
        "ADP",
        "PROPN",
        "PUNCT",
        "SPACE",
    ]
    assert [t.dep_ for t in doc] == [
        "",
        "nsubj:pass",
        "",
        "flat",
        "",
        "aux:pass",
        "",
        "root",
        "",
        "case",
        "root",
        "punct",
        "",
    ]
    assert [t.head.i for t in doc] == [0, 7, 2, 1, 4, 7, 6, 7, 8, 10, 10, 10, 12]
    assert len(doc.ents) == 2
    assert doc.ents[0].text == "Barack  Obama"
    assert doc.ents[0].label_ == "PERSON"
    assert doc.ents[1].text == "Hawaii"
    assert doc.ents[1].label_ == "GPE"

    # Test serialization
    reloaded_nlp = load_pipeline(lang).from_bytes(nlp.to_bytes())
    assert reloaded_nlp.config.to_str() == nlp.config.to_str()


class _FakeStanzaWord:
    def __init__(self, text, head, upos="X", deprel="dep"):
        self.text = text
        self.head = head
        self.upos = upos
        self.deprel = deprel


class _FakeStanzaToken:
    def __init__(self, words, text=None):
        self.words = words
        # A Stanza multi-word token's text is the surface form,
        # not the concatenation of the words it was expanded into
        self.text = text if text is not None else words[0].text


class _FakeStanzaSentence:
    def __init__(self, tokens):
        self.tokens = tokens


class _FakeStanzaDoc:
    def __init__(self, sentences):
        self.sentences = sentences


def test_get_tokens_with_heads_collapses_mwt_and_remaps_heads():
    """Test that mwt tokens are collapsed and dependency heads remapped.

    Covers languages whose Stanza pipeline has both the mwt and the parse
    processors (e.g. Spanish, French): heads of words around a collapsed
    multi-word token must point at the token that covers their governor.
    """
    sentence = _FakeStanzaSentence(
        [
            _FakeStanzaToken([_FakeStanzaWord("Ich", head=2)]),
            _FakeStanzaToken([_FakeStanzaWord("gehe", head=0)]),
            # "im" is expanded by the mwt processor into "in" + "dem"
            _FakeStanzaToken(
                [_FakeStanzaWord("in", head=5), _FakeStanzaWord("dem", head=3)],
                text="im",
            ),
            _FakeStanzaToken([_FakeStanzaWord("Schule", head=2)]),
        ]
    )
    second_sentence = _FakeStanzaSentence(
        [
            _FakeStanzaToken([_FakeStanzaWord("Sie", head=2)]),
            _FakeStanzaToken([_FakeStanzaWord("lacht", head=0)]),
        ]
    )
    snlp_doc = _FakeStanzaDoc([sentence, second_sentence])

    tokens, heads = StanzaTokenizer._StanzaTokenizer__get_tokens_with_heads(snlp_doc)

    # The multi-word token is collapsed into its surface form,
    # other tokens are flattened words as before
    assert [token.text for token in tokens] == [
        "Ich",
        "gehe",
        "im",
        "Schule",
        "Sie",
        "lacht",
    ]
    assert isinstance(tokens[2], MultiWordTokenSurface)
    # text and lemma are the surface form, other annotations come
    # from the first expanded word
    assert tokens[2].lemma == "im"
    assert tokens[2].upos == "X"

    # Relative heads: "Ich" -> "gehe", "gehe" is root, "im" -> "Schule",
    # "Schule" -> "gehe", and the second sentence's words are unaffected
    # by the words collapsed in the first one
    assert heads == [1, 0, 1, -2, 1, 0]


@pytest.mark.skip_engine("stanza_en")
def test_convert_doc_keeps_mwt_surface_text_offsets_and_entities():
    """Test _convert_doc on a real Stanza Document with a multi-word token.

    The Document is built from CoNLL-U with the real Stanza Token, Word
    and Span classes instead of running the German model, so it runs on
    every test run without a model download. The annotations are what the
    German pipeline produces for the text ("im" expanded into "in" + "dem").
    """
    from types import SimpleNamespace
    from spacy.vocab import Vocab
    from stanza.models.common.doc import Span
    from stanza.utils.conll import CoNLL

    text = "Wir treffen uns im Büro mit Thomas Bergmann."
    conllu = "\n".join(
        [
            "1\tWir\twir\tPRON\tPPER\t_\t2\tnsubj\t_\tstart_char=0|end_char=3",
            "2\ttreffen\ttreffen\tVERB\tVVFIN\t_\t0\troot\t_\tstart_char=4|end_char=11",
            "3\tuns\tuns\tPRON\tPRF\t_\t2\tobj\t_\tstart_char=12|end_char=15",
            "4-5\tim\t_\t_\t_\t_\t_\t_\t_\tstart_char=16|end_char=18",
            "4\tin\tin\tADP\tAPPR\t_\t6\tcase\t_\t_",
            "5\tdem\tder\tDET\tART\t_\t6\tdet\t_\t_",
            "6\tBüro\tBüro\tNOUN\tNN\t_\t2\tobl\t_\tstart_char=19|end_char=23",
            "7\tmit\tmit\tADP\tAPPR\t_\t8\tcase\t_\tstart_char=24|end_char=27",
            "8\tThomas\tThomas\tPROPN\tNE\t_\t2\tobl\t_\tstart_char=28|end_char=34",
            "9\tBergmann\tBergmann\tPROPN\tNE\t_\t8\tflat\t_\tstart_char=35|end_char=43",
            "10\t.\t.\tPUNCT\t$.\t_\t2\tpunct\t_\tstart_char=43|end_char=44",
            "",
        ]
    )
    snlp_doc = CoNLL.conll2doc(input_str=conllu)
    snlp_doc.text = text
    sentence = snlp_doc.sentences[0]
    snlp_doc.entities = [
        Span(tokens=sentence.tokens[6:8], type="PER", doc=snlp_doc, sent=sentence)
    ]
    tokenizer = StanzaTokenizer(SimpleNamespace(processors={}), Vocab())
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = tokenizer._convert_doc(snlp_doc)

    assert doc.text == text
    assert not [w for w in caught if "multi-word token" in str(w.message)]
    assert [t.text for t in doc] == [
        "Wir",
        "treffen",
        "uns",
        "im",
        "Büro",
        "mit",
        "Thomas",
        "Bergmann",
        ".",
    ]
    for token in doc:
        assert doc.text[token.idx : token.idx + len(token.text)] == token.text

    # the collapsed token keeps its surface form as lemma and borrows
    # the annotations of the first expanded word
    assert doc[3].lemma_ == "im"
    assert doc[3].pos_ == "ADP"

    # dependency heads around the collapsed token point at the right tokens:
    # "im" -> "Büro", "Büro" -> "treffen", "Bergmann" -> "Thomas"
    assert [t.head.i for t in doc] == [1, 1, 1, 4, 1, 6, 1, 6, 1]

    # NER entities keep the character offsets of the original text
    assert [(e.text, e.start_char, e.end_char, e.label_) for e in doc.ents] == [
        ("Thomas Bergmann", 28, 43, "PER")
    ]
