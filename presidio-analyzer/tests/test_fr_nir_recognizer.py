"""
Tests for FrNirRecognizer (French NIR / numéro de sécurité sociale).

All test numbers are fictitious/generated and do not represent real persons.
Valid numbers carry a key computed as 97 - (N mod 97) over the 13-character
body, with 2A -> 19 and 2B -> 18 substituted for Corsican départements.
"""
from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.predefined_recognizers import FrNirRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from tests.mocks import NlpEngineMock


@pytest.fixture(scope="module")
def recognizer():
    return FrNirRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["FR_NIR"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions",
    [
        # fmt: off
        # Valid NIR – key matches → result at MAX_SCORE
        ("185057800608491", 1, ((0, 15),)),
        ("1 85 05 78 006 084 91", 1, ((0, 21),)),
        ("1850578006084 91", 1, ((0, 16),)),
        ("292117511500381", 1, ((0, 15),)),
        # Corsica: 2A / 2B substituted by 19 / 18 before the modulo
        ("174062A00401243", 1, ((0, 15),)),
        ("2 63 08 2B 022 007 56", 1, ((0, 21),)),
        ("174062a00401243", 1, ((0, 15),)),
        # Overseas département (97x) and born abroad (99)
        ("188079741100403", 1, ((0, 15),)),
        ("279019912345690", 1, ((0, 15),)),
        # Temporary registration codes for the sex digit
        ("301053401234504", 1, ((0, 15),)),
        ("499026911000102", 1, ((0, 15),)),
        ("755083312001051", 1, ((0, 15),)),
        ("861111304500231", 1, ((0, 15),)),
        # Unknown / incomplete month codes: 20, 13, 42, 50, 99
        ("165206912300167", 1, ((0, 15),)),
        ("270134400702112", 1, ((0, 15),)),
        ("158425901200392", 1, ((0, 15),)),
        ("290509904560009", 1, ((0, 15),)),
        ("133999999999931", 1, ((0, 15),)),
        # Key boundaries: 97 and 01
        ("237014646459597", 1, ((0, 15),)),
        ("103099494432201", 1, ((0, 15),)),
        # Embedded in text
        ("Numéro de sécurité sociale : 1 85 05 78 006 084 91.", 1, ((29, 50),)),
        ("NIR 292117511500381 (assuré)", 1, ((4, 19),)),
        ("185057800608491 et 292117511500381", 2, ((0, 15), (19, 34))),
        # Invalid: wrong key
        ("185057800608492", 0, ()),
        ("1 85 05 78 006 084 37", 0, ()),
        # Invalid: sex digit 0, 5, 6, 9
        ("085057800608491", 0, ()),
        ("585057800608491", 0, ()),
        ("685057800608491", 0, ()),
        ("985057800608491", 0, ()),
        # Invalid: month 00, 14 and 45 are not defined
        ("185007800608491", 0, ()),
        ("185147800608491", 0, ()),
        ("185457800608491", 0, ()),
        # Invalid: département 00 and 2C
        ("185050000608491", 0, ()),
        ("174062C00401243", 0, ()),
        # Invalid: 13-digit body without key, 14 and 16 digits
        ("1850578006084", 0, ()),
        ("18505780060849", 0, ()),
        ("1850578006084912", 0, ()),
        # Lookalike negative: a 15-digit order number failing the key
        ("Commande 185057800608400 expédiée", 0, ()),
        # fmt: on
    ],
)
def test_when_all_fr_nirs_then_succeed(
    text, expected_len, expected_positions, recognizer, entities, max_score
):
    results = recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, (st_pos, fn_pos) in zip(results, expected_positions):
        assert_result(res, entities[0], st_pos, fn_pos, max_score)


@pytest.mark.parametrize(
    "number, expected",
    [
        ("185057800608491", True),
        ("1 85 05 78 006 084 91", True),
        ("174062A00401243", True),
        ("174062a00401243", True),
        ("263082B02200756", True),
        ("237014646459597", True),  # key 97
        ("103099494432201", True),  # key 01
        ("185057800608492", False),
        ("174062B00401243", False),  # 2B body with the 2A key
        ("174062C00401243", False),
        ("1850578006084", False),
        ("1850578006084912", False),
        ("18505780060849A", False),
        ("abcdefghijklmno", False),
    ],
)
def test_when_fr_nir_validated_then_key_result_is_correct(
    number, expected, recognizer
):
    assert recognizer.validate_result(number) == expected


@pytest.mark.parametrize(
    "body, expected",
    [
        ("1850578006084", 91),
        ("2921175115003", 81),
        ("174062A004012", 43),
        ("263082B022007", 56),
        ("2370146464595", 97),
        ("1030994944322", 1),
        ("174062C004012", None),
        ("185057800608", None),
        ("18505780060849", None),
    ],
)
def test_when_key_computed_then_matches_spec(body, expected):
    assert FrNirRecognizer._compute_key(body) == expected


def test_when_name_passed_then_it_is_used():
    """Constructor must accept the ``name`` kwarg the YAML loader passes."""
    recognizer = FrNirRecognizer(name="CustomFrNir")
    assert recognizer.name == "CustomFrNir"
    assert recognizer.supported_language == "fr"
    assert recognizer.country_code() == "fr"


def test_when_enabled_in_registry_yaml_then_loads_and_detects():
    """Detection must work through the path users actually configure.

    The shipped ``default_recognizers.yaml`` entry is loaded with
    ``enabled: true`` and the top-level ``supported_languages`` set to ``fr``,
    then run through ``AnalyzerEngine``.
    """
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "FrNirRecognizer"]
    assert len(entries) == 1, "FrNirRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "fr"
    assert entry["supported_languages"] == ["fr"]
    assert entry["enabled"] is False

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["fr"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    assert [type(r).__name__ for r in registry.recognizers] == ["FrNirRecognizer"]

    analyzer = AnalyzerEngine(
        registry=registry, nlp_engine=NlpEngineMock(), supported_languages=["fr"]
    )

    results = analyzer.analyze("NIR : 1 85 05 78 006 084 91", language="fr")
    assert len(results) == 1
    assert_result(results[0], "FR_NIR", 6, 27, 1.0)

    assert analyzer.analyze("NIR : 1 85 05 78 006 084 37", language="fr") == []
