from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UkPassportRecognizer(PatternRecognizer):
    """
    Recognizes UK passport numbers using regex.

    UK passport numbers are 9 digits (all numeric) for every series currently
    in circulation, per HM Passport Office "Basic passport checks" (GOV.UK).

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "uk"

    PATTERNS = [
        Pattern(
            "UK Passport (very weak)",
            r"\b\d{9}\b",
            0.05,
        ),
    ]

    CONTEXT = [
        "passport",
        "passport number",
        "travel document",
        "uk passport",
        "british passport",
        "her majesty",
        "his majesty",
        "hm passport",
        "hmpo",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "UK_PASSPORT",
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
