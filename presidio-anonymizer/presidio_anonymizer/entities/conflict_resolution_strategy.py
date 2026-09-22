"""An Enum class designed to manage all types of conflicts among entities or text."""

from enum import Enum


class ConflictResolutionStrategy(Enum):
    """Conflict resolution strategy.

    The strategy to use when there is a conflict between two entities.

    MERGE_SIMILAR_OR_CONTAINED: This default strategy resolves conflicts
    between similar or contained entities.
    REMOVE_INTERSECTIONS: Effectively resolves both intersection conflicts
    among entities and default strategy conflicts. When two results overlap,
    the lower-scored one is trimmed to the part outside the higher-scored one
    (on equal scores, the one that starts first keeps the overlap). Results
    trimmed to nothing are dropped.
    KEEP_CONTAINED_WITH_HIGHER_SCORE: Gives every character to the highest scored
    entity covering it, so an entity contained in a lower scored one is kept and
    the containing entity is split around it. The other strategies always drop
    the contained entity, whatever its score.
    NONE: No conflict resolution will be performed.
    """

    MERGE_SIMILAR_OR_CONTAINED = "merge_similar_or_contained"
    REMOVE_INTERSECTIONS = "remove_intersections"
    KEEP_CONTAINED_WITH_HIGHER_SCORE = "keep_contained_with_higher_score"
