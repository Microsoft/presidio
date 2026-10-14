from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class KrPassportRecognizer(PatternRecognizer):
    """
    Recognize Korean Passport Number.

    https://learn.microsoft.com/en-us/purview/sit-defn-south-korea-passport-number

    the current passport number format:
        - one letter 'M' or 'm' or 'S' or 's' or 'R' or 'r' or 'O' or 'o' or 'D' or 'd'
        - three digits
        - one letter (A-Z, a-z)
        - four digits

    the previous passport number format:
        - one letter 'M' or 'm' or 'S' or 's' or 'R' or 'r' or 'O' or 'o' or 'D' or 'd'
        - eight digits

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "kr"

    PATTERNS = [
        Pattern(
            "Passport Number (Current)",
            r"(?<![A-Z0-9a-z])[MmSsRrOoDd]\d{3}[A-Za-z]\d{4}(?![0-9])",
            0.1,
        ),
        Pattern(
            "Passport Number (Previous)",
            r"(?<![A-Z0-9a-z])[MmSsRrOoDd]\d{8}(?![0-9])",
            0.05,
        ),
    ]

    CONTEXT = [
        "Korean passport",
        "Korean passport number",
        "대한민국 여권",
        "여권",
        "passport",
        "passport number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ko",
        supported_entity: str = "KR_PASSPORT",
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
