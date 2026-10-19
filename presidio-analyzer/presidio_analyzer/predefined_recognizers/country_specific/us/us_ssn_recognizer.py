from collections import defaultdict
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsSsnRecognizer(PatternRecognizer):
    """Recognize US Social Security Number (SSN) using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern("SSN1 (very weak)", r"\b([0-9]{5})-([0-9]{4})\b", 0.05),
        Pattern("SSN2 (very weak)", r"\b([0-9]{3})-([0-9]{6})\b", 0.05),
        Pattern("SSN3 (very weak)", r"\b(([0-9]{3})-([0-9]{2})-([0-9]{4}))\b", 0.05),
        Pattern("SSN4 (very weak)", r"\b[0-9]{9}\b", 0.05),
        Pattern("SSN5 (medium)", r"\b([0-9]{3})[- .]([0-9]{2})[- .]([0-9]{4})\b", 0.5),
    ]

    CONTEXT = [
        "social",
        "security",
        # "sec", # Task #603: Support keyphrases ("social sec")
        "ssn",
        "ssns",
        # "ssn#",  # iss:1452 - a # does not work with LemmaContextAwareEnhancer
        # "ss#",  # iss:1452 - a # does not work with LemmaContextAwareEnhancer
        "ssid",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_SSN",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be validated as a US_SSN entity.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        # if there are delimiters, make sure both delimiters are the same
        delimiter_counts = defaultdict(int)
        for c in pattern_text:
            if c in (".", "-", " "):
                delimiter_counts[c] += 1
        if len(delimiter_counts.keys()) > 1:
            # mismatched delimiters
            return True

        only_digits = "".join(c for c in pattern_text if c.isdigit())
        if all(only_digits[0] == c for c in only_digits):
            # cannot be all same digit
            return True

        if only_digits[3:5] == "00" or only_digits[5:] == "0000":
            # groups cannot be all zeros
            return True

        area_number = only_digits[:3]
        if area_number in ("000", "666") or area_number.startswith("9"):
            # area number (first group) is never issued by the SSA
            return True

        if only_digits in ("123456789", "078051120"):
            # canonical sample/placeholder SSNs published for examples
            return True

        return False
