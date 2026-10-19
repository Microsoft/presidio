import pytest

from presidio_analyzer import AnalyzerEngine
from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import VinRecognizer


@pytest.fixture(scope="module")
def recognizer():
    return VinRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["VIN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        ("Vehicle VIN is 1HGCM82633A004352", 1, ((15, 32),), ((1.0, 1.0),)),
        ("chassis number 1HGCM82633A004352 recorded", 1, ((15, 32),), ((1.0, 1.0),)),
        ("vin: 1hgcm82633a004352", 1, ((5, 22),), ((1.0, 1.0),)),
        ("The vehicle identification number is 1HGCM82633A004352", 1, ((37, 54),), ((1.0, 1.0),)),
        # European-style VIN with non-matching NA check digit keeps base score
        ("VIN WVWZZZ1KZAW123456 on file", 1, ((4, 21),), ((0.5, 0.5),)),
        # North American VIN with bad check digit is filtered out
        ("VIN 1HGCM82633A004353 on file", 0, (), ()),
        # Order-like NA token with invalid check digit must not be flagged
        ("Order 1HGCM82633A004353 confirmed", 0, (), ()),
        # Invalid cases
        ("Not a VIN: 1HGCM82633A00435", 0, (), ()),
        ("Invalid char I in 1IGCM82633A004352", 0, (), ()),
        ("Invalid char O in 1OGCM82633A004352", 0, (), ()),
        ("Invalid char Q in 1QGCM82633A004352", 0, (), ()),
        # fmt: on
    ],
)
def test_when_vin_in_text_then_detected(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


@pytest.mark.parametrize(
    "vin, expected",
    [
        ("1HGCM82633A004352", True),
        ("WVWZZZ1KZAW123456", None),
        ("1HGCM82633A004353", False),
        ("SHORT", False),
    ],
)
def test_validate_result(vin, expected, recognizer):
    assert recognizer.validate_result(vin) is expected


def test_vin_context_boosts_score(spacy_nlp_engine):
    """Context words near a VIN should raise confidence above the base pattern score."""
    analyzer_engine = AnalyzerEngine(nlp_engine=spacy_nlp_engine)
    vin = "WVWZZZ1KZAW123456"

    results_without_context = analyzer_engine.analyze(
        text=f"Reference {vin} on file",
        language="en",
        entities=["VIN"],
        ad_hoc_recognizers=[VinRecognizer()],
    )
    results_with_context = analyzer_engine.analyze(
        text=f"Vehicle identification number {vin} on file",
        language="en",
        entities=["VIN"],
        ad_hoc_recognizers=[VinRecognizer()],
    )

    assert len(results_without_context) == 1
    assert len(results_with_context) == 1
    assert results_without_context[0].score == 0.5
    assert results_with_context[0].score > results_without_context[0].score
