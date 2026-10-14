from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ZaPassportRecognizer(PatternRecognizer):
    """
    Recognize South African passport numbers using regex and validation.

    South African passport numbers are 9 characters: one letter prefix
    (A, D, M, or T) followed by 8 digits.

    Reference:
    https://en.wikipedia.org/wiki/South_African_passport

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    PASSPORT_LENGTH = 9
    ALLOWED_PREFIXES = frozenset({"A", "D", "M", "T"})

    PATTERNS = [
        Pattern(
            "South African Passport",
            r"\b[ADMT]\d{8}\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "passport",
        "passport number",
        "travel document",
        "dha",
        "south african passport",
        "rsa passport",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_PASSPORT",
        name: Optional[str] = None,
    ):
        patterns = self.PATTERNS if patterns is None else patterns
        context = self.CONTEXT if context is None else context
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        text = pattern_text.upper()
        if len(text) != self.PASSPORT_LENGTH:
            return False
        if text[0] not in self.ALLOWED_PREFIXES:
            return False
        return text[1:].isdigit()
