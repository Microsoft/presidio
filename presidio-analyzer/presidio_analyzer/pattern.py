import json
from typing import Dict

import regex as re


class Pattern:
    """
    A class that represents a regex pattern.

    :param name: the name of the pattern
    :param regex: the regex pattern to detect
    :param score: the pattern's strength (values varies 0-1)
    """

    def __init__(self, name: str, regex: str, score: float):
        self.name = name
        self.regex = regex
        self.score = score
        self.compiled_regex = None
        self.compiled_with_flags = None

        self.__validate_regex(self.regex)
        self.__validate_score(self.score)

    @staticmethod
    def __validate_regex(pattern: str) -> None:
        """Validate that the regex pattern is valid."""
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

    @staticmethod
    def __validate_score(score: float) -> None:
        if score < 0 or score > 1:
            raise ValueError(f"Invalid score: {score}. Score should be between 0 and 1")

    def to_dict(self) -> Dict:
        """
        Turn this instance into a dictionary.

        :return: a dictionary
        """
        return_dict = {"name": self.name, "score": self.score, "regex": self.regex}
        return return_dict

    @classmethod
    def from_dict(cls, pattern_dict: Dict) -> "Pattern":
        """
        Load an instance from a dictionary.

        :param pattern_dict: a dictionary holding the pattern's parameters
        :return: a Pattern instance
        """
        return cls(**pattern_dict)

    def __repr__(self):
        """Return string representation of instance."""
        return json.dumps(self.to_dict())

    def __str__(self):
        """Return string representation of instance."""
        return json.dumps(self.to_dict())
