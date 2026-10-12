"""
Tests for DeTaxIdRecognizer (Steueridentifikationsnummer).

All test numbers are fictitious/generated and do not represent real persons.
Valid numbers satisfy the BZSt digit-repetition rule (exactly one digit
repeated twice or three times in the first ten positions, no three-in-a-row)
and carry a check digit produced with the official ISO 7064 Mod 11, 10
algorithm as specified by the Bundeszentralamt für Steuern (§§ 139a–139e AO).
"""
from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import DeTaxIdRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from tests.mocks import NlpEngineMock


@pytest.fixture(scope="module")
def recognizer():
    return DeTaxIdRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["DE_TAX_ID"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Valid Steuer-IdNr – structure and checksum pass → result at MAX_SCORE
        ("39632801577", 1, ((0, 11),)),  # 3 appears twice
        ("95078563523", 1, ((0, 11),)),  # 5 appears three times, not adjacent
        ("Meine Steuer-ID: 39632801577.", 1, ((17, 28),)),
        ("IdNr. 95078563523 liegt vor.", 1, ((6, 17),)),
        # Invalid: wrong check digit
        ("39632801571", 0, ()),
        ("95078563520", 0, ()),
        # Invalid: leading zero (first digit must be 1–9)
        ("02345678901", 0, ()),
        # Invalid: too short / too long
        ("3963280157",  0, ()),
        ("396328015770", 0, ()),
        # Invalid: all ten leading digits are identical (excluded by spec)
        ("11111111111", 0, ()),
        # Invalid: a single digit appears 4+ times in positions 1-10
        ("11112345678", 0, ()),
        # Invalid structure despite a correct check digit – the cases the
        # digit-repetition rule exists to reject:
        # ten distinct digits (no digit repeated)
        ("12345678903", 0, ()),
        # two different digits repeated
        ("11223456785", 0, ()),
        # a digit repeated three times in three consecutive positions
        ("24567778917", 0, ()),
        # Lookalike negative: an 11-digit order number with a valid check digit
        # but ten distinct digits must not be flagged
        ("Bestellnummer 30598162475 wurde versandt.", 0, ()),
        # fmt: on
    ],
)
def test_when_all_de_tax_ids_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "number, expected",
    [
        # Valid numbers
        ("39632801577", True),  # one digit twice
        ("51894376235", True),  # one digit twice
        ("95078563523", True),  # one digit three times, not adjacent
        ("79715630877", True),  # one digit three times, not adjacent
        ("41372159010", True),  # check value 10 is written as digit 0
        ("86095742719", True),  # docstring example
        # Wrong check digit
        ("39632801571", False),
        ("95078563520", False),
        # Leading zero
        ("02345678903", False),
        # Non-numeric
        ("abcdefghijk", False),
        # Wrong length
        ("3963280157",  False),
        ("396328015770", False),
        # All same first 10 digits
        ("11111111111", False),
        # A digit repeated more than 3 times is invalid
        ("11112345678", False),
        ("12222234567", False),
        # Structure violations with a correct check digit
        ("12345678903", False),  # no digit repeated
        ("98765432106", False),  # no digit repeated
        ("11223456785", False),  # two different digits repeated
        ("11123456786", False),  # triple at positions 1-3
        ("24567778917", False),  # triple at positions 5-7
    ],
)
def test_when_de_tax_id_validated_then_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected


@pytest.mark.parametrize(
    "leading_digits, expected",
    [
        ("3963280157", True),   # one digit twice
        ("9507856352", True),   # one digit three times, positions 2, 6, 9
        ("7971563087", True),   # one digit three times, positions 1, 3, 10
        ("1234567890", False),  # ten distinct digits
        ("1122345678", False),  # two digits twice
        ("1112345678", False),  # three in a row at the start
        ("2456777891", False),  # three in a row in the middle
        ("1111234567", False),  # four times
        ("1111111111", False),  # all identical
    ],
)
def test_when_digit_repetition_checked_then_bzst_rule_is_applied(
    leading_digits, expected
):
    assert DeTaxIdRecognizer._has_valid_digit_repetition(leading_digits) == expected


def test_when_enabled_in_registry_yaml_then_loads_and_detects():
    """Detection must work through the path users actually configure.

    The shipped ``default_recognizers.yaml`` entry is loaded with
    ``enabled: true`` and the top-level ``supported_languages`` set to ``de``,
    then run through ``AnalyzerEngine``.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "DeTaxIdRecognizer"]
    assert len(entries) == 1, "DeTaxIdRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "de"
    assert entry["supported_languages"] == ["de"]

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["de"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["DeTaxIdRecognizer"]

    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=NlpEngineMock(), supported_languages=["de"]
    )

    results = analyzer.analyze("Steuer-ID 39632801577", language="de")
    assert len(results) == 1
    assert_result(results[0], "DE_TAX_ID", 10, 21, 1.0)

    # Ten distinct digits with a correct check digit are not a Steuer-IdNr
    assert analyzer.analyze("Steuer-ID 12345678903", language="de") == []
