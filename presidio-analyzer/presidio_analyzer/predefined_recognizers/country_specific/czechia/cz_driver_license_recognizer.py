from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzDriverLicenseRecognizer(PatternRecognizer):
    """
    Recognizes Czech driving licence numbers (číslo řidičského průkazu).

    The řidičský průkaz is the Czech driving licence, issued in the
    EU-harmonised card format. The document number consists of 2
    uppercase letters followed by 6-9 digits (e.g. ED 994127 on cards,
    CZ-prefixed variants appear in registers and exports).

    Legal basis: § 103 zákona č. 361/2000 Sb., o provozu na pozemních
    komunikacích; vyhláška č. 31/2001 Sb. EU Directive 2006/126/EC.
    Data protection: GDPR Art. 4 Nr. 1, zákon č. 110/2019 Sb.

    Format: 2 uppercase letters + 6-9 digits, optionally separated by a
    space. No public check digit algorithm exists, so ``validate_result``
    only drops clearly invalid inputs (lowercase prefix such as ordinary
    words before a number, all-zero digits). Final confidence is driven
    by context words ("řidičský průkaz", "ŘP", ...) via the
    ContextAwareEnhancer.

    Examples (fictitious): ED994127, CZ123456789

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    PATTERNS = [
        Pattern(
            "Řidičský průkaz (2 letters + digits)",
            r"(?<![\w/-])[A-Z]{2}\s?\d{6,9}(?![\w/-])",
            0.3,
        ),
    ]

    CONTEXT = [
        "řidičský",
        "řidičského",
        "řidičském",
        "řidičák",
        "průkaz",
        "průkazu",
        "průkazem",
        "oprávnění",
        "ridicsky prukaz",
        "licence",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "CZ_DRIVER_LICENSE",
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
        Validate the driving licence number structurally.

        Patterns are matched case-insensitively (global regex flags), but
        real licence numbers are printed in uppercase, so a lowercase
        prefix (e.g. the words "na 123456" would otherwise match) is
        rejected here. All-zero digit blocks are rejected as well.

        :param pattern_text: the text to validate
        :return: False if malformed, None otherwise (keep pattern score,
                 let context drive confidence)
        """
        pattern_text = pattern_text.strip()

        letters = pattern_text[:2]
        digits = pattern_text[2:].strip()

        if not letters.isalpha() or not letters.isupper():
            return False

        if not digits.isdigit() or digits.lstrip("0") == "":
            return False

        return None
