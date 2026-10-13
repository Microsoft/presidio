from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class PlPeselRecognizer(PatternRecognizer):
    """
    Recognize PESEL number using regex and checksum.

    For more information about PESEL: https://en.wikipedia.org/wiki/PESEL

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "pl"

    PATTERNS = [
        # The lookarounds reject 11 digits that are part of a longer number; \b
        # would also reject a PESEL glued to a letter, as in "PESEL44051401458".
        Pattern(
            "PESEL",
            r"(?<!\d)[0-9]{2}([02468][1-9]|[13579][012])"
            r"(0[1-9]|1[0-9]|2[0-9]|3[01])[0-9]{5}(?!\d)",
            0.4,
        ),
    ]

    CONTEXT = ["PESEL"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pl",
        supported_entity: str = "PL_PESEL",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        if len(pattern_text) != 11 or not pattern_text.isdigit():
            return False

        digits = [int(digit) for digit in pattern_text]
        weights = [1, 3, 7, 9, 1, 3, 7, 9, 1, 3]

        weighted_sum = sum(d * w for d, w in zip(digits[:10], weights))
        # PESEL check digit = (10 - weighted_sum % 10) % 10. See
        # https://en.wikipedia.org/wiki/PESEL#Check_digit
        check_digit = (10 - weighted_sum % 10) % 10

        return check_digit == digits[10]
