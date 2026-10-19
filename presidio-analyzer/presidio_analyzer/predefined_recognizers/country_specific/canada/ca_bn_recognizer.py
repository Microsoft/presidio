"""Recognizer for Canadian Business Number (BN)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CaBnRecognizer(PatternRecognizer):
    """Recognize Canadian Business Number (BN) using regex + Luhn checksum.

    A BN is a 9-digit business identifier issued by the Canada Revenue Agency
    (CRA). The last digit is a Luhn check digit computed over the first 8
    digits (same scheme as the Canadian SIN). A BN is often written as a
    15-character program account number: the 9-digit BN followed by a 2-letter
    CRA program identifier (RT: GST/HST, RP: payroll, RC: corporate income
    tax, RM: import/export, RR: registered charity, RZ: information returns)
    and a 4-digit reference number, e.g. 123456782 RT 0001.

    Format: DDDDDDDDD or DDDDDDDDD PP RRRR (spaces optional)

    A bare 9-digit BN is indistinguishable from other Luhn-checked 9-digit
    identifiers (e.g. SIN) without context, so the bare form scores low and
    relies on context words.

    Reference: https://www.canada.ca/en/revenue-agency/services/tax/businesses/topics/business-registration/business-number-program-account/need-program-accounts.html

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ca"

    PATTERNS = [
        # Lookaround anchors instead of \b: \b would still match a 9-digit
        # run joined to a larger token by "/", "-" or "." (e.g. serial
        # numbers like PO-123456782 or decimals like 0.123456782). The
        # trailing (?!\.\d) blocks decimal continuations while still
        # allowing a sentence-ending period. The first negative lookahead
        # in the weak pattern suppresses it when the program-account
        # pattern below matches the same span, so overlapping results are
        # not returned twice.
        Pattern(
            "BN (weak)",
            r"(?<![\w./-])\d{9}"
            r"(?!\s?(?:RT|RP|RC|RM|RR|RZ)\s?\d{4})(?![\w/-]|\.\d)",
            0.05,
        ),
        Pattern(
            "BN program account (medium)",
            r"(?<![\w./-])\d{9}\s?(RT|RP|RC|RM|RR|RZ)\s?\d{4}(?![\w/-]|\.\d)",
            0.5,
        ),
    ]

    CONTEXT = [
        "business number",
        "bn",
        "cra",
        "canada revenue agency",
        "gst",
        "hst",
        "payroll",
        "program account",
        # French equivalents
        "ne",
        "numéro d'entreprise",
        "arc",
        "agence du revenu du canada",
        "tps",
        "tvh",
        "compte de programme",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CA_BN",
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
        Check if the pattern text cannot be validated as a CA_BN entity.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        digits = "".join(c for c in pattern_text if c.isdigit())[:9]
        if len(set(digits)) == 1:
            return True
        return not self._luhn_valid(digits)

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
