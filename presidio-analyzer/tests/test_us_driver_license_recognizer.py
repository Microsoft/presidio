import pytest
from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import UsLicenseRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Return the recognizer under test."""
    return UsLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the entity the recognizer detects."""
    return ["US_DRIVER_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # one letter, digits: the commonest state shape
        (
            "H12234567",
            1,
            ((0, 9),),
            ((0.3, 0.3),),
        ),
        (
            "A1234567",
            1,
            ((0, 8),),
            ((0.3, 0.3),),
        ),
        # two letters, digits
        (
            "AB12345",
            1,
            ((0, 7),),
            ((0.3, 0.3),),
        ),
        # digits-letters-digits (NH-style)
        (
            "12ABC12345",
            1,
            ((0, 10),),
            ((0.3, 0.3),),
        ),
        # digits then a letter
        (
            "123456789A",
            1,
            ((0, 10),),
            ((0.3, 0.3),),
        ),
        # a letter in the middle breaks the shape
        (
            "C12T345672",
            0,
            (),
            (),
        ),
        # bare digit runs only ever score very weakly
        (
            "123456789 1234567890 12345678901 123456789012 1234567890123",
            5,
            (
                (0, 9),
                (10, 20),
                (21, 32),
                (33, 45),
                (46, 59),
            ),
            (
                (0.0, 0.02),
                (0.0, 0.02),
                (0.0, 0.02),
                (0.0, 0.02),
                (0.0, 0.02),
            ),
        ),
        # letters only are never a licence
        (
            "ABCDEFG ABCDEFGH ABCDEFGHI",
            0,
            (),
            (),
        ),
        (
            "ABCD ABCDEFGHIJ",
            0,
            (),
            (),
        ),
        # fmt: on
    ],
)
def test_when_driver_licenses_in_text_then_all_us_driver_licenses_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Detect every licence-shaped token, and nothing else, at the right score."""
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "token",
    [
        # the examples from #1063
        "A1",
        "H1",
        "D3",
        "B43",
        # segment tags and qualifiers from delimited formats such as X12
        "N3",
        "D8",
        "J069",
        # what the former dead alternative 'A-Z]{2}[0-9]{2,5}' literally matched
        "A-Z]]12",
    ],
)
def test_short_or_malformed_tokens_are_not_driver_licenses(recognizer, entities, token):
    """Reject tokens shorter than any state's licence format.

    No US state issues a licence number shorter than five characters, so a
    letter followed by one to three digits is ordinary text. Before this, every
    such token scored 0.3, which is how "A1" and "D3" were flagged (#1063).
    """
    assert recognizer.analyze(token, entities) == []


def test_context_word_raises_the_score(recognizer, entities, spacy_nlp_engine):
    """A CONTEXT word before the value must lift it above the bare pattern."""
    registry = RecognizerRegistry()
    registry.add_recognizer(recognizer)
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)

    bare = analyzer.analyze(
        "Number A1234567 on file.", language="en", entities=entities
    )
    with_context = analyzer.analyze(
        "Driver license A1234567 on file.", language="en", entities=entities
    )

    assert len(bare) == 1 and len(with_context) == 1
    assert bare[0].score == pytest.approx(0.3)
    assert with_context[0].score > bare[0].score


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path, spacy_nlp_engine):
    """Detection must work through the path users actually configure."""
    conf = tmp_path / "recognizers.yaml"
    conf.write_text(
        """
supported_languages:
  - en
recognizers:
  - name: UsLicenseRecognizer
    supported_languages:
      - en
    type: predefined
    enabled: true
    country_code: us
"""
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)

    results = analyzer.analyze("Driver license A1234567", language="en")

    assert [result.entity_type for result in results] == ["US_DRIVER_LICENSE"]
    assert results[0].start == 15 and results[0].end == 23
    assert results[0].score > EntityRecognizer.MIN_SCORE
