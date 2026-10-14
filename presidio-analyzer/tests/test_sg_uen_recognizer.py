import pytest

from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import SgUenRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result
from tests.mocks import NlpEngineMock


@pytest.fixture(scope="module")
def recognizer():
    return SgUenRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["SG_UEN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        ## Medium match
        # Test with valid UEN Format A
        ("53125226D", 1, [(0, 9)],),
        # Test with valid UEN Format B
        ("201434292D", 1, [(0, 10)],),
        # # Test with valid UEN Format C starting with T
        ("T16RF0037C", 1, [(0, 10)],),
        # # Test with valid UEN Format C starting with S
        ("S57TU0392K", 1, [(0, 10)],),
        # # Test with valid UEN Format C starting with R
        ("R16RF0037F", 1, [(0, 10)],),
        # Test with multiple valid UENs
        ("53125226D 201434292D S57TU0392K", 3, [(0, 9), (10, 20), (21, 31)],),
        # Test with valid UEN in a sentence
        ("UEN 53125226D was processed", 1, [(4, 13)],),
        # Lower-case UENs must still validate; the prefix, entity-type and
        # check letters are upper-cased before the checksum. Format A and C:
        ("53125226d", 1, [(0, 9)],),
        ("t16rf0037c", 1, [(0, 10)],),

        ## No match
        # Test with invalid length
        ("53125226", 0, (),),
        # Test with empty string
        ("", 0, (),),
        # fmt: on
    ],
)
def test_when_all_sg_uens_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


def test_when_format_c_uen_has_non_ascii_digit_then_no_result_and_no_error(
    recognizer, entities
):
    """A fullwidth digit matches the pattern but has no checksum value."""
    assert recognizer.analyze("T\uff186RF0037C", entities) == []


def test_when_enabled_in_configuration_then_non_ascii_digit_does_not_stop_analysis():
    """Loaded from configuration, the UEN after the malformed one is still found."""
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "SgUenRecognizer",
                    "type": "predefined",
                    "supported_languages": ["en"],
                    "enabled": True,
                    "country_code": "sg",
                }
            ],
        }
    ).create_recognizer_registry()
    analyzer = AnalyzerEngine(registry=registry, nlp_engine=NlpEngineMock())

    results = analyzer.analyze("UEN T\uff186RF0037C or T16RF0037C", language="en")

    assert [(r.entity_type, r.start, r.score) for r in results] == [("SG_UEN", 18, 1.0)]
