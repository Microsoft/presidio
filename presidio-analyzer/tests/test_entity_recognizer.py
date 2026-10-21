# ruff: noqa: D103,E501,I001

import pytest

from presidio_analyzer import AnalysisExplanation, EntityRecognizer, RecognizerResult


def test_when_to_dict_then_return_correct_dictionary():
    ent_recognizer = EntityRecognizer(["ENTITY"])
    entity_rec_dict = ent_recognizer.to_dict()

    assert entity_rec_dict is not None
    assert entity_rec_dict["supported_entities"] == ["ENTITY"]
    assert entity_rec_dict["supported_language"] == "en"


def test_when_from_dict_then_returns_instance():
    ent_rec_dict = {"supported_entities": ["A", "B", "C"], "supported_language": "he"}
    entity_rec = EntityRecognizer.from_dict(ent_rec_dict)

    assert entity_rec.supported_entities == ["A", "B", "C"]
    assert entity_rec.supported_language == "he"
    assert entity_rec.version == "0.0.1"


def test_when_remove_duplicates_duplicates_removed():
    # test same result with different score will return only the highest
    arr = [
        RecognizerResult(
            start=0,
            end=5,
            score=0.1,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 1
    assert results[0].score == 0.5


def test_when_remove_duplicates_different_then_entity_not_removed():
    # test same result with different score will return only the highest
    arr = [
        RecognizerResult(
            start=0,
            end=5,
            score=0.1,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="y",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 2


def test_when_remove_duplicates_contained_shorter_length_results_removed():
    arr = [
        RecognizerResult(
            start=0,
            end=10,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
        RecognizerResult(
            start=0,
            end=5,
            score=0.5,
            entity_type="x",
            analysis_explanation=AnalysisExplanation(
                recognizer="test",
                original_score=0,
                pattern_name="test",
                pattern="test",
                validation_result=None,
            ),
        ),
    ]
    results = EntityRecognizer.remove_duplicates(arr)
    assert len(results) == 1


def test_when_higher_score_result_contains_lower_score_then_contained_removed():
    outer = RecognizerResult(entity_type="x", start=0, end=10, score=0.9)
    inner = RecognizerResult(entity_type="x", start=2, end=8, score=0.5)

    results = EntityRecognizer.remove_duplicates([inner, outer])

    assert results == [outer]


def test_when_higher_score_result_is_contained_by_lower_score_then_both_kept():
    inner = RecognizerResult(entity_type="x", start=2, end=8, score=0.9)
    outer = RecognizerResult(entity_type="x", start=0, end=10, score=0.5)

    results = EntityRecognizer.remove_duplicates([outer, inner])

    assert results == [inner, outer]


def test_when_results_partially_overlap_then_both_kept():
    first = RecognizerResult(entity_type="x", start=0, end=5, score=0.5)
    second = RecognizerResult(entity_type="x", start=3, end=8, score=0.5)

    results = EntityRecognizer.remove_duplicates([second, first])

    assert results == [first, second]


def test_when_contained_results_have_different_types_then_both_kept():
    outer = RecognizerResult(entity_type="x", start=0, end=10, score=0.5)
    inner = RecognizerResult(entity_type="y", start=2, end=8, score=0.5)

    results = EntityRecognizer.remove_duplicates([inner, outer])

    assert results == [outer, inner]


def test_when_entity_type_is_missing_then_remove_duplicates_does_not_raise():
    result_without_type = RecognizerResult.from_json(
        {"start": 0, "end": 5, "score": 0.5}
    )
    person = RecognizerResult(entity_type="PERSON", start=10, end=15, score=0.9)

    results = EntityRecognizer.remove_duplicates([result_without_type, person])

    assert results == [person, result_without_type]


def test_when_results_have_same_end_then_contained_result_removed():
    outer = RecognizerResult(entity_type="x", start=0, end=10, score=0.5)
    inner = RecognizerResult(entity_type="x", start=5, end=10, score=0.5)

    results = EntityRecognizer.remove_duplicates([inner, outer])

    assert results == [outer]


def test_when_result_score_is_zero_then_result_removed():
    zero_score = RecognizerResult(entity_type="x", start=0, end=5, score=0)
    nonzero_score = RecognizerResult(entity_type="x", start=10, end=15, score=0.5)

    results = EntityRecognizer.remove_duplicates([zero_score, nonzero_score])

    assert results == [nonzero_score]


def test_when_results_are_empty_then_empty_list_returned():
    assert EntityRecognizer.remove_duplicates([]) == []


def test_when_results_are_exact_duplicates_then_one_result_kept():
    first = RecognizerResult(entity_type="x", start=0, end=5, score=0.5)
    second = RecognizerResult(entity_type="x", start=0, end=5, score=0.5)

    results = EntityRecognizer.remove_duplicates([first, second])

    assert len(results) == 1
    assert results[0] == first


def test_when_results_are_kept_then_returned_in_priority_order():
    high_score = RecognizerResult(entity_type="x", start=10, end=12, score=0.9)
    shorter = RecognizerResult(entity_type="y", start=2, end=5, score=0.5)
    longer = RecognizerResult(entity_type="z", start=2, end=8, score=0.5)

    results = EntityRecognizer.remove_duplicates([shorter, high_score, longer])

    assert results == [high_score, longer, shorter]


def test_when_results_do_not_overlap_then_no_containment_checks(monkeypatch):
    def fail_if_contained_in_is_called(*_args):
        pytest.fail("contained_in should not be called for non-overlapping results")

    monkeypatch.setattr(
        RecognizerResult,
        "contained_in",
        fail_if_contained_in_is_called,
    )

    results = [
        RecognizerResult(
            entity_type="x",
            start=i * 10,
            end=i * 10 + 9,  # no overlap between results
            score=0.5,
        )
        for i in range(20_000)
    ]

    results = EntityRecognizer.remove_duplicates(results)

    assert len(results) == 20_000


sanitizer_test_set = [
    ["  a|b:c       ::-", [("-", ""), (" ", ""), (":", ""), ("|", "")], "abc"],
    ["def", "", "def"],
]


@pytest.mark.parametrize("input_text, params, expected_output", sanitizer_test_set)
def test_sanitize_value(input_text, params, expected_output):
    """
    Test to assert sanitize_value functionality from base class.

    :param input_text: input string
    :param params: List of tuples, indicating what has to be sanitized with which
    :param expected_output: sanitized value
    :return: True/False
    """
    assert EntityRecognizer.sanitize_value(input_text, params) == expected_output


def test_score_thresholds_default_to_empty_mapping():
    recognizer = EntityRecognizer(["ENTITY"])

    assert recognizer.score_thresholds == {}


def test_score_thresholds_constructor_and_setter_defensively_copy():
    thresholds = {"default": 0.4, "ENTITY": 0.7}
    recognizer = EntityRecognizer(["ENTITY"], score_thresholds=thresholds)
    thresholds["ENTITY"] = 0.1
    returned = recognizer.score_thresholds
    returned["ENTITY"] = 0.2

    assert recognizer.score_thresholds == {"default": 0.4, "ENTITY": 0.7}

    recognizer.score_thresholds = {"ENTITY": 0.5}
    assert recognizer.score_thresholds == {"ENTITY": 0.5}


@pytest.mark.parametrize("thresholds", [False, True, 0, "", "0.4", []])
def test_score_thresholds_reject_non_mapping_values(thresholds):
    with pytest.raises(ValueError, match="must be a mapping"):
        EntityRecognizer(["ENTITY"], score_thresholds=thresholds)


@pytest.mark.parametrize(
    "thresholds",
    [
        {"ENTITY": False},
        {"ENTITY": "0.4"},
        {"ENTITY": -0.1},
        {"ENTITY": 1.1},
        {"": 0.4},
        {" ENTITY": 0.4},
    ],
)
def test_score_thresholds_reject_invalid_entries(thresholds):
    with pytest.raises(ValueError):
        EntityRecognizer(["ENTITY"], score_thresholds=thresholds)
