from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzPassportRecognizer(PatternRecognizer):
    """
    Recognizes Czech passport numbers (číslo cestovního pasu).

    Czech passports (cestovní pas) are issued by the Ministry of the
    Interior. Biometric passports issued since 2006 carry an 8-digit
    document number; older series used 7 digits or a 2-letter prefix
    followed by 6-7 digits.

    Legal basis: zákon č. 329/1999 Sb., o cestovních dokladech.
    Data protection: GDPR Art. 4 Nr. 1, zákon č. 110/2019 Sb.

    Format:
        - 2 uppercase letters followed by 6-7 digits (older series), or
        - 7-8 digits (current biometric series)

    No public check digit algorithm exists for the printed document
    number, so ``validate_result`` only drops clearly invalid inputs
    (lowercase letter prefix, all-zero digits). Final confidence is
    driven by context words ("cestovní pas", "pas č.", ...) via the
    ContextAwareEnhancer.

    Examples (fictitious): AB123456, 39182634

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    PATTERNS = [
        Pattern(
            "Cestovní pas (letter prefix)",
            r"(?<![\w/-])[A-Z]{2}\s?\d{6,7}(?![\w/-])",
            0.3,
        ),
        Pattern(
            "Cestovní pas (digits only)",
            r"(?<![\w/.-])\d{7,8}(?![\w/-])",
            0.1,
        ),
    ]

    CONTEXT = [
        "cestovní",
        "cestovního",
        "pas",
        "pasu",
        "pasem",
        "passport",
        "cestovni pas",
        "doklad",
        "dokladu",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "CZ_PASSPORT",
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

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate the passport number structurally.

        Patterns are matched case-insensitively (global regex flags), but
        real document numbers are printed in uppercase, so a lowercase
        letter prefix (e.g. the words "je 123456" would otherwise match)
        is rejected here. All-zero digit blocks are rejected as well.

        :param pattern_text: the text to validate
        :return: False if malformed, None otherwise (keep pattern score,
                 let context drive confidence)
        """
        pattern_text = pattern_text.strip()

        letters = "".join(c for c in pattern_text if c.isalpha())
        digits = "".join(c for c in pattern_text if c.isdigit())

        if letters and not letters.isupper():
            return False

        if not digits or digits.lstrip("0") == "":
            return False

        return None
