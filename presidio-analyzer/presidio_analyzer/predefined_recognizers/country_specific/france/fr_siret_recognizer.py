"""Recognizer for French SIRET establishment identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FrSiretRecognizer(PatternRecognizer):
    """Recognize French SIRET numbers using regex + Luhn checksum.

    A SIRET is the 14-digit identifier INSEE assigns to every establishment:
    the 9-digit SIREN of the legal unit, then a 5-digit NIC whose last digit
    is a Luhn check digit over the 14 digits. The SIREN part carries its own
    Luhn check digit.

    Format: DDDDDDDDDDDDDD, DDDDDDDDD DDDDD or DDD DDD DDD DDDDD, in ASCII
    digits. The separator may be a space, a no-break space (U+00A0) or a
    narrow no-break space (U+202F), as produced by French typography.

    Establishments of La Poste (SIREN 356000000) other than its head office
    follow a specific rule: the sum of the 14 digits is a multiple of 5.
    Either check is accepted for that SIREN. This tolerance is not in the
    INSEE documents: in the Sirene register of 1 September 2026, 41
    establishments of La Poste, head office included, satisfy Luhn and not
    the multiple-of-5 rule.

    The checksum only discards candidates; a pass leaves the pattern score
    unchanged.

    Sources:
    - INSEE, "Identifiants économiques : SIREN, NIC et SIRET", section 8:
      https://xml.insee.fr/schema/siret.html
    - INSEE, "Lettre d'information Sirene n°16", November 2013 (Luhn, La
      Poste rule):
      https://web.archive.org/web/20230128092015/http://sirene.fr/static-resources/doc/lettres/lettre-16-novembre-2013.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of this recognizer
    """

    COUNTRY_CODE = "fr"

    LA_POSTE_SIREN = "356000000"

    PATTERNS = [
        Pattern("SIRET (very weak)", r"\b[0-9]{14}\b", 0.05),
        Pattern("SIRET (weak)", r"\b[0-9]{9}[ \u00a0\u202f][0-9]{5}\b", 0.1),
        Pattern(
            "SIRET (medium)",
            r"\b[0-9]{3}[ \u00a0\u202f][0-9]{3}[ \u00a0\u202f][0-9]{3}"
            r"[ \u00a0\u202f][0-9]{5}\b",
            0.3,
        ),
    ]

    CONTEXT = ["siret"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "fr",
        supported_entity: str = "FR_SIRET",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
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
        Check if the pattern text cannot be validated as a FR_SIRET entity.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        digits = "".join(c for c in pattern_text if c.isdigit())
        siren = digits[:9]
        if siren == "000000000" or not self._luhn_valid(siren):
            return True
        if self._luhn_valid(digits):
            return False
        if siren == self.LA_POSTE_SIREN:
            return sum(int(d) for d in digits) % 5 != 0
        return True

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
