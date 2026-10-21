"""Tests for Thai National ID (TNIN) recognizer."""

from pathlib import Path

import presidio_analyzer
import pytest
import yaml
from presidio_analyzer.predefined_recognizers import ThTninRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider

from tests import assert_result, assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Create a Thai TNIN recognizer instance for testing."""
    return ThTninRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return the Thai TNIN entity type for testing."""
    return ["TH_TNIN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid TNINs - should get high scores due to format validation and checksum
        # Note: These are example TNINs created for testing purposes
        # with valid checksums
        ("1234567890121", 1, ((0, 13),), ((0.5, 1.0),),),
        ("2345678901234", 1, ((0, 13),), ((0.5, 1.0),),),
        ("3456789012347", 1, ((0, 13),), ((0.5, 1.0),),),
        ("4567890123459", 1, ((0, 13),), ((0.5, 1.0),),),
        ("5678901234560", 1, ((0, 13),), ((0.5, 1.0),),),

        # Regression: valid TNINs whose province code (N2N3) is 22, 52 or 58.
        # These are real, assigned provinces (Chanthaburi/Lampang/Mae Hong Son)
        # and are NOT in the forbidden list, but an over-narrow regex class
        # ([25][0134567]) dropped N3=2 and N3=8, rejecting them.
        ("1220000000007", 1, ((0, 13),), ((0.5, 1.0),),),  # province 22
        ("1520000000004", 1, ((0, 13),), ((0.5, 1.0),),),  # province 52
        ("1580000000004", 1, ((0, 13),), ((0.5, 1.0),),),  # province 58

        # Valid TNINs in sentences
        ("My Thai ID is 1234567890121", 1, ((14, 27),), ((0.5, 1.0),),),
        ("TNIN: 2345678901234", 1, ((6, 19),), ((0.5, 1.0),),),
        ("เลขประจำตัวประชาชน: 3456789012347", 1, ((20, 33),), ((0.5, 1.0),),),

        # Invalid TNINs - wrong length
        ("123456789012", 0, (), (),),  # 12 digits
        ("12345678901234", 0, (), (),),  # 14 digits

        # Invalid TNINs - non-digits
        ("123456789012a", 0, (), (),),  # contains letter
        ("123456789012 ", 0, (), (),),  # contains space

        # Invalid TNINs - format violations (first digit is 0)
        ("0234567890124", 0, (), (),),
        ("0034567890124", 0, (), (),),

        # Invalid TNINs - format violations (second digit is 0)
        ("1034567890124", 0, (), (),),
        ("1304567890124", 0, (), (),),

        # Invalid TNINs - forbidden second-third combinations
        ("1284567890124", 0, (), (),),  # 28 is forbidden
        ("1294567890124", 0, (), (),),  # 29 is forbidden
        ("1594567890124", 0, (), (),),  # 59 is forbidden
        ("1684567890124", 0, (), (),),  # 68 is forbidden
        ("1694567890124", 0, (), (),),  # 69 is forbidden
        ("1784567890124", 0, (), (),),  # 78 is forbidden
        ("1794567890124", 0, (), (),),  # 79 is forbidden
        ("1874567890124", 0, (), (),),  # 87 is forbidden
        ("1884567890124", 0, (), (),),  # 88 is forbidden
        ("1894567890124", 0, (), (),),  # 89 is forbidden
        ("1974567890124", 0, (), (),),  # 97 is forbidden
        ("1984567890124", 0, (), (),),  # 98 is forbidden
        ("1994567890124", 0, (), (),),  # 99 is forbidden

        # Invalid TNINs - checksum failures (but valid format)
        # These have valid format but wrong checksum digit
        ("1234567890123", 0, (), (),),  # should be 1, not 3
        ("2345678901235", 0, (), (),),  # should be 4, not 5
        ("3456789012346", 0, (), (),),  # should be 7, not 6

        # Edge cases
        ("0000000000000", 0, (), (),),  # all zeros (invalid format)
        ("1111111111111", 0, (), (),),  # all ones (valid format but wrong checksum)

        # Context enhancement tests
        ("Thai National ID 1234567890121", 1, ((17, 30),), ((0.5, 1.0),),),
        ("เลขบัตรประชาชน 2345678901234", 1, ((15, 28),), ((0.5, 1.0),),),
    ],
)
def test_when_tnin_in_text_then_all_tnins_found(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Test that Thai TNIN recognizer correctly identifies TNINs.

    Test various text contexts including valid TNINs, invalid formats,
    and different languages to ensure proper recognition.
    """
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


def test_validate_result_with_valid_tnin(recognizer):
    """Test validate_result method with valid TNINs."""
    # These should return True (valid)
    assert recognizer.validate_result("1234567890121") is True
    assert recognizer.validate_result("2345678901234") is True
    assert recognizer.validate_result("3456789012347") is True


def test_validate_result_with_invalid_format(recognizer):
    """Test validate_result method with invalid format TNINs."""
    # These should return False (invalid format)
    assert recognizer.validate_result("0234567890124") is False  # starts with 0
    assert recognizer.validate_result("1034567890124") is False  # second digit is 0
    assert recognizer.validate_result("1284567890124") is False  # forbidden 28
    assert recognizer.validate_result("1294567890124") is False  # forbidden 29


def test_validate_result_with_wrong_length(recognizer):
    """Test validate_result method with wrong length."""
    # These should return False (wrong length)
    assert recognizer.validate_result("123456789012") is False  # 12 digits
    assert recognizer.validate_result("12345678901234") is False  # 14 digits


def test_validate_result_with_non_digits(recognizer):
    """Test validate_result method with non-digit characters."""
    # These should return False (non-digits)
    assert recognizer.validate_result("123456789012a") is False  # contains letter
    assert recognizer.validate_result("123456789012 ") is False  # contains space


def test_context_words(recognizer):
    """Test that context words are properly set."""
    expected_context = [
        "Thai National ID",
        "Thai ID Number",
        "TNIN",
        "เลขประจำตัวประชาชน",
        "เลขบัตรประชาชน",
        "รหัสปชช",
    ]
    assert recognizer.context == expected_context


def test_supported_entity(recognizer):
    """Test that supported entity is correctly set."""
    assert recognizer.supported_entities == ["TH_TNIN"]


def test_supported_language(recognizer):
    """Test that supported language is correctly set."""
    assert recognizer.supported_language == "th"


@pytest.mark.parametrize(
    "text, expected_span",
    [
        # Grouped 1-4-5-2-1 as printed on the ID card (1103702071811)
        ("เลขประจำตัวประชาชน 1 1037 02071 81 1", (19, 36)),
        # Dashed, as written on forms
        ("เลขประจำตัวประชาชน 1-1037-02071-81-1", (19, 36)),
        ("Thai ID Number: 3-1010-00123-45-0 issued", (16, 33)),
        # Thai text runs straight into the number
        ("เลขประจำตัวประชาชน1-1037-02071-81-1", (18, 35)),
        ("1 2201 00000 00 9", (0, 17)),
        # An unrelated number next to it, with the other separator
        ("1-1037-02071-81-1 2026", (0, 17)),
        ("No. 1 1-1037-02071-81-1", (6, 23)),
    ],
)
def test_when_tnin_is_grouped_then_found_and_validated(
    text, expected_span, recognizer, entities, max_score
):
    """A TNIN written in its card grouping is detected and passes the checksum."""
    results = recognizer.analyze(text, entities)

    assert len(results) == 1
    assert_result(results[0], "TH_TNIN", *expected_span, max_score)


@pytest.mark.parametrize(
    "text",
    [
        "1 1037 02071 81 2",  # grouped, wrong check digit
        "1-1037 02071-81-1",  # mixed separators
        "1 1037 0207181 1",  # wrong grouping
        "11 1037 02071 81 1",  # longer leading run
        "1 1037 02071 81 1 5",  # longer trailing run
        "1-1037-02071-81-1-5",  # longer trailing run, dashed
        "7-1-1037-02071-81-1",  # longer leading run, dashed
        "1 2837 02071 81 1",  # forbidden province code 28
    ],
)
def test_when_grouped_tnin_lookalike_then_not_found(text, recognizer, entities):
    """Grouped lookalikes stay undetected."""
    assert recognizer.analyze(text, entities) == []


def test_grouped_tnin_detected_when_enabled_in_yaml(max_score):
    """The grouped form is detected through the registry configuration path."""
    conf = Path(presidio_analyzer.__file__).parent / "conf" / "default_recognizers.yaml"
    recognizers = yaml.safe_load(conf.read_text(encoding="utf-8"))["recognizers"]
    entry = next(r for r in recognizers if r.get("name") == "ThTninRecognizer")

    registry = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["th"],
            "recognizers": [dict(entry, enabled=True)],
        }
    ).create_recognizer_registry()
    results = registry.recognizers[0].analyze(
        "เลขประจำตัวประชาชน 1-1037-02071-81-1", ["TH_TNIN"]
    )

    assert len(results) == 1
    assert_result(results[0], "TH_TNIN", 19, 36, max_score)
