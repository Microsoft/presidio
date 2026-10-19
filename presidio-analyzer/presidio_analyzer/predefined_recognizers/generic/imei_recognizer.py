from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class ImeiRecognizer(PatternRecognizer):
    """
    Recognize International Mobile Equipment Identity (IMEI) numbers using regex.

    IMEI is a 15-digit identifier for mobile devices. The last digit is a Luhn
    check digit derived from the preceding 14 digits; validation is performed
    over the full 15-digit IMEI. Detection relies on a formatted
    pattern (``##-######-######-#`` or ``## ###### ###### #``) to avoid
    collisions with other 15-digit Luhn identifiers such as AMEX credit
    card numbers.

    ref:
    - https://en.wikipedia.org/wiki/International_Mobile_Equipment_Identity
    """

    PATTERNS = [
        Pattern("IMEI (medium)", r"\b\d{2}([- ])\d{6}\1\d{6}\1\d\b", 0.5),
    ]

    CONTEXT = [
        "imei",
        "mobile device",
        "handset",
        "device serial",
        "phone serial",
        "serial number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IMEI",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be validated as an IMEI.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        only_digits = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        if len(only_digits) != 15:
            return True
        return not self._luhn_valid(only_digits)

    @staticmethod
    def _luhn_valid(digits: str) -> bool:
        """Validate using the Luhn checksum."""
        total = 0
        for i, digit in enumerate(reversed(digits)):
            n = int(digit)
            if i % 2 == 1:
                n *= 2
                if n > 9:
                    n -= 9
            total += n
        return total % 10 == 0
