import pytest
from presidio_analyzer.predefined_recognizers import KrRrnRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    """Return KrRrnRecognizer instance."""
    return KrRrnRecognizer()


@pytest.fixture(scope="module")
def entities():
    """Return supported entity list."""
    return ["KR_RRN"]


@pytest.mark.parametrize(
    "text, expected_len, expected_positions, expected_score_ranges",
    [
        # Valid RRNs, but medium match
        ("960121-1234567", 1, ((0, 14),), ((0.5, 0.5),), ),
        ("9601211234567", 1, ((0, 13),), ((0.5, 0.5),), ),
        ("000505-3637892", 1, ((0, 14),), ((0.5, 0.5),), ),
        ("0005053637892", 1, ((0, 13),), ((0.5, 0.5),), ),
        ("His Korean RRN is 960121-1234567", 1, ((18, 32),), ((0.5, 0.5),), ),
        ("주민등록번호: 960121-1234567", 1, ((8, 22),), ((0.5, 0.5),), ),
        ("신분증 확인: 960121-1234567", 1, ((8, 22),), ((0.5, 0.5),), ),
        ("본인인증 960121-1234567", 1, ((5, 19),), ((0.5, 0.5),), ),

        # Valid RRNs, strong match by validate_result()
        ("960121-1021413", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("9601211021413", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("050912-2000019", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("0509122000019", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("His RRN is 9601211021413", 1, ((11, 24),), ((1.0, 1.0),), ),
        ("주민번호는 9601211021413입니다", 1, ((6, 19),), ((1.0, 1.0),), ),

        # Invalid RRNs
        ("001332-1234567", 0, (), (),),
        ("0013321234567", 0, (), (),),
        ("960121+1021413", 0, (), (),),
        ("960111-10214131", 0, (), (),),
        ("960303-0021413", 0, (), (),),
        ("760413-5212134", 0, (), (),),
        ("000402-6214431", 0, (), (),),
        ("051102-9234110", 0, (), (),),
    ],
)
def test_when_all_rrns_then_succeed(
    text,
    expected_len,
    expected_positions,
    expected_score_ranges,
    recognizer,
    entities,
    max_score,
):
    """Test recognition and validation of Korean RRN across valid and invalid inputs."""
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


def test_korean_context_keywords_in_rrn_recognizer(recognizer):
    """Test that Korean context keywords are present in KrRrnRecognizer.context."""
    expected_korean_keywords = [
        "주민등록번호",
        "주민번호",
        "주민등록증",
        "주민등록",
        "신분증",
        "본인인증",
    ]
    for keyword in expected_korean_keywords:
        assert keyword in recognizer.context


@pytest.mark.parametrize(
    "context_word",
    ["주민등록번호", "주민번호", "주민등록증", "주민등록", "신분증", "본인인증"],
)
def test_when_korean_context_used_then_score_enhanced(recognizer, context_word):
    """Test that Korean context keywords enhance confidence score from 0.5 to 0.85."""
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    from presidio_analyzer.nlp_engine import NlpArtifacts

    text = f"{context_word} 960121-1234567"
    results = recognizer.analyze(text, ["KR_RRN"])
    assert len(results) == 1
    assert results[0].score == 0.5

    tokens = [context_word, "960121-1234567"]
    tokens_indices = [0, len(context_word) + 1]
    artifacts = NlpArtifacts(
        entities=[],
        tokens=tokens,
        tokens_indices=tokens_indices,
        lemmas=tokens,
        nlp_engine=None,
        language="ko",
    )
    artifacts.keywords = [context_word, "960121-1234567"]

    enhancer = LemmaContextAwareEnhancer()
    enhanced_results = enhancer.enhance_using_context(
        text, results, artifacts, [recognizer]
    )

    assert len(enhanced_results) == 1
    assert enhanced_results[0].score == 0.85
    assert (
        enhanced_results[0].analysis_explanation.supportive_context_word
        == context_word
    )


def test_when_no_korean_context_then_score_not_enhanced(recognizer):
    """Test that unrelated context does not enhance confidence score."""
    from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
    from presidio_analyzer.nlp_engine import NlpArtifacts

    text = "random text 960121-1234567"
    results = recognizer.analyze(text, ["KR_RRN"])
    assert len(results) == 1
    assert results[0].score == 0.5

    tokens = ["random", "text", "960121-1234567"]
    tokens_indices = [0, 7, 12]
    artifacts = NlpArtifacts(
        entities=[],
        tokens=tokens,
        tokens_indices=tokens_indices,
        lemmas=tokens,
        nlp_engine=None,
        language="ko",
    )
    artifacts.keywords = ["random", "text", "960121-1234567"]

    enhancer = LemmaContextAwareEnhancer()
    enhanced_results = enhancer.enhance_using_context(
        text, results, artifacts, [recognizer]
    )

    assert len(enhanced_results) == 1
    assert enhanced_results[0].score == 0.5
    assert (
        enhanced_results[0].analysis_explanation.supportive_context_word == ""
    )
