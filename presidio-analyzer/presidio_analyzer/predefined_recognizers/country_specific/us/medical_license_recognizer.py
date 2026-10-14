from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer

# https://www.meditec.com/blog/dea-numbers-what-do-they-mean


class MedicalLicenseRecognizer(PatternRecognizer):
    """
    Recognize common Medical license numbers using regex + checksum.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "USA DEA Certificate Number (weak)",
            r"\b(?:[abcdefghjklmprstuxABCDEFGHJKLMPRSTUX]{1}[a-zA-Z]{1}\d{7}|"
            r"[abcdefghjklmprstuxABCDEFGHJKLMPRSTUX]{1}9\d{7})\b",
            0.4,
        ),
    ]

    CONTEXT = ["medical", "certificate", "DEA"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "MEDICAL_LICENSE",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
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

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        checksum = self.__luhn_checksum(sanitized_value)

        return checksum

    @staticmethod
    def __luhn_checksum(sanitized_value: str) -> bool:
        def digits_of(n: str) -> List[int]:
            return [int(dig) for dig in str(n)]

        digits = digits_of(sanitized_value[2:])
        checksum = digits.pop()
        even_digits = digits[-1::-2]
        odd_digits = digits[-2::-2]
        checksum *= -1
        checksum += 2 * sum(even_digits) + sum(odd_digits)
        return checksum % 10 == 0
