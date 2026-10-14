from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class PhPassportRecognizer(PatternRecognizer):
    """
    Recognizes Philippine Passport Number.

    Common formats:
    - 1 letter + 7 digits + 1 letter (e.g., P1234567A)
    - 2 letters + 7 digits (e.g., EB1234567)

    Reference:
    - ICAO Doc 9303, Machine Readable Travel Documents (passport document
      numbers are machine-readable passport identifiers; used here as a
      reliable reference for passport-number handling):
      https://www.icao.int/publications/doc-series/doc-9303

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ph"

    # Weak pattern: Philippine passport numbers do not include a universally
    # reliable checksum / strict character set constraints (unlike MRZ check
    # digits) and may therefore produce false positives without nearby context.
    PATTERNS = [
        Pattern(
            "PH Passport (weak: 1L7D1L or 2L7D)",
            r"\b(?:[A-Z]\d{7}[A-Z]|[A-Z]{2}\d{7})\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "passport",
        "passport number",
        "passport no",
        "passport no.",
        "passport#",
        "passport id",
        "travel document",
        "philippine passport",
        "philippines passport",
        "pasaporte",
        "pasaporte number",
        "dfa",  # Department of Foreign Affairs
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PH_PASSPORT",
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
