from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class PkCnicRecognizer(PatternRecognizer):
    """
    Recognizes Pakistani Computerised National Identity Card number ("CNIC").

    The CNIC is a 13 digit unique number issued to each citizen by the
    National Database and Registration Authority (NADRA). It is written in
    the format 35202-1234567-1: five digits, a dash, seven digits, a dash and
    one digit. The first digit is a province or region code from 1 to 7
    (1 Khyber Pakhtunkhwa, 2 FATA, 3 Punjab, 4 Sindh, 5 Balochistan,
    6 Islamabad Capital Territory, 7 Gilgit-Baltistan and Azad Kashmir).
    The CNIC has no checksum, so this recognizer identifies it using regex,
    context words and sanity checks on the digits.

    Reference: https://en.wikipedia.org/wiki/Computerised_National_Identity_Card

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "pk"

    PATTERNS = [
        Pattern(
            "CNIC (strong)",
            r"\b[1-7][0-9]{4}-[0-9]{7}-[0-9]\b",
            0.65,
        ),
        Pattern(
            "CNIC (weak)",
            r"\b[1-7][0-9]{12}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "cnic",
        "national identity card",
        "computerized national identity card",
        "identity card",
        "nadra",
        "pakistan",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PK_CNIC",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.replacement_pairs = (
            replacement_pairs if replacement_pairs else [("-", ""), (" ", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be validated as a PK_CNIC entity.

        The CNIC has no checksum, so invalidation is based on sanity checks:
        the sanitized value must be 13 digits, start with a province or
        region code from 1 to 7, and not be a trivial number such as all
        digits being the same or a sequential run of digits.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        if len(sanitized_value) != 13 or not sanitized_value.isnumeric():
            return True
        if int(sanitized_value[0]) not in range(1, 8):
            return True
        if len(set(sanitized_value)) == 1:
            # cannot be all the same digit
            return True
        if self._is_sequential(sanitized_value):
            # cannot be a trivially sequential run of digits
            return True
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 1234567890123 ascends by one each step, and
        9876543210987 descends by one each step.

        :param digits: Numeric string to check
        :return: True if every digit follows the previous one sequentially
        """
        values = [int(digit) for digit in digits]
        ascending = all(
            (values[i] + 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        descending = all(
            (values[i] - 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        return ascending or descending
