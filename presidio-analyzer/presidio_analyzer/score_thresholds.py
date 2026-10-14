"""Validation helpers for recognizer score thresholds."""

from collections.abc import Mapping
from typing import Dict


def validate_score_threshold(threshold: object) -> float:
    """Validate a score threshold without coercing its input type.

    :param threshold: The value to validate.
    :return: The validated score threshold.
    """
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        raise ValueError(f"Score threshold must be numeric, got: {threshold}")
    if not 0.0 <= threshold <= 1.0:
        raise ValueError(
            f"Score threshold must be between 0.0 and 1.0, got: {threshold}"
        )
    return threshold


def normalize_score_thresholds(score_thresholds: object) -> Dict[str, float]:
    """Validate and defensively copy one recognizer's score thresholds.

    :param score_thresholds: The threshold mapping to validate.
    :return: A normalized copy of the score thresholds.
    """
    if score_thresholds is None:
        return {}
    if not isinstance(score_thresholds, Mapping):
        raise ValueError("score_thresholds must be a mapping")

    normalized = {}
    for entity, threshold in score_thresholds.items():
        if not isinstance(entity, str) or not entity or entity.strip() != entity:
            raise ValueError("score_thresholds keys must be non-empty strings")
        normalized[entity] = validate_score_threshold(threshold)
    return normalized
