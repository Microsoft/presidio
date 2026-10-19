from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UkPassportRecognizer(PatternRecognizer):
    """
    Recognizes UK passport numbers using regex.

    A UK passport number is 9 digits. HM Passport Office documents the same
    9-digit number for every book design from 1988 through the 2025 Series D,
    see "Basic passport checks":
    https://www.gov.uk/government/publications/basic-passport-checks/basic-passport-checks-accessible

    The one letters-and-digits identifier on a UK passport is the serial on the
    thin film patch over the photo, which is 3 letters and 4 digits followed by
    a check symbol. The same guidance warns not to confuse it with the passport
    number, and it is not matched here.

    Nine bare digits carry no structure, so the score follows
    UsPassportRecognizer, which scores the same shape at 0.05.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "uk"

    PATTERNS = [
        Pattern(
            "UK Passport (very weak)",
            r"\b[0-9]{9}\b",
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
