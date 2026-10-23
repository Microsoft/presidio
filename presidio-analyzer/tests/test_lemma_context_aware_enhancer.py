import pytest

from presidio_analyzer import LemmaContextAwareEnhancer


def test_when_index_finding_then_succeed():
    # This test uses a simulated recognize result for the following
    # text: "my phone number is:(425) 882-9090"
    match = "(425) 882-9090"
    # the start index of the match
    start = 19
    tokens = ["my", "phone", "number", "is:(425", ")", "882", "-", "9090"]
    tokens_indices = [0, 3, 9, 16, 23, 25, 28, 29]
    index = LemmaContextAwareEnhancer._find_index_of_match_token(
        match, start, tokens, tokens_indices
    )
    assert index == 3


def test_when_context_word_substring_then_no_false_match():
    """
    Test that substring matching does not cause false positives.
    
    This test verifies the fix for issue #1061 where 'lic' was matching
    'duplicate' as a substring. With whole-word matching, 'lic' should
    only match 'lic' exactly, not substrings like 'duplicate'.
    """
    context_list = ["duplicate", "license", "driver"]
    recognizer_context_list = ["lic"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    # 'lic' should NOT match 'duplicate' (substring match - should be False)
    # 'lic' should NOT match 'license' (not exact match - should be False)
    # 'lic' should NOT match 'driver' (not exact match - should be False)
    assert result == ""


def test_when_context_word_exact_match_then_succeed():
    """
    Test that exact whole-word matches work correctly.
    
    'lic' should match 'lic' exactly (case-insensitive).
    """
    context_list = ["lic", "license", "driver"]
    recognizer_context_list = ["lic"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    # 'lic' should match 'lic' exactly
    assert result == "lic"


def test_when_context_word_case_insensitive_then_succeed():
    """
    Test that matching is case-insensitive.
    
    'LIC' should match 'lic' and vice versa.
    """
    context_list = ["LIC", "license", "driver"]
    recognizer_context_list = ["lic"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    # 'lic' should match 'LIC' (case-insensitive)
    assert result == "lic"
    
    # Test reverse case
    context_list = ["lic", "license", "driver"]
    recognizer_context_list = ["LIC"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    # 'LIC' should match 'lic' (case-insensitive)
    assert result == "LIC"


def test_when_context_word_multiple_matches_then_first_match_returned():
    """
    Test that when multiple context words match, the first one is returned.
    """
    context_list = ["driver", "license", "permit"]
    recognizer_context_list = ["license", "driver", "permit"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    # Should return the first match from recognizer_context_list
    assert result == "license"


def test_when_context_word_no_match_then_empty_string():
    """
    Test that when no context words match, empty string is returned.
    """
    context_list = ["random", "words", "here"]
    recognizer_context_list = ["lic", "driver", "license"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="whole_word"
    )
    
    assert result == ""


def test_when_duplicate_word_in_text_then_lic_context_not_matched_with_whole_word(
    spacy_nlp_engine,
):
    """
    Integration test for issue #1061: 'lic' should not match 'duplicate' with whole_word mode.
    
    This test verifies that when using "whole_word" mode, the context word 'lic'
    (from US_DRIVER_LICENSE recognizer) should NOT cause false context enhancement
    when 'duplicate' appears in text.
    """
    from presidio_analyzer import PatternRecognizer, Pattern
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    
    # Create a recognizer with 'lic' as context word (similar to US_DRIVER_LICENSE)
    test_recognizer = PatternRecognizer(
        supported_entity="TEST_LICENSE",
        name="test_license_recognizer",
        context=["lic"],  # This is the problematic context word
        patterns=[Pattern("test_pattern", r"\b[A-Z0-9]{8}\b", 0.3)],
    )
    
    # Test case: Text with 'duplicate' but no actual license context words
    # The word 'duplicate' contains 'lic' as a substring, but should NOT match with whole_word mode
    text = "This is a duplicate document with code ABC12345"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    
    recognizer_results = test_recognizer.analyze(text, nlp_artifacts)
    assert len(recognizer_results) > 0
    
    original_score = recognizer_results[0].score
    
    # Use whole_word mode to prevent false positives
    enhancer = LemmaContextAwareEnhancer(context_matching_mode="whole_word")
    enhanced_results = enhancer.enhance_using_context(
        text, recognizer_results, nlp_artifacts, [test_recognizer]
    )
    
    # With whole-word matching, 'lic' should NOT match 'duplicate'
    # So the score should NOT be enhanced and supportive_context_word should be empty
    assert enhanced_results[0].score == original_score
    assert (
        enhanced_results[0].analysis_explanation.supportive_context_word == ""
    )


def test_when_duplicate_word_in_text_then_lic_context_matches_with_substring(
    spacy_nlp_engine,
):
    """
    Test that substring mode (default) maintains backward compatibility.
    
    This test verifies that with the default "substring" mode, 'lic' DOES match
    'duplicate' (the original behavior), maintaining backward compatibility.
    """
    from presidio_analyzer import PatternRecognizer, Pattern
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    
    # Create a recognizer with 'lic' as context word
    test_recognizer = PatternRecognizer(
        supported_entity="TEST_LICENSE",
        name="test_license_recognizer",
        context=["lic"],
        patterns=[Pattern("test_pattern", r"\b[A-Z0-9]{8}\b", 0.3)],
    )
    
    # Text with 'duplicate' - with substring mode (default), 'lic' should match
    text = "This is a duplicate document with code ABC12345"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    
    recognizer_results = test_recognizer.analyze(text, nlp_artifacts)
    assert len(recognizer_results) > 0
    
    original_score = recognizer_results[0].score
    
    # Use default substring mode (backward compatible behavior)
    enhancer = LemmaContextAwareEnhancer()  # Default is "substring"
    enhanced_results = enhancer.enhance_using_context(
        text, recognizer_results, nlp_artifacts, [test_recognizer]
    )
    
    # With substring matching (default), 'lic' DOES match 'duplicate' (original behavior)
    # So the score should be enhanced
    assert enhanced_results[0].score > original_score
    assert (
        enhanced_results[0].analysis_explanation.supportive_context_word == "lic"
    )


def test_when_substring_matching_mode_then_compound_words_match():
    """
    Test that substring matching mode works for compound words.
    
    This verifies that 'card' can match 'creditcard' when using substring mode,
    which is useful for handling words without spaces.
    """
    context_list = ["creditcard", "passportnumber", "driverlicense"]
    recognizer_context_list = ["card", "passport", "license"]
    
    # With substring matching, 'card' should match 'creditcard'
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="substring"
    )
    
    assert result == "card"
    
    # Test that 'lic' also matches 'duplicate' in substring mode (the original behavior)
    context_list = ["duplicate", "license"]
    recognizer_context_list = ["lic"]
    
    result = LemmaContextAwareEnhancer._find_supportive_word_in_context(
        context_list, recognizer_context_list, matching_mode="substring"
    )
    
    # In substring mode, 'lic' matches 'duplicate' (original behavior)
    assert result == "lic"


def test_when_invalid_matching_mode_then_raises_error():
    """
    Test that invalid matching mode raises ValueError.
    """
    import pytest
    
    with pytest.raises(ValueError, match="context_matching_mode must be one of"):
        LemmaContextAwareEnhancer(context_matching_mode="invalid_mode")
    
    # Test that "hybrid" is no longer a valid mode (it was redundant)
    with pytest.raises(ValueError, match="context_matching_mode must be one of"):
        LemmaContextAwareEnhancer(context_matching_mode="hybrid")


def test_when_substring_mode_then_compound_words_work_in_integration(spacy_nlp_engine):
    """
    Integration test for substring matching with compound words.
    
    This test verifies that substring matching works end-to-end for cases
    like "passportnumber" matching "passport" context word.
    """
    from presidio_analyzer import PatternRecognizer, Pattern
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    
    # Create a recognizer with 'passport' as context word
    test_recognizer = PatternRecognizer(
        supported_entity="TEST_PASSPORT",
        name="test_passport_recognizer",
        context=["passport"],  # Context word that should match in compound words
        patterns=[Pattern("test_pattern", r"\b[A-Z0-9]{8}\b", 0.3)],
    )
    
    # Text with compound word "passportnumber" (no space)
    text = "My passportnumber is ABC12345"
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    
    recognizer_results = test_recognizer.analyze(text, nlp_artifacts)
    assert len(recognizer_results) > 0
    
    original_score = recognizer_results[0].score
    
    # Use substring matching mode
    enhancer = LemmaContextAwareEnhancer(context_matching_mode="substring")
    enhanced_results = enhancer.enhance_using_context(
        text, recognizer_results, nlp_artifacts, [test_recognizer]
    )
    
    # With substring matching, 'passport' should match 'passportnumber'
    # So the score should be enhanced
    assert enhanced_results[0].score > original_score
    assert (
        enhanced_results[0].analysis_explanation.supportive_context_word == "passport"
    )


def _licence_recognizer(context, regex=r"\b[A-Z]{3}\d{5}\b"):
    from presidio_analyzer import Pattern, PatternRecognizer

    return PatternRecognizer(
        supported_entity="TEST_LICENCE",
        name="test_licence_recognizer",
        context=context,
        patterns=[Pattern("test_pattern", regex, 0.3)],
    )


def _enhance_one(spacy_nlp_engine, text, recognizer, enhancer):
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    results = recognizer.analyze(text, recognizer.supported_entities, nlp_artifacts)
    assert len(results) == 1
    return enhancer.enhance_using_context(text, results, nlp_artifacts, [recognizer])[0]


@pytest.mark.parametrize(
    "recognizer_name, text, phrase, start, end",
    [
        (
            "UkDrivingLicenceRecognizer",
            "My driving licence number is MORGA753116SM9IJ.",
            "driving licence",
            29,
            45,
        ),
        (
            "UkNinoRecognizer",
            "His national insurance is AB 12 34 56 C.",
            "national insurance",
            26,
            39,
        ),
    ],
)
def test_when_predefined_multi_word_context_precedes_entity_then_score_enhanced(
    spacy_nlp_engine, recognizer_name, text, phrase, start, end
):
    from presidio_analyzer import predefined_recognizers

    recognizer = getattr(predefined_recognizers, recognizer_name)()
    enhancer = LemmaContextAwareEnhancer()
    control_text = "Reference " + text[start:end] + " was filed."

    result = _enhance_one(spacy_nlp_engine, text, recognizer, enhancer)
    control = _enhance_one(spacy_nlp_engine, control_text, recognizer, enhancer)

    assert (result.start, result.end) == (start, end)
    assert result.score == pytest.approx(0.85)
    assert result.analysis_explanation.supportive_context_word == phrase
    assert result.analysis_explanation.score_context_improvement == pytest.approx(0.35)
    assert control.score == pytest.approx(0.5)
    assert control.analysis_explanation.supportive_context_word == ""


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
@pytest.mark.parametrize(
    "text",
    [
        "My driving licence number is ABC12345",
        "My Driving  LICENCE is ABC12345",
        "driving\tlicence:\nABC12345",
    ],
)
def test_when_multi_word_context_word_in_window_then_score_enhanced(
    spacy_nlp_engine, text, matching_mode
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = LemmaContextAwareEnhancer(context_matching_mode=matching_mode)

    result = _enhance_one(spacy_nlp_engine, text, recognizer, enhancer)

    assert result.score == pytest.approx(0.65)
    assert result.analysis_explanation.supportive_context_word == "driving licence"


@pytest.mark.parametrize(
    "text",
    [
        "licence driving ABC12345",
        "driving the licence ABC12345",
        "driving, licence ABC12345",
        # after the entity, and the suffix window is 0 by default
        "ABC12345 is my driving licence",
        # before the five keywords of the prefix window
        "driving licence office closed early today because staff were ill ABC12345",
    ],
)
def test_when_multi_word_context_word_not_in_window_then_score_unchanged(
    spacy_nlp_engine, text
):
    recognizer = _licence_recognizer(["driving licence"])

    result = _enhance_one(
        spacy_nlp_engine, text, recognizer, LemmaContextAwareEnhancer()
    )

    assert result.score == pytest.approx(0.3)
    assert result.analysis_explanation.supportive_context_word == ""


def test_when_suffix_window_set_then_multi_word_context_after_entity_counts(
    spacy_nlp_engine,
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = LemmaContextAwareEnhancer(context_suffix_count=3)

    result = _enhance_one(
        spacy_nlp_engine, "ABC12345 is my driving licence", recognizer, enhancer
    )

    assert result.score == pytest.approx(0.65)


def test_when_multi_word_context_word_embedded_then_only_substring_mode_matches(
    spacy_nlp_engine,
):
    text = "My driving licences are ABC12345"
    recognizer = _licence_recognizer(["driving licence"])

    substring = _enhance_one(
        spacy_nlp_engine,
        text,
        recognizer,
        LemmaContextAwareEnhancer(context_matching_mode="substring"),
    )
    whole_word = _enhance_one(
        spacy_nlp_engine,
        text,
        recognizer,
        LemmaContextAwareEnhancer(context_matching_mode="whole_word"),
    )

    assert substring.score == pytest.approx(0.65)
    assert whole_word.score == pytest.approx(0.3)


@pytest.mark.parametrize(
    "text, expected_score",
    [
        # the phrase is part of the entity itself
        ("Filed: driving licence 12345", 0.3),
        # an occurrence inside the entity, then one before it
        ("driving licence: driving licence 12345", 0.65),
    ],
)
def test_when_multi_word_context_word_overlaps_entity_then_it_is_not_context(
    spacy_nlp_engine, text, expected_score
):
    recognizer = _licence_recognizer(["driving licence"], r"driving licence \d{5}")

    result = _enhance_one(
        spacy_nlp_engine, text, recognizer, LemmaContextAwareEnhancer()
    )

    assert result.score == pytest.approx(expected_score)


@pytest.mark.parametrize("matching_mode", ["substring", "whole_word"])
def test_when_rejected_phrase_match_overlaps_a_valid_one_then_valid_one_counts(
    spacy_nlp_engine, matching_mode
):
    recognizer = _licence_recognizer(["test test"], r"^test")
    enhancer = LemmaContextAwareEnhancer(
        context_prefix_count=0,
        context_suffix_count=2,
        context_matching_mode=matching_mode,
    )

    result = _enhance_one(spacy_nlp_engine, "test test test", recognizer, enhancer)

    assert (result.start, result.end) == (0, 4)
    assert result.score == pytest.approx(0.65)


def test_when_window_ends_inside_a_word_then_whole_word_phrase_does_not_match(
    spacy_nlp_engine,
):
    # spaCy splits "10km" into "10" and "km", so the window ends after "10"
    recognizer = _licence_recognizer(["foo 10"])
    enhancer = LemmaContextAwareEnhancer(
        context_prefix_count=0,
        context_suffix_count=2,
        context_matching_mode="whole_word",
    )

    result = _enhance_one(spacy_nlp_engine, "ABC12345 foo 10km", recognizer, enhancer)

    assert result.score == pytest.approx(0.3)


@pytest.mark.parametrize("prefix_count, suffix_count", [(-1, 0), (5, -1), (-1, -1)])
def test_when_window_count_is_negative_then_no_error(
    spacy_nlp_engine, prefix_count, suffix_count
):
    recognizer = _licence_recognizer(["driving licence"])
    enhancer = LemmaContextAwareEnhancer(
        context_prefix_count=prefix_count, context_suffix_count=suffix_count
    )

    result = _enhance_one(
        spacy_nlp_engine, "driving licence ABC12345", recognizer, enhancer
    )

    expected = 0.65 if prefix_count >= 0 else 0.3
    assert result.score == pytest.approx(expected)


def test_when_single_word_context_also_matches_then_it_stays_supportive_word(
    spacy_nlp_engine,
):
    recognizer = _licence_recognizer(["driving licence", "licence"])

    result = _enhance_one(
        spacy_nlp_engine,
        "My driving licence is ABC12345",
        recognizer,
        LemmaContextAwareEnhancer(),
    )

    assert result.analysis_explanation.supportive_context_word == "licence"


def test_when_phrase_has_regex_characters_then_matched_literally():
    text = "my driver's lic. (uk) ABC12345"
    entity_start = text.index("ABC12345")

    found = LemmaContextAwareEnhancer._find_supportive_phrase_in_text(
        text, 0, entity_start, entity_start, len(text), ["driver's lic. (uk)"]
    )
    not_found = LemmaContextAwareEnhancer._find_supportive_phrase_in_text(
        text, 0, entity_start, entity_start, len(text), ["driver.s lic"]
    )

    assert found == "driver's lic. (uk)"
    assert not_found == ""


@pytest.mark.parametrize(
    "text, prefix_count, suffix_count",
    [
        ("Filed today: my driving licence number is ABC12345 and more text", 5, 0),
        ("Filed today: my driving licence number is ABC12345 and more text", 1, 2),
        ("ABC12345", 5, 5),
    ],
)
def test_context_window_span_covers_the_tokens_of_the_context_lemmas(
    spacy_nlp_engine, text, prefix_count, suffix_count
):
    nlp_artifacts = spacy_nlp_engine.process_text(text, "en")
    enhancer = LemmaContextAwareEnhancer(
        context_prefix_count=prefix_count, context_suffix_count=suffix_count
    )
    start = text.index("ABC12345")

    span_start, span_end = enhancer._get_context_window_span(
        nlp_artifacts, "ABC12345", start
    )
    words = enhancer._extract_surrounding_words(nlp_artifacts, "ABC12345", start)

    in_span = [
        token.lemma_.lower()
        for token in nlp_artifacts.tokens
        if span_start <= token.idx and token.idx + len(token) <= span_end
    ]
    assert set(words) == set(in_span) & set(nlp_artifacts.keywords)


def test_when_multi_word_context_precedes_entity_then_result_passes_threshold(
    spacy_nlp_engine,
):
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.predefined_recognizers import UkDrivingLicenceRecognizer

    registry = RecognizerRegistry(recognizers=[UkDrivingLicenceRecognizer()])
    engine = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)

    with_phrase = engine.analyze(
        "My driving licence number is MORGA753116SM9IJ.",
        language="en",
        score_threshold=0.6,
    )
    without_phrase = engine.analyze(
        "Reference MORGA753116SM9IJ was filed.", language="en", score_threshold=0.6
    )

    assert [(r.entity_type, r.start, r.end) for r in with_phrase] == [
        ("UK_DRIVING_LICENCE", 29, 45)
    ]
    assert with_phrase[0].score == pytest.approx(0.85)
    assert without_phrase == []
