"""Recognizer for Canadian postal codes."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CaPostalCodeRecognizer(PatternRecognizer):
    """Recognize Canadian postal codes using regex.

    Format: A1A 1A1 (letter-digit-letter, space, digit-letter-digit). A stricter
    pattern (higher score) matches the canonical spaced form; a weaker pattern
    (lower score, relies on surrounding context to clear the analyzer's score
    threshold) matches the same shape without a space, since that form is more
    prone to false positives against unrelated 6-character alphanumeric codes.
    Canada Post's official format is uppercase, but this recognizer relies on
    the base class's default case-insensitive matching since PII may appear
    in lowercase in real-world text. The letters D, F, I, O, Q, U are never
    used in any letter position. W and Z are additionally excluded from the
    first letter position (reserved for future expansion).

    Reference: https://www.canadapost-postescanada.ca/cpc/en/support/articles/addressing-guidelines/postal-codes.page

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ca"

    PATTERNS = [
        Pattern(
            "CA Postal Code (strict, with space)",
            r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z] \d[ABCEGHJ-NPRSTV-Z]\d\b",
            0.3,
        ),
        Pattern(
            "CA Postal Code (weak, no space)",
            r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\d[ABCEGHJ-NPRSTV-Z]\d\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "postal code",
        "postcode",
        "zip",
        "canada",
        "ontario",
        "quebec",
        "alberta",
        "british columbia",
        # French equivalents
        "code postal",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CA_POSTAL_CODE",
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
