import pytest
from presidio_analyzer.predefined_recognizers import UsLicenseRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return UsLicenseRecognizer()


@pytest.fixture(scope="module")
def entities():
    return ["US_DRIVER_LICENSE"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # fmt: off
        ("H12234567", 1, ((0, 9),), ((0.3, 0.4),),),
        ("C12T345672", 0, (), (),),
        # invalid license that should fail, but doesn't do to context
        # ("my driver's license is C12T345672", 0, (), (),),
        # Other states license very weak tests
        (
            "123456789 1234567890 12345679012 123456790123 1234567901234 1234",
            5,
            ((0, 9), (10, 20), (21, 32), (33, 45), (46, 59),),
            ((0.0, 0.02), (0.0, 0.02), (0.0, 0.02), (0.0, 0.02), (0.0, 0.02),),
        ),
        ("ABCDEFG ABCDEFGH ABCDEFGHI", 0, (), (),),
        ("ABCD ABCDEFGHIJ", 0, (), (),),
        # The following fails due to keyphrases not yet supported
        # ("my driver license: ABCDEFG", 1, ((19, 25),), ((0.5, 0.91),),),
        # fmt: on
    ],
)
def test_when_driver_licenes_in_text_then_all_us_driver_licenses_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
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
    "license_number",
    [
        "A1",
        "A12345678901234",
        "A123456789012345678",
        "AB12",
        "AB1234567",
        "A123456R",
        "AB123456C",
        "A1B2C",
        "12ABC12345",
        "123AB1234",
        "1234567A",
        "123456789A",
        "12345678AB",
    ],
)
def test_alphanumeric_driver_license_formats(license_number, recognizer, entities):
    text = f" {license_number} "

    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert_result_within_score_range(
        results[0],
        entities[0],
        1,
        len(license_number) + 1,
        0.3,
        0.3,
    )
    assert results[0].score == pytest.approx(0.3)


@pytest.mark.parametrize(
    "license_number",
    [
        "AB1",
        "AB12345678",
        "A123456789012345",
        "A1234567890123456",
        "A12345678901234567",
        "A-Z]]12",
    ],
)
def test_invalid_alphanumeric_driver_license_formats_are_ignored(
    license_number, recognizer, entities
):
    assert recognizer.analyze(license_number, entities) == []


def test_recognizer_loads_and_detects_when_enabled_in_yaml(tmp_path):
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
""",
        encoding="utf-8",
    )
    registry = RecognizerRegistryProvider(conf_file=conf).create_recognizer_registry()

    assert [type(r).__name__ for r in registry.recognizers] == ["UsLicenseRecognizer"]
    results = registry.recognizers[0].analyze(
        "License AB12", entities=["US_DRIVER_LICENSE"]
    )
    assert len(results) == 1
    assert_result_within_score_range(results[0], "US_DRIVER_LICENSE", 8, 12, 0.3, 0.3)
    assert results[0].score == pytest.approx(0.3)
