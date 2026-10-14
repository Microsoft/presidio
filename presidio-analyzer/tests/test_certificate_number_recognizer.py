from pathlib import Path

import pytest
import yaml

import presidio_analyzer
from presidio_analyzer import EntityRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from tests import assert_result
from presidio_analyzer.predefined_recognizers.country_specific.us import MedicalLicenseRecognizer


@pytest.fixture(scope="module")
def cc_recognizer():
    return MedicalLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["MEDICAL_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_scores, expected_res",
    [
        # fmt: off
        ("GL0285191 EU4488929", 2, (), ((0, 9),(10,19),),),
        ("K92993548", 1, (), ((0, 9),),),
        ("my certificate number is: BB1388568", 1, (), ((26,35),),),
        ("The DEA number is  BG8207031", 0, (), (),),
        ("123 456\n789", 0, (), (),),
        # Registrant-type letter followed by 9
        ("A91234563", 1, (), ((0, 9),),),
        # Delimited by punctuation
        ("DEA: BB1388568.", 1, (), ((5, 14),),),
        ("(BB1388568)", 1, (), ((1, 10),),),
        # Embedded in a longer alphanumeric token: not a DEA number
        ("XBB1388568", 0, (), (),),
        ("1BB1388568", 0, (), (),),
        ("BB13885681234", 0, (), (),),
        ("Invoice ORDERBB1388568 was paid", 0, (), (),),
        ("Claim ID CLM13885681234 received", 0, (), (),),
        ("A912345634", 0, (), (),),
        # fmt: on
    ],
)
def test_when_all_medical_licence_number_then_succeed(
    text,
    expected_len,
    expected_scores,
    expected_res,
    cc_recognizer,
    entities,
    max_score,
):
    results = cc_recognizer.analyze(text, entities)
    assert len(results) == expected_len
    for res, expected_score in zip(results, expected_scores):
        assert res.score == expected_score
    for res, (start, end) in zip(results, expected_res):
        assert_result(res, entities[0], start, end, max_score)


def test_loads_from_default_recognizers_yaml_and_ignores_embedded_values():
    """The shipped YAML entry loads and only matches standalone values."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entries = [r for r in recognizers if r.get("name") == "MedicalLicenseRecognizer"]
    assert len(entries) == 1, "MedicalLicenseRecognizer missing from YAML"
    entry = entries[0]
    assert entry["country_code"] == "us"

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == [
        "MedicalLicenseRecognizer"
    ]
    recognizer = registry.recognizers[0]

    text = "Order ORDERBB1388568, prescriber DEA BB1388568"
    results = recognizer.analyze(text, ["MEDICAL_LICENSE"])

    assert [(r.start, r.end) for r in results] == [(37, 46)]
    assert results[0].entity_type == "MEDICAL_LICENSE"
    assert results[0].score == pytest.approx(EntityRecognizer.MAX_SCORE)
