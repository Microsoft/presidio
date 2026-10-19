from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from tests import assert_result_within_score_range
from presidio_analyzer.predefined_recognizers import UsMbiRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider


@pytest.fixture(scope="module")
def recognizer():
    return UsMbiRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_MBI"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        # Valid MBI with dashes (medium match) - example from CMS documentation
        ("1EG4-TE5-MK73", 1, ((0, 13),), ((0.5, 0.6),),),
        # Valid MBI without dashes (weak match)
        ("1EG4TE5MK73", 1, ((0, 11),), ((0.3, 0.4),),),
        # Multiple MBIs in text
        (
            "Patient 1EG4-TE5-MK73 and 2AG9-XC4-NN22",
            2, ((8, 21), (26, 39),), ((0.5, 0.6), (0.5, 0.6),),
        ),
        # MBI with different valid characters
        ("9XX9-XX9-XX99", 1, ((0, 13),), ((0.5, 0.6),),),
        # Valid MBI in context
        ("Medicare ID: 3CD5-FG7-HJ89", 1, ((13, 26),), ((0.5, 0.6),),),
        # MBI without dashes surrounded by text
        (
            "The MBI is 4EF6GH8JK12 for this patient",
            1, ((11, 22),), ((0.3, 0.4),),
        ),
        # No match - contains excluded letter S in position 2
        ("1SG4-TE5-MK73", 0, (), (),),
        # No match - contains excluded letter L in position 5
        ("1EG4-LE5-MK73", 0, (), (),),
        # No match - contains excluded letter O in position 8
        ("1EG4-TE5-OK73", 0, (), (),),
        # No match - contains excluded letter I in position 9
        ("1EG4-TE5-MI73", 0, (), (),),
        # No match - contains excluded letter B in position 2
        ("1BG4-TE5-MK73", 0, (), (),),
        # No match - contains excluded letter Z in position 5
        ("1EG4-ZE5-MK73", 0, (), (),),
        # No match - letter in position 1 (should be number)
        ("AEG4-TE5-MK73", 0, (), (),),
        # No match - 0 in position 1 (CMS: position 1 is numeric 1 thru 9)
        ("0EG4-TE5-MK73", 0, (), (),),
        ("0EG4TE5MK73", 0, (), (),),
        ("Medicare ID: 0EG4-TE5-MK73", 0, (), (),),
        # No match - number in position 2 (should be letter)
        ("12G4-TE5-MK73", 0, (), (),),
        # No match - too short
        ("1EG4TE5MK7", 0, (), (),),
        # No match - too long
        ("1EG4TE5MK734", 0, (), (),),
        # Lowercase matches (presidio uses case-insensitive matching by default)
        ("1eg4-te5-mk73", 1, ((0, 13),), ((0.5, 0.6),),),
        # fmt: on
    ],
)
def test_when_mbi_in_text_then_all_us_mbis_are_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    results = recognizer.analyze(text, entities)
    results = sorted(results, key=lambda x: x.start)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos), (st_score, fn_score) in zip(
        results, expected_positions, expected_score_ranges
    ):
        if fn_score == "max":
            fn_score = max_score
        assert_result_within_score_range(
            res, entities[0], st_pos, fn_pos, st_score, fn_score
        )


def test_mbi_recognizer_supported_entity(recognizer):
    """Test that recognizer supports the correct entity."""
    assert recognizer.supported_entities == ["US_MBI"]


def test_mbi_recognizer_supported_language(recognizer):
    """Test that recognizer supports English by default."""
    assert recognizer.supported_language == "en"


def test_mbi_recognizer_context_words(recognizer):
    """Test that recognizer has appropriate context words."""
    expected_context = [
        "medicare", "mbi", "beneficiary", "cms", "medicaid", "hic", "hicn"
    ]
    assert recognizer.context == expected_context


def test_loads_from_default_recognizers_yaml_and_rejects_leading_zero():
    """The shipped YAML entry loads and rejects a 0 in position 1."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "UsMbiRecognizer"]
    assert len(entries) == 1, "UsMbiRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "us"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["UsMbiRecognizer"]
    recognizer = registry.recognizers[0]

    text = "Old ID 0EG4-TE5-MK73, current MBI 1EG4-TE5-MK73"
    results = recognizer.analyze(text, ["US_MBI"])

    assert [(r.start, r.end) for r in results] == [(34, 47)]
    assert results[0].entity_type == "US_MBI"
    assert results[0].score == pytest.approx(0.5)
