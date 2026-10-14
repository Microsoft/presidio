from typing import Dict, Optional

from presidio_anonymizer.entities import PIIEntity


class OperatorResult(PIIEntity):
    """A class to hold data for engines results either anonymize or deanonymize."""

    def __init__(
        self,
        start: int,
        end: int,
        entity_type: str,
        text: str = None,
        operator: str = None,
        score: Optional[float] = None,
    ):
        PIIEntity.__init__(self, start, end, entity_type)
        self.text = text
        self.operator = operator
        self.score = score

    def __repr__(self):
        """Return a string representation of the object."""
        return str(self.to_dict())

    def to_dict(self) -> Dict:
        """Return object as Dict."""
        return dict(self.__dict__)

    def __str__(self):
        """Return a string representation of the object."""
        return str(self.to_dict())

    def __eq__(self, other: "OperatorResult") -> bool:
        """
        Verify two OperatorResults are equal.

        :param other: OperatorResult
        :return: bool
        """
        return (
            self.start == other.start
            and self.end == other.end
            and self.entity_type == other.entity_type
            and self.operator == other.operator
            and self.text == other.text
        )

    @classmethod
    def from_json(cls, json: Dict) -> "OperatorResult":
        """
        Create OperatorResult from user json.

        :param json: json representation for this operator result. For example:
        {
            "start": 0,
            "end": 10,
            "key": "1111111111111111",
            "entity_type":"PERSON",
            "text":"resulted_text",
            "operator":"encrypt",
            "score": 0.85
        }
        """
        start = json.get("start")
        end = json.get("end")
        entity_type = json.get("entity_type")
        text = json.get("text")
        operator = json.get("operator")
        score = json.get("score")
        return cls(
            start=start,
            end=end,
            entity_type=entity_type,
            text=text,
            operator=operator,
            score=float(score) if score is not None else None,
        )
