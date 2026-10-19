import pytest
from presidio_analyzer.context_aware_enhancers import LemmaContextAwareEnhancer
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import KrRrnRecognizer

from tests import assert_result_within_score_range


@pytest.fixture(scope="module")
def recognizer():
    return KrRrnRecognizer()

@pytest.fixture(scope="module")
def entities():
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
        
        # Valid RRNs, strong match by validate_result()
        ("960121-1021413", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("9601211021413", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("050912-2000019", 1, ((0, 14),), ((1.0, 1.0),), ),
        ("0509122000019", 1, ((0, 13),), ((1.0, 1.0),), ),
        ("His RRN is 9601211021413", 1, ((11, 24),), ((1.0, 1.0),), ),
        
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


def test_when_korean_context_terms_then_present_in_context(recognizer):
    """Korean terms must be in context so enhancement can fire on Korean text."""
    for korean_term in ["주민등록번호", "주민번호", "신분증", "본인인증"]:
        assert korean_term in recognizer.context


@pytest.mark.parametrize(
    "text, start, end",
    [
        # context term before the number: the default prefix window
        ("주민등록번호 960121-1021413 확인 부탁드립니다", 7, 21),
        # context term after the number: the suffix window, off by default
        ("960121-1021413 주민번호로 본인인증 완료", 0, 14),
    ],
)
def test_when_korean_context_on_either_side_then_pattern_match_is_kept(
    text, start, end, recognizer, entities
):
    """Korean context text on either side must not disturb the match itself."""
    results = recognizer.analyze(text, entities)
    assert len(results) == 1
    assert_result_within_score_range(
        results[0], entities[0], start, end, 1.0, 1.0
    )


@pytest.mark.parametrize(
    "korean_term", ["주민등록번호", "주민번호", "신분증", "본인인증"]
)
def test_when_korean_context_term_is_supplied_then_score_is_boosted(
    korean_term, recognizer, entities
):
    """Each new Korean term must actually raise the score through the enhancer.

    Context taken from the surrounding text needs a Korean NLP model, which
    the test environment does not ship, so the boost is exercised through the
    explicit ``context`` argument, the same way ``test_context_support`` does.
    A checksum-invalid number is used so there is room above the base score.
    """
    text = "960121-1234567"
    engine = NoOpNlpEngine(models=[{"lang_code": "ko", "model_name": "no_op"}])
    engine.load()
    nlp_artifacts = engine.process_text(text, "ko")
    raw = recognizer.analyze(text, entities, nlp_artifacts)
    enhancer = LemmaContextAwareEnhancer()

    without = enhancer.enhance_using_context(text, raw, nlp_artifacts, [recognizer])
    boosted = enhancer.enhance_using_context(
        text, raw, nlp_artifacts, [recognizer], [korean_term]
    )

    assert without[0].score == 0.5
    assert boosted[0].score == pytest.approx(0.85)
    assert boosted[0].analysis_explanation.supportive_context_word == korean_term
