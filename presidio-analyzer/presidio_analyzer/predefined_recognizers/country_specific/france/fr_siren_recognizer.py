"""Recognizer for French SIREN legal unit identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FrSirenRecognizer(PatternRecognizer):
    """Recognize French SIREN numbers using regex + Luhn checksum.

    A SIREN is the 9-digit identifier INSEE assigns to every natural or legal
    person entered in the Sirene register; natural persons are those working
    as self-employed. The last digit is a Luhn check digit.

    Format: DDDDDDDDD or DDD DDD DDD, in ASCII digits. The separator may be a
    space, a no-break space (U+00A0) or a narrow no-break space (U+202F), as
    produced by French typography.

    The first 9 digits of a spaced SIRET are a SIREN and are reported as such,
    next to the FR_SIRET result of FrSiretRecognizer.

    The checksum only discards candidates. A Luhn check passes one arbitrary
    number in ten, so a pass leaves the pattern score unchanged.

    Sources:
    - INSEE, "Identifiants économiques : SIREN, NIC et SIRET", sections 3
      and 8:
      https://xml.insee.fr/schema/siret.html
    - INSEE, "Lettre d'information Sirene n°16", November 2013:
      https://web.archive.org/web/20230128092015/http://sirene.fr/static-resources/doc/lettres/lettre-16-novembre-2013.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of this recognizer
    """

    COUNTRY_CODE = "fr"

    PATTERNS = [
        Pattern("SIREN (very weak)", r"\b[0-9]{9}\b", 0.05),
        Pattern(
            "SIREN (weak)",
            r"\b[0-9]{3}[ \u00a0\u202f][0-9]{3}[ \u00a0\u202f][0-9]{3}\b",
            0.1,
        ),
    ]

    CONTEXT = ["siren"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "fr",
        supported_entity: str = "FR_SIREN",
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
        Check if the pattern text cannot be validated as a FR_SIREN entity.

        The all-zero number passes Luhn but is not an assigned SIREN.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        digits = "".join(c for c in pattern_text if c.isdigit())
        return digits == "000000000" or not self._luhn_valid(digits)

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
