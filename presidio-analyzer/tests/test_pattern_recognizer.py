import importlib
import os
import re
from typing import List
from unittest.mock import MagicMock, patch

import pytest
import regex as regex_module
from presidio_analyzer import Pattern, PatternRecognizer, RecognizerResult
from presidio_analyzer.pattern_recognizer import REGEX_TIMEOUT_SECONDS

from tests import assert_result


class MockRecognizer(PatternRecognizer):
    def validate_result(self, pattern_text):
        return True

    def __init__(self, entity, patterns, deny_list, name, context):
        super().__init__(
            supported_entity=entity,
            name=name,
            patterns=patterns,
            deny_list=deny_list,
            context=context,
        )


def test_when_no_entity_for_pattern_recognizer_then_error():
    with pytest.raises(ValueError):
        patterns = [Pattern("p1", "someregex", 1.0), Pattern("p1", "someregex", 0.5)]
        MockRecognizer(
            entity=[], patterns=patterns, deny_list=[], name=None, context=None
        )


def test_when_deny_list_then_keywords_found():
    test_recognizer = MockRecognizer(
        patterns=[],
        entity="ENTITY_1",
        deny_list=["phone", "name"],
        context=None,
        name=None,
    )

    results = test_recognizer.analyze(
        "my phone number is 555-1234, and my name is John", ["ENTITY_1"]
    )

    assert len(results) == 2
    assert_result(results[0], "ENTITY_1", 3, 8, 1.0)
    assert_result(results[1], "ENTITY_1", 36, 40, 1.0)


def test_when_deny_list_then_keywords_not_found():
    test_recognizer = MockRecognizer(
        patterns=[],
        entity="ENTITY_1",
        deny_list=["phone", "name"],
        context=None,
        name=None,
    )

    results = test_recognizer.analyze(
        "No deny list words, though includes PII entities: 555-1234, John", ["ENTITY_1"]
    )

    assert len(results) == 0


def test_when_taken_from_dict_then_load_correctly():
    json = {
        "supported_entity": "ENTITY_1",
        "supported_language": "en",
        "patterns": [{"name": "p1", "score": 0.5, "regex": "([0-9]{1,9})"}],
        "context": ["w1", "w2", "w3"],
        "version": "1.0",
    }

    new_recognizer = PatternRecognizer.from_dict(json)
    # consider refactoring assertions
    assert new_recognizer.supported_entities == ["ENTITY_1"]
    assert new_recognizer.supported_language == "en"
    assert new_recognizer.patterns[0].name == "p1"
    assert new_recognizer.patterns[0].score == 0.5
    assert new_recognizer.patterns[0].regex == "([0-9]{1,9})"
    assert new_recognizer.context == ["w1", "w2", "w3"]
    assert new_recognizer.version == "1.0"


def test_when_taken_from_dict_then_returns_instance():
    pattern1_dict = {"name": "p1", "score": 0.5, "regex": "([0-9]{1,9})"}
    pattern2_dict = {"name": "p2", "score": 0.8, "regex": "([0-9]{1,9})"}

    ent_rec_dict = {
        "supported_entity": "A",
        "supported_language": "he",
        "patterns": [pattern1_dict, pattern2_dict],
    }
    pattern_recognizer = PatternRecognizer.from_dict(ent_rec_dict)

    assert pattern_recognizer.supported_entities == ["A"]
    assert pattern_recognizer.supported_language == "he"
    assert pattern_recognizer.version == "0.0.1"

    assert pattern_recognizer.patterns[0].name == "p1"
    assert pattern_recognizer.patterns[0].score == 0.5
    assert pattern_recognizer.patterns[0].regex == "([0-9]{1,9})"

    assert pattern_recognizer.patterns[1].name == "p2"
    assert pattern_recognizer.patterns[1].score == 0.8
    assert pattern_recognizer.patterns[1].regex == "([0-9]{1,9})"


def test_when_validation_occurs_then_analysis_explanation_is_updated():

    patterns = [Pattern(name="test_pattern", regex="([0-9]{1,9})", score=0.5)]
    mock_recognizer = MockRecognizer(
        entity="TEST",
        patterns=patterns,
        deny_list=None,
        name="MockRecognizer",
        context=None,
    )

    results: List[RecognizerResult] = mock_recognizer.analyze(
        text="Testing 1 2 3", entities=["TEST"]
    )

    assert results[0].analysis_explanation.original_score == 0.5
    assert results[0].analysis_explanation.score == 1


@pytest.mark.parametrize(
    "text, expected_len, deny_list",
    [
        ("Mr. PLUM", 1, ["Mr.", "Mrs."]),
        ("...Mr...PLUM...", 1, ["Mr.", "Mrs."]),
        ("..MMr...PLUM...", 0, ["Mr.", "Mrs."]),
        ("Mrr PLUM...", 0, ["Mr.", "Mrs."]),
        ("\\Mr.\\ PLUM...", 1, ["Mr.", "Mrs."]),
        ("\\Mr.\\ PLUM...,Mrs. Plum", 2, ["Mr.", "Mrs."]),
        ("", 0, ["Mr.", "Mrs."]),
        ("MMrrrMrs.", 0, ["Mr.", "Mrs."]),
        ("\\Mrs.", 1, ["Mr.", "Mrs."]),
        ("A B is an entity", 1, ["A B", "B C"]),
        ("A is not an entity", 0, ["A B", "B C"]),
        ("A B C", 1, ["A B", "B C"]),
        ("A B B C", 2, ["A B", "B C"]),
        ("Hi A.,.\\.B Hi", 1, ["A.,.\\.B"]),
    ],
)
def test_deny_list_non_space_separator_identified_correctly(
    text, expected_len, deny_list
):
    recognizer = PatternRecognizer(
        supported_entity="TITLE",
        name="TitlesRecognizer",
        supported_language="en",
        deny_list=deny_list,
    )

    result = recognizer.analyze(text, entities=["TITLE"])

    assert len(result) == expected_len


def test_deny_list_score_change():
    deny_list = ["Mr.", "Mrs."]
    recognizer = PatternRecognizer(
        supported_entity="TITLE",
        name="TitlesRecognizer",
        supported_language="en",
        deny_list=deny_list,
        deny_list_score=0.64,
    )

    result = recognizer.analyze(text="Mrs. Kennedy", entities=["TITLE"])
    assert result[0].score == 0.64


@pytest.mark.parametrize(
    "text,flag,expected_len",
    [("mrs. Kennedy", re.IGNORECASE, 1), ("mrs. Kennedy", re.DOTALL, 0)],
)
def test_deny_list_regex_flags(text, flag, expected_len):
    deny_list = ["Mr.", "Mrs."]
    recognizer = PatternRecognizer(
        supported_entity="TITLE",
        name="TitlesRecognizer",
        supported_language="en",
        deny_list=deny_list,
    )

    result = recognizer.analyze(text=text, entities=["TITLE"], regex_flags=flag)
    assert len(result) == expected_len


def test_empty_deny_list_raises_value_error():
    with pytest.raises(ValueError):
        PatternRecognizer(
            supported_entity="TITLE",
            name="TitlesRecognizer",
            supported_language="en",
            deny_list=[],
        )


@pytest.mark.parametrize(
    "global_flag,expected_len",
    [(re.IGNORECASE | re.MULTILINE, 2), (re.MULTILINE, 0)],
)
def test_global_regex_flag_deny_list_returns_right_result(global_flag, expected_len):
    deny_list = ["MrS", "mR"]
    text = "Mrs. smith \n\n" \
           "and Mr. Jones were sitting in the room."

    recognizer_ignore_case = PatternRecognizer(supported_entity="TITLE",
                                               name="TitlesRecognizer",
                                               deny_list=deny_list,
                                               global_regex_flags=global_flag)

    results = recognizer_ignore_case.analyze(text=text, entities=["TITLE"])
    assert len(results) == expected_len


def test_pattern_recognizer_with_invalidate_result():
    """Test PatternRecognizer with invalidate_result returning True."""
    class InvalidatingRecognizer(PatternRecognizer):
        def invalidate_result(self, pattern_text):
            # Invalidate if pattern starts with '0'
            return pattern_text.startswith('0')

    patterns = [Pattern(name="test_pattern", regex=r"\d{3}", score=0.8)]
    recognizer = InvalidatingRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="InvalidatingTest",
    )

    # Test with valid pattern (doesn't start with 0)
    results = recognizer.analyze("Test 123 and 456", ["TEST"])
    assert len(results) == 2
    assert all(r.score == 0.8 for r in results)

    # Test with invalidated pattern (starts with 0)
    results = recognizer.analyze("Test 012 and 098", ["TEST"])
    assert len(results) == 0  # Should be filtered out due to MIN_SCORE


def test_pattern_recognizer_with_validate_result_false():
    """Test PatternRecognizer with validate_result returning False."""
    class ValidatingRecognizer(PatternRecognizer):
        def validate_result(self, pattern_text):
            # Only validate if it contains digit '5'
            return '5' in pattern_text

    patterns = [Pattern(name="test_pattern", regex=r"\d{3}", score=0.5)]
    recognizer = ValidatingRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="ValidatingTest",
    )

    # Test with valid pattern (contains 5)
    results = recognizer.analyze("Test 456", ["TEST"])
    assert len(results) == 1
    assert results[0].score == 1.0  # MAX_SCORE

    # Test with invalid pattern (no 5)
    results = recognizer.analyze("Test 123", ["TEST"])
    assert len(results) == 0  # Filtered due to MIN_SCORE


def test_pattern_recognizer_with_both_validate_and_invalidate():
    """Test PatternRecognizer with both validate and invalidate logic."""
    class BothRecognizer(PatternRecognizer):
        def validate_result(self, pattern_text):
            return len(pattern_text) == 3

        def invalidate_result(self, pattern_text):
            return pattern_text == "000"

    patterns = [Pattern(name="test_pattern", regex=r"\d{3}", score=0.5)]
    recognizer = BothRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="BothTest",
    )

    # Test with valid and not invalidated
    results = recognizer.analyze("Test 123", ["TEST"])
    assert len(results) == 1
    assert results[0].score == 1.0

    # Test with invalidated
    results = recognizer.analyze("Test 000", ["TEST"])
    assert len(results) == 0


def test_pattern_recognizer_empty_match_skipped():
    """Test that empty regex matches are skipped."""
    patterns = [Pattern(name="test_pattern", regex=r"\d*", score=0.5)]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="EmptyMatchTest",
    )

    # This regex can match empty strings
    results = recognizer.analyze("abc", ["TEST"])
    # Empty matches should be filtered out
    assert len(results) == 0


def test_pattern_recognizer_to_dict():
    """Test serialization of PatternRecognizer to dict."""
    patterns = [Pattern(name="p1", regex=r"\d+", score=0.8)]
    deny_list = ["word1", "word2"]
    context = ["context1", "context2"]

    recognizer = PatternRecognizer(
        supported_entity="TEST_ENTITY",
        patterns=patterns,
        deny_list=deny_list,
        context=context,
        name="TestRecognizer",
        version="1.0.0",
    )

    result_dict = recognizer.to_dict()

    assert result_dict["supported_entity"] == "TEST_ENTITY"
    assert "supported_entities" not in result_dict
    assert len(result_dict["patterns"]) == 2  # 1 pattern + 1 deny_list pattern
    assert result_dict["deny_list"] == deny_list
    assert result_dict["context"] == context
    assert result_dict["name"] == "TestRecognizer"
    assert result_dict["version"] == "1.0.0"


def test_pattern_recognizer_from_dict_with_both_supported_entity_and_entities():
    """Test from_dict raises error when both supported_entity and supported_entities present."""
    recognizer_dict = {
        "supported_entity": "ENTITY_A",
        "supported_entities": ["ENTITY_B"],
        "patterns": [{"name": "p1", "score": 0.5, "regex": r"\d+"}],
    }

    with pytest.raises(ValueError, match="Both 'supported_entity' and 'supported_entities'"):
        PatternRecognizer.from_dict(recognizer_dict)


def test_pattern_recognizer_from_dict_with_supported_entities_only():
    """Test from_dict uses first element of supported_entities."""
    recognizer_dict = {
        "supported_entities": ["ENTITY_A", "ENTITY_B"],
        "patterns": [{"name": "p1", "score": 0.5, "regex": r"\d+"}],
    }

    recognizer = PatternRecognizer.from_dict(recognizer_dict)
    assert recognizer.supported_entities == ["ENTITY_A"]


def test_pattern_recognizer_from_dict_with_empty_supported_entities():
    """Test from_dict with empty supported_entities list."""
    recognizer_dict = {
        "supported_entities": [],
        "patterns": [{"name": "p1", "score": 0.5, "regex": r"\d+"}],
    }

    # Should raise TypeError because supported_entity parameter is missing
    with pytest.raises(TypeError):
        PatternRecognizer.from_dict(recognizer_dict)


def test_pattern_recognizer_analyze_with_custom_regex_flags():
    """Test analyze with custom regex flags."""
    patterns = [Pattern(name="test_pattern", regex=r"test", score=0.8)]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="FlagTest",
        global_regex_flags=0,  # No flags by default
    )

    # Should not match with default flags (case-sensitive)
    results = recognizer.analyze("TEST", ["TEST"])
    assert len(results) == 0

    # Should match with IGNORECASE flag
    results = recognizer.analyze("TEST", ["TEST"], regex_flags=re.IGNORECASE)
    assert len(results) == 1


def test_pattern_recognizer_multiple_patterns():
    """Test recognizer with multiple patterns."""
    patterns = [
        Pattern(name="pattern1", regex=r"\b\d{3}\b", score=0.6),
        Pattern(name="pattern2", regex=r"\b[A-Z]{4}\b", score=0.7),
    ]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="MultiPatternTest",
        global_regex_flags=re.DOTALL | re.MULTILINE
    )

    results = recognizer.analyze("Number 123 and CAPS word", ["TEST"])
    # Should find exactly 2 results (digits and capitals)
    assert len(results) == 2

    # Check that both patterns were matched with correct scores
    scores = sorted([r.score for r in results])
    assert scores == [0.6, 0.7]


def test_pattern_recognizer_build_regex_explanation():
    """Test build_regex_explanation static method."""
    explanation = PatternRecognizer.build_regex_explanation(
        recognizer_name="TestRecognizer",
        pattern_name="TestPattern",
        pattern=r"\d+",
        original_score=0.85,
        validation_result=True,
        regex_flags=re.IGNORECASE,
    )

    assert explanation.recognizer == "TestRecognizer"
    assert explanation.pattern_name == "TestPattern"
    assert explanation.pattern == r"\d+"
    assert explanation.original_score == 0.85
    assert explanation.validation_result == True
    assert explanation.regex_flags == re.IGNORECASE
    assert "TestRecognizer" in explanation.textual_explanation
    assert "TestPattern" in explanation.textual_explanation


def test_pattern_recognizer_load_method():
    """Test that load method can be called without error."""
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        deny_list=["test"],
    )

    # load() should not raise any exception
    recognizer.load()


def test_pattern_recognizer_with_zero_global_regex_flags():
    """Test PatternRecognizer with 0 as global_regex_flags."""
    patterns = [Pattern(name="test", regex=r"test", score=0.5)]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        global_regex_flags=0,
    )

    # Should work with 0 flags (case-sensitive)
    results = recognizer.analyze("test", ["TEST"])
    assert len(results) == 1

    # Should not match different case
    results = recognizer.analyze("TEST", ["TEST"])
    assert len(results) == 0


def test_pattern_recognizer_recompiles_regex_on_flag_change():
    """Test that regex is recompiled when flags change."""
    patterns = [Pattern(name="test", regex=r"test", score=0.5)]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        global_regex_flags=0,
    )

    # First analysis with no flags
    results = recognizer.analyze("TEST", ["TEST"], regex_flags=0)
    assert len(results) == 0

    # Second analysis with IGNORECASE flag (should recompile)
    results = recognizer.analyze("TEST", ["TEST"], regex_flags=re.IGNORECASE)
    assert len(results) == 1


def test_pattern_recognizer_recognizer_metadata():
    """Test that recognition_metadata is properly set in results."""
    patterns = [Pattern(name="test", regex=r"\d+", score=0.5)]
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=patterns,
        name="MetadataTest",
    )

    results = recognizer.analyze("Test 123", ["TEST"])
    assert len(results) == 1

    metadata = results[0].recognition_metadata
    assert "recognizer_name" in metadata
    assert metadata["recognizer_name"] == "MetadataTest"
    assert "recognizer_identifier" in metadata


def test_when_regex_times_out_then_pattern_is_skipped():
    """Test that a timed-out regex pattern is skipped and returns no results."""
    patterns = [Pattern(name="slow", regex=r"\d+", score=0.5)]
    recognizer = PatternRecognizer(supported_entity="TEST", patterns=patterns)

    mock_compiled = MagicMock()
    mock_compiled.finditer.side_effect = TimeoutError("regex timed out")

    with patch(
        "presidio_analyzer.pattern_recognizer.re.compile",
        return_value=mock_compiled,
    ):
        results = recognizer.analyze("Test 123", ["TEST"])

    assert results == []


def test_when_regex_times_out_then_other_patterns_still_run():
    """Test that a timed-out pattern doesn't prevent other patterns from running."""
    slow_pattern = Pattern(name="slow", regex=r"\d+", score=0.5)
    fast_pattern = Pattern(name="fast", regex=r"[a-z]+", score=0.6)
    recognizer = PatternRecognizer(
        supported_entity="TEST", patterns=[slow_pattern, fast_pattern]
    )

    original_compile = regex_module.compile
    call_count = 0

    def compile_side_effect(pattern_str, **kwargs):
        nonlocal call_count
        call_count += 1
        compiled = original_compile(pattern_str, **kwargs)
        if call_count == 1:
            mock_compiled = MagicMock()
            mock_compiled.finditer.side_effect = TimeoutError("regex timed out")
            return mock_compiled
        return compiled

    with patch(
        "presidio_analyzer.pattern_recognizer.re.compile",
        side_effect=compile_side_effect,
    ):
        results = recognizer.analyze("test123", ["TEST"])

    # fast_pattern (letters) should still have produced results even if slow timed out
    assert len(results) >= 1


def test_regex_timeout_seconds_value():
    """Test that REGEX_TIMEOUT_SECONDS is set to 60 seconds."""
    assert REGEX_TIMEOUT_SECONDS == 60


def test_regex_timeout_seconds_env_var_override():
    """Test that REGEX_TIMEOUT_SECONDS can be overridden via environment variable."""
    import presidio_analyzer.pattern_recognizer as pr_module

    with patch.dict(os.environ, {"REGEX_TIMEOUT_SECONDS": "30"}):
        importlib.reload(pr_module)
        assert pr_module.REGEX_TIMEOUT_SECONDS == 30

    # Restore the module to default state
    importlib.reload(pr_module)


@pytest.mark.parametrize(
    "regex, capture_group, expected_start, expected_end",
    [
        (r"Password: (\w+)", None, 0, 14),
        (r"Password: (\w+)", 0, 0, 14),
        (r"Password: (\w+)", 1, 10, 14),
        (r"Password: (?P<password>\w+)", "password", 10, 14),
    ],
)
def test_when_capture_group_given_then_result_spans_that_group_or_whole_match(
    regex, capture_group, expected_start, expected_end
):
    recognizer = PatternRecognizer(
        supported_entity="PASSWORD",
        patterns=[
            Pattern(
                name="password", regex=regex, score=0.5, capture_group=capture_group
            )
        ],
    )

    results = recognizer.analyze("Password: 1234", ["PASSWORD"])

    assert len(results) == 1
    assert_result(results[0], "PASSWORD", expected_start, expected_end, 0.5)


@pytest.mark.parametrize(
    "text, expected_spans",
    [
        ("id", []),
        ("id:", []),
        ("id: 42", [(4, 6)]),
    ],
)
def test_when_capture_group_does_not_participate_or_is_empty_then_match_is_skipped(
    text, expected_spans
):
    recognizer = PatternRecognizer(
        supported_entity="ID",
        patterns=[
            Pattern(name="id", regex=r"\bid(?:(:) ?(\d*))?", score=0.5, capture_group=2)
        ],
    )

    results = recognizer.analyze(text, ["ID"])

    assert [(result.start, result.end) for result in results] == expected_spans


def test_when_capture_group_set_then_validation_hooks_receive_group_text():
    received = []

    class RecordingRecognizer(PatternRecognizer):
        def validate_result(self, pattern_text):
            received.append(("validate", pattern_text))
            return None

        def invalidate_result(self, pattern_text):
            received.append(("invalidate", pattern_text))
            return None

    recognizer = RecordingRecognizer(
        supported_entity="PASSWORD",
        patterns=[
            Pattern(
                name="password", regex=r"Password: (\w+)", score=0.5, capture_group=1
            )
        ],
    )

    recognizer.analyze("Password: 1234", ["PASSWORD"])

    assert received == [("validate", "1234"), ("invalidate", "1234")]


def test_when_same_regex_uses_different_capture_groups_then_each_group_is_reported():
    regex = r"(\w+)@(\w+)\.com"
    recognizer = PatternRecognizer(
        supported_entity="EMAIL_PART",
        patterns=[
            Pattern(name="user", regex=regex, score=0.4, capture_group=1),
            Pattern(name="domain", regex=regex, score=0.4, capture_group=2),
        ],
    )

    results = recognizer.analyze("mail john@example.com", ["EMAIL_PART"])

    assert sorted((result.start, result.end) for result in results) == [
        (5, 9),
        (10, 17),
    ]


@pytest.mark.parametrize("capture_group", [2, "b"])
def test_when_regex_flags_remove_capture_group_then_pattern_is_skipped_with_warning(
    caplog, capture_group
):
    # With re.VERBOSE, "# (?P<b>b)" is a comment, so the regex has only one group
    verbose_dependent = Pattern(
        name="verbose_dependent",
        regex=r"(secret\w*) # (?P<b>b)",
        score=0.5,
        capture_group=capture_group,
    )
    plain = Pattern(name="plain", regex=r"\b\d+\b", score=0.6)
    recognizer = PatternRecognizer(
        supported_entity="TEST",
        patterns=[verbose_dependent, plain],
        global_regex_flags=re.VERBOSE,
    )

    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        results = recognizer.analyze("secretvalue 123 secretother", ["TEST"])

    assert [(result.start, result.end, result.score) for result in results] == [
        (12, 15, 0.6)
    ]
    # Logged once per analyze call, not once per match
    warning = (
        f"Regex pattern 'verbose_dependent' has no capture group {capture_group!r} "
        "when compiled with the regex flags in use, skipping."
    )
    assert caplog.text.count(warning) == 1
    assert "secretvalue" not in caplog.text
    assert "secretother" not in caplog.text

    # The warning does not depend on the text containing a candidate match
    caplog.clear()
    with caplog.at_level("WARNING", logger="presidio-analyzer"):
        assert recognizer.analyze("no candidates here", ["TEST"]) == []
    assert caplog.text.count(warning) == 1


def test_when_capture_group_set_then_recognizer_round_trips_through_dict():
    recognizer_dict = {
        "supported_entity": "PASSWORD",
        "patterns": [
            {
                "name": "password",
                "regex": r"Password: (?P<password>\w+)",
                "score": 0.5,
                "capture_group": "password",
            }
        ],
    }

    recognizer = PatternRecognizer.from_dict(recognizer_dict)
    restored = PatternRecognizer.from_dict(recognizer.to_dict())

    assert recognizer.patterns[0].capture_group == "password"
    assert recognizer.to_dict()["patterns"] == recognizer_dict["patterns"]
    results = restored.analyze("Password: 1234", ["PASSWORD"])
    assert len(results) == 1
    assert_result(results[0], "PASSWORD", 10, 14, 0.5)
