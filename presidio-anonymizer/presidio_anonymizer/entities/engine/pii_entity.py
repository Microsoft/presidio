import logging
from abc import ABC

from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.services.validators import (
    validate_parameter_exists,
    validate_parameter_not_empty,
    validate_type,
)


class PIIEntity(ABC):
    """Abstract class to hold the text we are going to operate on metadata."""

    logger = logging.getLogger("presidio-anonymizer")

    def __init__(self, start: int, end: int, entity_type: str):
        self.start = start
        self.end = end
        self.entity_type = entity_type
        self.__validate_fields()

    def __repr__(self):
        """Return a string representation of the object."""
        repr_str = (
            f"start: {self.start}, "
            f"end: {self.end}, "
            f"entity_type: {self.entity_type}"
        )
        score = getattr(self, "score", None)
        if score is not None:
            repr_str = repr_str + f", score: {score}"
        return repr_str

    def __gt__(self, other):
        """Check one entity is greater then other by the text end index."""
        return self.start > other.start

    def __eq__(self, other):
        """Check two text metadata entities are equal."""
        return (
            self.start == other.start
            and self.end == other.end
            and self.entity_type == other.entity_type
        )

    def __validate_fields(self):
        validate_parameter_exists(self.start, "result", "start")
        validate_type(self.start, "start", int)
        validate_parameter_exists(self.end, "result", "end")
        validate_type(self.end, "end", int)
        validate_parameter_not_empty(self.entity_type, "result", "entity_type")
        if self.start < 0 or self.end < 0:
            raise InvalidParamError(
                "Invalid input, result start and end must be positive"
            )
        if self.start > self.end:
            raise InvalidParamError(
                f"Invalid input, start index '{self.start}' "
                f"must be smaller than end index '{self.end}'"
            )
