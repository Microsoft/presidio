"""Recognizer for the Polish tax identification number (NIP)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class PlNipRecognizer(PatternRecognizer):
    """
    Recognize Polish NIP (Numer Identyfikacji Podatkowej) using regex and checksum.

    NIP is the 10-digit tax identification number Poland assigns to legal
    persons, other entities and individuals who run a business or are
    registered for VAT; other individuals use their PESEL as their tax
    identification number. The NIP of a sole trader identifies a natural
    person.

    Format: 10 ASCII digits, written as ``1234563218`` or grouped with hyphens
    as ``123-456-32-18`` or ``123-45-63-218``. The VAT-EU form is the NIP
    preceded by ``PL`` (art. 97 ust. 10 of the Polish VAT Act); the result
    covers the 10 digits without the prefix.

    Checksum: multiply the first 9 digits by the weights 6, 5, 7, 2, 3, 4, 5,
    6, 7 and add the products. The sum modulo 11 is the check digit; a
    remainder of 10 means no valid NIP has those 9 digits. One arbitrary
    10-digit number in 11 passes, so the checksum only discards candidates
    and a pass leaves the pattern score unchanged.

    Source: European TIN Portal, "POLAND - Information on Tax Identification
    Numbers", sections 1.2 (who gets a NIP) and 2.2 (structure and checksum):
    https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/Poland-TIN.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of this recognizer
    """

    COUNTRY_CODE = "pl"

    WEIGHTS = (6, 5, 7, 2, 3, 4, 5, 6, 7)

    PATTERNS = [
        # The lookarounds reject 10 digits that are part of a longer number; \b
        # would also reject the NIP in the VAT-EU form "PL1234563218".
        Pattern(
            "NIP with hyphens (medium)",
            r"(?<!\d)[0-9]{3}-"
            r"(?:[0-9]{3}-[0-9]{2}-[0-9]{2}|[0-9]{2}-[0-9]{2}-[0-9]{3})(?!\d)",
            0.3,
        ),
        Pattern("NIP (very weak)", r"(?<!\d)[0-9]{10}(?!\d)", 0.05),
    ]

    # Context is matched against single words, so a phrase such as "numer
    # identyfikacji podatkowej" never matches; its last word does. "podatkowy"
    # is that word's lemma. "vat" also occurs inside English words ("private"),
    # but hardly in Polish ones, which spell that sound with a "w".
    CONTEXT = ["nip", "podatkowej", "podatkowy", "vat"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pl",
        supported_entity: str = "PL_NIP",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be validated as a PL_NIP entity.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        digits = [int(c) for c in pattern_text if c.isdecimal()]
        if len(digits) != 10:
            return True

        weighted_sum = sum(d * w for d, w in zip(digits, self.WEIGHTS))
        # A remainder of 10 never equals a digit, so it is rejected here too.
        return weighted_sum % 11 != digits[9]
