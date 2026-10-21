import pytest

from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    RecognizerResult,
    OperatorConfig,
    ConflictResolutionStrategy,
    EngineResult,
    OperatorResult,
)


@pytest.mark.parametrize(
    # fmt: off
    "text, analyzer_result1, analyzer_result2, conflict_strategy, expected_result",
    [
        (
            ("Fake card number 4151 3217 6243 3448.com "
             "that overlaps with nonexisting URL."),
            RecognizerResult("CREDIT_CARD", 17, 36, 0.8),
            RecognizerResult("URL", 32, 40, 0.8),
            ConflictResolutionStrategy.MERGE_SIMILAR_OR_CONTAINED,
            ("Fake card number 4151 3217 6243 34483448.com "
             "that overlaps with nonexisting URL.")
        ),
        (
            "Fake text with SSN 145-45-6789 and phone number 953-555-5555.",
            RecognizerResult("SSN", 19, 30, 0.85),
            RecognizerResult("PHONE_NUMBER", 48, 60, 0.95),
            None,
            "Fake text with SSN 145-45-6789 and phone number 953-555-5555."
        ),
    ]
    # fmt: on
)
def test_when_merge_similar_or_contained_selected_then_default_conflict_handled(
    text, analyzer_result1, analyzer_result2, conflict_strategy, expected_result
):
    engine = AnonymizerEngine()
    operator_config = OperatorConfig("keep")
    result = engine.anonymize(
        text,
        [analyzer_result1, analyzer_result2],
        {"DEFAULT": operator_config},
        conflict_resolution=conflict_strategy
    ).text

    assert result == expected_result


@pytest.mark.parametrize(
    # fmt: off
    "text, analyzer_results, conflict_strategy, expected_result",
    [
        # CREDIT_CARD Entity has higher score, so adjustment will occur at URL entity
        (
            (
                "Fake card number 4151 3217 6243 3448.com "
                "that overlaps with nonexisting URL."
            ),
            [
                RecognizerResult("CREDIT_CARD", 17, 36, 1),
                RecognizerResult("URL", 32, 40, 0.5)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text=(
                    "Fake card number 4151 3217 6243 3448.com "
                    "that overlaps with nonexisting URL."
                ),
                items=[
                    OperatorResult(17, 36, 'CREDIT_CARD',
                                   '4151 3217 6243 3448', 'keep'),
                    OperatorResult(36, 40, 'URL', '.com', 'keep')
                ]
            )
        ),
        # URL Entity has higher score, so adjustment will occur at CREDIT_CARD entity
        (
            (
                "Fake card number 4151 3217 6243 3448.com "
                "that overlaps with nonexisting URL."
            ),
            [
                RecognizerResult("CREDIT_CARD", 17, 36, 0.8),
                RecognizerResult("URL", 32, 40, 1)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text=(
                    "Fake card number 4151 3217 6243 3448.com "
                    "that overlaps with nonexisting URL."
                ),
                items=[
                    OperatorResult(17, 32, 'CREDIT_CARD', '4151 3217 6243 ', 'keep'),
                    OperatorResult(32, 40, 'URL', '3448.com', 'keep')
                ]
            )
        ),
        # Both entities has same score, so adjustment will occur at second entity
        (
            (
                "Fake card number 4151 3217 6243 3448.com "
                "that overlaps with nonexisting URL."
            ),
            [
                RecognizerResult("CREDIT_CARD", 17, 36, 0.8),
                RecognizerResult("URL", 32, 40, 0.8)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text=(
                    "Fake card number 4151 3217 6243 3448.com "
                    "that overlaps with nonexisting URL."
                ),
                items=[
                    OperatorResult(17, 36, 'CREDIT_CARD',
                                   '4151 3217 6243 3448', 'keep'),
                    OperatorResult(36, 40, 'URL', '.com', 'keep')
                ]
            )
        ),
        # More than one entity intersections
        (
            (
                "Fake card number 4151 3217 6243 3448.com "
                "that overlaps with nonexisting URL."
            ),
            [
                RecognizerResult("CREDIT_CARD", 17, 36, 0.8),
                RecognizerResult("URL", 28, 40, 0.8),
                RecognizerResult("Ent1", 31, 42, 0.9),
                RecognizerResult("Ent2", 25, 40, 0.8)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text=(
                    "Fake card number 4151 3217 6243 3448.com "
                    "that overlaps with nonexisting URL."
                ),
                items=[
                    OperatorResult(31, 42, 'Ent1', ' 3448.com t', 'keep'),
                    OperatorResult(17, 31, 'CREDIT_CARD', '4151 3217 6243',  'keep')
                ]
            )
        ),
        # A trim makes two results share a start; the lower-scored one is trimmed
        # after the other instead of being cut to zero length
        (
            "aaaaaaaaaabbbbbcccccdddd",
            [
                RecognizerResult("A", 0, 10, 0.9),
                RecognizerResult("B", 5, 15, 0.5),
                RecognizerResult("C", 8, 20, 0.4)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text="aaaaaaaaaabbbbbcccccdddd",
                items=[
                    OperatorResult(0, 10, 'A', 'aaaaaaaaaa', 'keep'),
                    OperatorResult(10, 15, 'B', 'bbbbb', 'keep'),
                    OperatorResult(15, 20, 'C', 'ccccc', 'keep')
                ]
            )
        ),
        # A result trimmed to nothing is dropped instead of being returned
        # as a zero-length item
        (
            "aaaaaaaaaaccccccccccdddd",
            [
                RecognizerResult("A", 0, 10, 0.9),
                RecognizerResult("B", 3, 12, 0.3),
                RecognizerResult("C", 8, 20, 0.5)
            ],
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            EngineResult(
                text="aaaaaaaaaaccccccccccdddd",
                items=[
                    OperatorResult(0, 10, 'A', 'aaaaaaaaaa', 'keep'),
                    OperatorResult(10, 20, 'C', 'cccccccccc', 'keep')
                ]
            )
        )

    ]
    # fmt: on
)
def test_when_remove_intersections_conflict_selected_then_all_conflicts_handled(
    text, analyzer_results, conflict_strategy, expected_result
):
    engine = AnonymizerEngine()
    operator_config = OperatorConfig("keep")
    conflict_strategy = conflict_strategy
    result = engine.anonymize(
        text,
        analyzer_results,
        {"DEFAULT": operator_config},
        conflict_resolution=conflict_strategy
    )

    assert result.text == expected_result.text
    assert sorted(result.items) == sorted(expected_result.items)


def test_when_same_type_results_intersect_in_a_chain_then_one_result_remains():
    text = "aaaaaaaaaaaa tail"
    results = [
        RecognizerResult("PERSON", 5, 9, 0.4),
        RecognizerResult("PERSON", 0, 6, 0.9),
        RecognizerResult("PERSON", 8, 12, 0.5),
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert result.text == "<PERSON> tail"
    assert [(item.start, item.end) for item in result.items] == [(0, 8)]


def test_when_same_type_results_touch_then_both_remain():
    text = "aaaaabbbb"
    results = [
        RecognizerResult("PERSON", 0, 5, 0.9),
        RecognizerResult("PERSON", 5, 9, 0.9),
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert result.text == "<PERSON><PERSON>"


def test_when_result_is_contained_in_another_type_then_it_is_dropped():
    text = "aaaaaaaaaa"
    results = [
        RecognizerResult("LOCATION", 2, 5, 0.9),
        RecognizerResult("PERSON", 0, 10, 0.3),
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert result.text == "<PERSON>"


def test_when_results_have_equal_indices_then_the_higher_score_remains():
    text = "aaaaa"
    results = [
        RecognizerResult("PERSON", 0, 5, 0.9),
        RecognizerResult("LOCATION", 0, 5, 0.4),
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert result.text == "<PERSON>"


def test_when_results_have_equal_indices_and_scores_then_the_last_one_remains():
    text = "aaaaa"
    results = [
        RecognizerResult("LOCATION", 0, 5, 0.8),
        RecognizerResult("PERSON", 0, 5, 0.8),
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert result.text == "<PERSON>"


def test_when_many_results_do_not_overlap_then_all_are_anonymized():
    count = 20000
    text = "x" * (count * 10)
    results = [
        RecognizerResult(f"E{index}", index * 10, index * 10 + 5, 1.0)
        for index in range(count)
    ]

    result = AnonymizerEngine().anonymize(text, results)

    assert len(result.items) == count
