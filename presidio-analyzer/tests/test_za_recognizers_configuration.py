"""South African recognizers loaded through the YAML configuration path.

Their validators only check the shape of a match. A well-formed match keeps its
pattern score and context raises it; nothing is promoted to 1.0.
"""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range

DEFAULT_RECOGNIZERS = yaml.safe_load(
    (
        Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    ).read_text(encoding="utf-8")
)["recognizers"]


def _analyzer(nlp_engine, *recognizer_names):
    """Enable the shipped default_recognizers.yaml entries, as a user would."""
    entries = [r for r in DEFAULT_RECOGNIZERS if r.get("name") in recognizer_names]
    assert len(entries) == len(recognizer_names)
    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [dict(entry, enabled=True) for entry in entries],
        }
    ).create_recognizer_registry()
    return AnalyzerEngine(
        registry=registry, nlp_engine=nlp_engine, supported_languages=["en"]
    )


@pytest.mark.parametrize(
    "recognizer_name, entity, value, context_word, score, score_with_context",
    [
        ("ZaPassportRecognizer", "ZA_PASSPORT", "M12345678", "passport", 0.2, 0.55),
        ("ZaTrafficRegisterNumberRecognizer", "ZA_TRAFFIC_REGISTER_NUMBER", "1234567890123", "eNaTIS", 0.05, 0.4),
        ("ZaDriverLicenseRecognizer", "ZA_DRIVER_LICENSE", "60390002CGBV", "licence", 0.3, 0.65),
        ("ZaLicensePlateRecognizer", "ZA_LICENSE_PLATE", "KD93GKGP", "registration", 0.3, 0.65),
        ("ZaLicensePlateRecognizer", "ZA_LICENSE_PLATE", "DK 28 LF GP", "registration", 0.3, 0.65),
        ("ZaLicensePlateRecognizer", "ZA_LICENSE_PLATE", "GET 103 WP", "registration", 0.3, 0.65),
        ("ZaLicensePlateRecognizer", "ZA_LICENSE_PLATE", "015 SBZ EC", "registration", 0.3, 0.65),
        ("ZaCompanyRegistrationRecognizer", "ZA_COMPANY_REGISTRATION", "2019/123456/07", "CIPC", 0.4, 0.75),
        ("ZaCompanyRegistrationRecognizer", "ZA_COMPANY_REGISTRATION", "CK2001/123456", "CIPC", 0.3, 0.65),
    ],
)  # fmt: skip
def test_well_formed_match_keeps_pattern_score_when_enabled_in_yaml(
    spacy_nlp_engine,
    recognizer_name,
    entity,
    value,
    context_word,
    score,
    score_with_context,
):
    analyzer = _analyzer(spacy_nlp_engine, recognizer_name)

    for text, expected_score in (
        (f"Item {value} is on file.", score),
        (f"{context_word} {value} is on file.", score_with_context),
    ):
        results = analyzer.analyze(text, language="en", entities=[entity])

        start = text.index(value)
        assert len(results) == 1
        assert_result_within_score_range(
            results[0],
            entity,
            start,
            start + len(value),
            expected_score,
            expected_score,
        )


@pytest.mark.parametrize(
    "recognizer_name, entity, value",
    [
        # A valid South African ID number is not a traffic register number.
        ("ZaTrafficRegisterNumberRecognizer", "ZA_TRAFFIC_REGISTER_NUMBER", "8001015009087"),
        # A licence number has at least one letter.
        ("ZaDriverLicenseRecognizer", "ZA_DRIVER_LICENSE", "123456789012"),
        # A registration year cannot be in the future.
        ("ZaCompanyRegistrationRecognizer", "ZA_COMPANY_REGISTRATION", "2099/123456/07"),
    ],
)  # fmt: skip
def test_rejected_shape_is_still_dropped_when_enabled_in_yaml(
    spacy_nlp_engine, recognizer_name, entity, value
):
    analyzer = _analyzer(spacy_nlp_engine, recognizer_name)

    assert analyzer.analyze(f"Item {value} is on file.", "en", entities=[entity]) == []
