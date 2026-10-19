import json
from typing import Dict, Mapping, Optional, Union

import regex as re


class Pattern:
    """
    A class that represents a regex pattern.

    :param name: the name of the pattern
    :param regex: the regex pattern to detect
    :param score: the pattern's strength (values varies 0-1)
    :param capture_group: optional number or name of a capture group in the
    regex. If set, the span of this group is detected instead of the whole
    match, and matches in which the group does not participate are skipped.
    Defaults to None (the whole match).
    """

    def __init__(
        self,
        name: str,
        regex: str,
        score: float,
        capture_group: Optional[Union[int, str]] = None,
    ):
        self.name = name
        self.regex = regex
        self.score = score
        self.capture_group = capture_group
        self.compiled_regex = None
        self.compiled_with_flags = None

        self.__validate_regex(self.regex, self.capture_group)
        self.__validate_score(self.score)

    @staticmethod
    def __validate_regex(
        pattern: str, capture_group: Optional[Union[int, str]]
    ) -> None:
        """Validate that the regex pattern is valid and defines the capture group."""
        try:
            compiled_regex = re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        if capture_group is not None:
            Pattern.__validate_capture_group(
                capture_group, compiled_regex.groups, compiled_regex.groupindex
            )

    @staticmethod
    def __validate_capture_group(
        capture_group: Union[int, str], groups: int, groupindex: Mapping[str, int]
    ) -> None:
        if isinstance(capture_group, bool) or not isinstance(capture_group, (int, str)):
            raise ValueError(
                "capture_group must be an int or a str, "
                f"got {type(capture_group).__name__}"
            )
        if isinstance(capture_group, str):
            if capture_group not in groupindex:
                raise ValueError(
                    f"capture_group {capture_group!r} is not a named group "
                    f"in the regex. Named groups: {list(groupindex)}"
                )
        elif capture_group < 0:
            raise ValueError(
                f"capture_group must be a non-negative integer, got {capture_group}"
            )
        elif capture_group > groups:
            raise ValueError(
                f"capture_group {capture_group} is out of range: "
                f"regex defines {groups} capture group(s)"
            )

    @staticmethod
    def __validate_score(score: float) -> None:
        if score < 0 or score > 1:
            raise ValueError(
                f"Invalid score: {score}. " "Score should be between 0 and 1"
            )

    def to_dict(self) -> Dict:
        """
        Turn this instance into a dictionary.

        :return: a dictionary
        """
        return_dict = {"name": self.name, "score": self.score, "regex": self.regex}
        if self.capture_group is not None:
            return_dict["capture_group"] = self.capture_group
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
