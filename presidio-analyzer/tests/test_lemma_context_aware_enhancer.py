import pytest
import spacy
from presidio_analyzer import LemmaContextAwareEnhancer, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import NlpArtifacts


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


def _korean_nlp_artifacts():
    """Build NLP artifacts for a Korean sentence as ko_core_news_sm produces them.

    The Korean spaCy lemmatizer joins morphemes with "+" and can split a word
    inside a context term: ko_core_news_sm 3.8.0 lemmatizes "외국인등록번호는"
    as "외국인등록번+호는", which no longer contains "외국인등록번호".
    """
    nlp = spacy.blank(
        "ko", config={"nlp": {"tokenizer": {"@tokenizers": "spacy.Tokenizer.v1"}}}
    )
    doc = nlp("외국인등록번호는 900101-5234567")
    nlp_artifacts = NlpArtifacts(
        entities=[],
        tokens=doc,
        tokens_indices=[token.idx for token in doc],
        lemmas=["외국인등록번+호는", "900101", "-", "5234567"],
        nlp_engine=None,
        language="ko",
    )
    nlp_artifacts.keywords = ["외국인등록번+호는", "900101", "5234567"]
    return nlp_artifacts


def _korean_recognizer():
    return PatternRecognizer(
        supported_entity="KR_FRN",
        supported_language="ko",
        patterns=[Pattern("frn", r"\d{6}-\d{7}", 0.5)],
        context=["외국인등록번호"],
    )


def test_when_lemma_splits_korean_context_word_then_token_text_finds_it():
    """Test that token text finds a context word the Korean lemma splits."""
    nlp_artifacts = _korean_nlp_artifacts()
    recognizer = _korean_recognizer()
    text = nlp_artifacts.tokens.text
    raw_results = recognizer.analyze(text, ["KR_FRN"], nlp_artifacts)

    default = LemmaContextAwareEnhancer().enhance_using_context(
        text, raw_results, nlp_artifacts, [recognizer]
    )
    token_text = LemmaContextAwareEnhancer(
        token_text_languages=["ko"]
    ).enhance_using_context(text, raw_results, nlp_artifacts, [recognizer])

    assert default[0].score == 0.5
    assert token_text[0].score == pytest.approx(0.85)
    explanation = token_text[0].analysis_explanation
    assert explanation.supportive_context_word == "외국인등록번호"


def test_when_language_not_in_token_text_languages_then_lemmas_are_used():
    """Test that languages not listed in token_text_languages keep using lemmas."""
    doc = spacy.blank("en")("credit cards 4111111111111111")
    lemmas = ["credit", "card", "4111111111111111"]
    nlp_artifacts = NlpArtifacts(
        entities=[],
        tokens=doc,
        tokens_indices=[token.idx for token in doc],
        lemmas=lemmas,
        nlp_engine=None,
        language="en",
    )
    nlp_artifacts.keywords = lemmas
    recognizer = PatternRecognizer(
        supported_entity="CARD",
        patterns=[Pattern("card", r"\d{16}", 0.5)],
        context=["card"],
    )
    raw_results = recognizer.analyze(doc.text, ["CARD"], nlp_artifacts)

    enhancer = LemmaContextAwareEnhancer(
        context_matching_mode="whole_word", token_text_languages=["ko"]
    )
    results = enhancer.enhance_using_context(
        doc.text, raw_results, nlp_artifacts, [recognizer]
    )

    # "card" matches the lemma of "cards", which only the lemma path can see
    assert results[0].score == pytest.approx(0.85)


def test_when_token_text_is_used_then_nlp_artifacts_are_not_modified():
    """Test that the token-text swap leaves the caller's NLP artifacts unchanged."""
    nlp_artifacts = _korean_nlp_artifacts()
    recognizer = _korean_recognizer()
    text = nlp_artifacts.tokens.text
    raw_results = recognizer.analyze(text, ["KR_FRN"], nlp_artifacts)

    LemmaContextAwareEnhancer(token_text_languages=["ko"]).enhance_using_context(
        text, raw_results, nlp_artifacts, [recognizer]
    )

    assert nlp_artifacts.lemmas == ["외국인등록번+호는", "900101", "-", "5234567"]
    assert nlp_artifacts.keywords == ["외국인등록번+호는", "900101", "5234567"]
