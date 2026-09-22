"""
RecognizerResult is an exact copy of the RecognizerResult object from presidio-analyzer.

Represents the findings of detected entity.
"""

import logging
from typing import Dict

from presidio_anonymizer.entities.engine import PIIEntity
from presidio_anonymizer.services.validators import validate_parameter_exists


class RecognizerResult(PIIEntity):
    """
    Recognizer Result represents the findings of the detected entity.

    Result of a recognizer analyzing the text.

    :param entity_type: the type of the entity
    :param start: the start location of the detected entity
    :param end: the end location of the detected entity
    :param score: the score of the detection
    """

    logger = logging.getLogger("presidio-anonymizer")

    def __init__(self, entity_type: str, start: int, end: int, score: float):
        PIIEntity.__init__(self, start, end, entity_type)
        self.score = score
        validate_parameter_exists(score, "analyzer result", "score")

    @classmethod
    def from_json(cls, data: Dict):
        """
        Create RecognizerResult from json.

        :param data: e.g. {
            "start": 24,
            "end": 32,
            "score": 0.8,
            "entity_type": "NAME"
        }
        :return: RecognizerResult
        """
        score = data.get("score")
        entity_type = data.get("entity_type")
        start = data.get("start")
        end = data.get("end")
        return cls(entity_type, start, end, score)

    def __gt__(self, other):
        """
        Check if one result is greater by using the results indices in the text.

        :param other: another RecognizerResult
        :return: bool
        """
        if self.start == other.start:
            return self.end > other.end
        return self.start > other.start

    def __eq__(self, other):
        """
        Check two results are equal by using all class fields.

        :param other: another RecognizerResult
        :return: bool
        """
        equal_type = self.entity_type == other.entity_type
        equal_score = self.score == other.score
        return self.equal_indices(other) and equal_type and equal_score

    def __hash__(self):
        """
        Hash the result data by using all class fields.

        :return: int
        """
        return hash(
            f"{str(self.start)} {str(self.end)} {str(self.score)} {self.entity_type}"
        )

    def __str__(self) -> str:
        """Return a string representation of the instance."""
        return (
            f"type: {self.entity_type}, "
            f"start: {self.start}, "
            f"end: {self.end}, "
            f"score: {self.score}"
        )

    def has_conflict(self, other, keep_contained_with_higher_score: bool = False):
        """
        Check if two recognizer results are conflicted or not.

        I have a conflict if:
        1. My indices are the same as the other and my score is lower.
        2. If my indices are contained in another.

        :param other: RecognizerResult
        :param keep_contained_with_higher_score: if True, being contained in
        another result is a conflict only when my score is not higher than the
        other result's score.
        :return:
        """
        if self.equal_indices(other):
            return self.score <= other.score
        if keep_contained_with_higher_score:
            return other.contains(self) and self.score <= other.score
        return other.contains(self)

    def contains(self, other):
        """
        Check if one result is contained or equal to another result.

        :param other: another RecognizerResult
        :return: bool
        """
        return self.start <= other.start and self.end >= other.end

    def equal_indices(self, other):
        """
        Check if the indices are equal between two results.

        :param other: another RecognizerResult
        :return:
        """
        return self.start == other.start and self.end == other.end

    def intersects(self, other) -> int:
        """
        Check if self intersects with a different RecognizerResult.

        :return: If intersecting, returns the number of
        intersecting characters.
        If not, returns 0
        """
        # if they do not overlap the intersection is 0
        if self.end < other.start or other.end < self.start:
            return 0

        # otherwise the intersection is min(end) - max(start)
        return min(self.end, other.end) - max(self.start, other.start)
