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


@pytest.mark.parametrize(
    # fmt: off
    "conflict_strategy, expected_result",
    [
        (
            ConflictResolutionStrategy.MERGE_SIMILAR_OR_CONTAINED,
            "Name: <ENTITY1> Word3"
        ),
        (
            ConflictResolutionStrategy.REMOVE_INTERSECTIONS,
            "Name: <ENTITY1> Word3"
        ),
        (
            ConflictResolutionStrategy.KEEP_CONTAINED_WITH_HIGHER_SCORE,
            "Name: <ENTITY2><ENTITY1> Word3"
        ),
    ]
    # fmt: on
)
def test_when_contained_entity_scores_higher_then_only_new_strategy_keeps_it(
    conflict_strategy, expected_result
):
    engine = AnonymizerEngine()
    analyzer_results = [
        RecognizerResult("ENTITY1", 6, 17, 0.1),
        RecognizerResult("ENTITY2", 6, 11, 1),
    ]
    result = engine.anonymize(
        "Name: Word1 Word2 Word3",
        analyzer_results,
        conflict_resolution=conflict_strategy
    ).text

    assert result == expected_result


@pytest.mark.parametrize(
    # fmt: off
    "analyzer_results, expected_result",
    [
        # The contained entity scores higher, so it is kept and the containing
        # entity is trimmed down to the text it does not share.
        (
            [
                RecognizerResult("ENTITY1", 6, 17, 0.1),
                RecognizerResult("ENTITY2", 6, 11, 1)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 11, 'ENTITY2', 'Word1', 'keep'),
                    OperatorResult(11, 17, 'ENTITY1', ' Word2', 'keep')
                ]
            )
        ),
        # The contained entity scores lower, so it is dropped as it is by the
        # other strategies.
        (
            [
                RecognizerResult("ENTITY1", 6, 17, 1),
                RecognizerResult("ENTITY2", 6, 11, 0.1)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 17, 'ENTITY1', 'Word1 Word2', 'keep')
                ]
            )
        ),
        # Equal indices are resolved by score, as in the other strategies.
        (
            [
                RecognizerResult("ENTITY1", 6, 11, 0.1),
                RecognizerResult("ENTITY2", 6, 11, 1)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 11, 'ENTITY2', 'Word1', 'keep')
                ]
            )
        ),
    ]
    # fmt: on
)
def test_when_keep_contained_with_higher_score_selected_then_spans_do_not_overlap(
    analyzer_results, expected_result
):
    engine = AnonymizerEngine()
    operator_config = OperatorConfig("keep")
    result = engine.anonymize(
        "Name: Word1 Word2 Word3",
        analyzer_results,
        {"DEFAULT": operator_config},
        conflict_resolution=(
            ConflictResolutionStrategy.KEEP_CONTAINED_WITH_HIGHER_SCORE
        )
    )

    assert result.text == expected_result.text
    assert sorted(result.items) == sorted(expected_result.items)


@pytest.mark.parametrize(
    # fmt: off
    "analyzer_results, expected_result",
    [
        # The contained entity shares neither boundary, so the containing entity
        # is split in two and the text on both sides of it stays anonymized.
        (
            [
                RecognizerResult("ENTITY1", 6, 23, 0.1),
                RecognizerResult("ENTITY2", 12, 17, 1)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 12, 'ENTITY1', 'Word1 ', 'keep'),
                    OperatorResult(12, 17, 'ENTITY2', 'Word2', 'keep'),
                    OperatorResult(17, 23, 'ENTITY1', ' Word3', 'keep')
                ]
            )
        ),
        # Nested containment: every entity keeps the text no higher scored entity
        # covers, so the two parts of the middle entity survive as well.
        (
            [
                RecognizerResult("ENTITY1", 6, 23, 0.1),
                RecognizerResult("ENTITY2", 11, 18, 0.5),
                RecognizerResult("ENTITY3", 12, 17, 0.9)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 11, 'ENTITY1', 'Word1', 'keep'),
                    OperatorResult(11, 12, 'ENTITY2', ' ', 'keep'),
                    OperatorResult(12, 17, 'ENTITY3', 'Word2', 'keep'),
                    OperatorResult(17, 18, 'ENTITY2', ' ', 'keep'),
                    OperatorResult(18, 23, 'ENTITY1', 'Word3', 'keep')
                ]
            )
        ),
        # Nested containment sharing a start, where trimming one boundary would
        # leave an entity covering no text at all.
        (
            [
                RecognizerResult("ENTITY1", 6, 23, 0.1),
                RecognizerResult("ENTITY2", 6, 17, 0.5),
                RecognizerResult("ENTITY3", 6, 11, 0.9)
            ],
            EngineResult(
                text="Name: Word1 Word2 Word3",
                items=[
                    OperatorResult(6, 11, 'ENTITY3', 'Word1', 'keep'),
                    OperatorResult(11, 17, 'ENTITY2', ' Word2', 'keep'),
                    OperatorResult(17, 23, 'ENTITY1', ' Word3', 'keep')
                ]
            )
        ),
    ]
    # fmt: on
)
def test_when_contained_entity_is_kept_then_containing_entity_is_split(
    analyzer_results, expected_result
):
    engine = AnonymizerEngine()
    operator_config = OperatorConfig("keep")
    result = engine.anonymize(
        "Name: Word1 Word2 Word3",
        analyzer_results,
        {"DEFAULT": operator_config},
        conflict_resolution=(
            ConflictResolutionStrategy.KEEP_CONTAINED_WITH_HIGHER_SCORE
        )
    )

    assert result.text == expected_result.text
    assert sorted(result.items) == sorted(expected_result.items)


@pytest.mark.parametrize(
    # fmt: off
    "analyzer_results",
    [
        # Contained entity sharing the start of the containing one.
        [
            RecognizerResult("ENTITY1", 6, 17, 0.1),
            RecognizerResult("ENTITY2", 6, 11, 1)
        ],
        # Contained entity sharing the end of the containing one.
        [
            RecognizerResult("ENTITY1", 6, 17, 0.1),
            RecognizerResult("ENTITY2", 12, 17, 1)
        ],
        # Contained entity sharing neither boundary.
        [
            RecognizerResult("ENTITY1", 6, 23, 0.1),
            RecognizerResult("ENTITY2", 12, 17, 1)
        ],
        # Nested containment.
        [
            RecognizerResult("ENTITY1", 6, 23, 0.1),
            RecognizerResult("ENTITY2", 11, 18, 0.5),
            RecognizerResult("ENTITY3", 12, 17, 0.9)
        ],
        # Containment and partial intersection together.
        [
            RecognizerResult("ENTITY1", 6, 17, 0.1),
            RecognizerResult("ENTITY2", 12, 15, 1),
            RecognizerResult("ENTITY3", 14, 23, 0.5)
        ],
    ]
    # fmt: on
)
def test_when_keep_contained_with_higher_score_selected_then_flagged_text_is_covered(
    analyzer_results
):
    engine = AnonymizerEngine()
    operator_config = OperatorConfig("keep")
    result = engine.anonymize(
        "Name: Word1 Word2 Word3",
        analyzer_results,
        {"DEFAULT": operator_config},
        conflict_resolution=(
            ConflictResolutionStrategy.KEEP_CONTAINED_WITH_HIGHER_SCORE
        )
    )

    flagged_indices = set()
    for analyzer_result in analyzer_results:
        flagged_indices.update(range(analyzer_result.start, analyzer_result.end))
    anonymized_indices = set()
    for item in result.items:
        anonymized_indices.update(range(item.start, item.end))

    assert anonymized_indices == flagged_indices
    assert all(item.start < item.end for item in result.items)
