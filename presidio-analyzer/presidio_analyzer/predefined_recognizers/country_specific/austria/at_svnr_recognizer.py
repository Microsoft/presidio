"""Recognizer for the Austrian social insurance number (Versicherungsnummer)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class AtSvnrRecognizer(PatternRecognizer):
    """
    Recognize the Austrian social insurance number (SVNR / VSNR).

    The Versicherungsnummer, commonly called Sozialversicherungsnummer (SVNR),
    is the 10-digit personal identifier of the Austrian social insurance
    system. It is printed on the e-card and appears on payslips, employer
    registrations and medical documents.

    Format: ``LLLPTTMMJJ``, usually written ``LLLP TTMMJJ`` or ``LLLP TT MM JJ``
        Pos 1–3:  Laufnummer (serial number), counted upwards from 100, so
                  the first digit is never 0
        Pos 4:    Prüfziffer (check digit)
        Pos 5–10: usually the date of birth as ``DDMMYY``, but not always.
                  Persons whose birth date is unknown, or whose birth date
                  has no serial numbers left, get a fictitious date with a
                  month of 13, 14 or 15. A later correction of the birth
                  date does not change the number. The date part is
                  therefore not validated as a calendar date.

    Check digit algorithm:
        1. Multiply the three serial digits by 3, 7, 9 and the six date
           digits by 5, 8, 4, 2, 1, 6.
        2. The check digit is the sum of the products modulo 11.
        3. A remainder of 10 is never issued (the next serial number is
           used instead), so such numbers are rejected.

    Worked example for the synthetic number 4131 300271:
        serial 413    × 3, 7, 9          = 12 + 7 + 27              = 46
        date   300271 × 5, 8, 4, 2, 1, 6 = 15 + 0 + 0 + 4 + 7 + 6  = 32
        (46 + 32) mod 11 = 78 mod 11 = 1 → matches check digit '1'

    A random 10-digit run with a non-zero first digit passes the check digit
    about once in 11 tries, so a passing number is not promoted to the
    maximum score. Numbers that fail it are dropped (``invalidate_result``);
    the others keep their pattern score, and context words raise it.

    Sources:
    - Dachverband der österreichischen Sozialversicherungsträger,
      "Was ist die Versicherungsnummer?" (layout, weights, modulo 11, serial
      never starting with 0, remainder 10 never issued, fictitious birth
      dates):
      https://www.sozialversicherung.at/cdscontent/?contentid=10007.820902
    - Austrian Federal Ministry of Health, Family and Youth, parliamentary
      answer 4690/AB XXIII. GP of 2008-09-01 (remainder-10 rule, months
      13 to 15):
      https://www.parlament.gv.at/dokument/XXIII/AB/4690/fnameorig_136871.html

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param name: Name of the recognizer
    """

    COUNTRY_CODE = "at"

    SVNR_LENGTH = 10
    CHECK_DIGIT_INDEX = 3
    # Weights for the serial digits (pos 1–3) followed by the date digits
    # (pos 5–10); the check digit itself is not weighted.
    WEIGHTS = (3, 7, 9, 5, 8, 4, 2, 1, 6)

    PATTERNS = [
        Pattern(
            "SVNR (very weak)",
            r"\b[1-9]\d{9}\b",
            0.05,
        ),
        Pattern(
            "SVNR (weak)",
            # Groups separated by a space or a no-break space (U+00A0)
            r"\b[1-9]\d{3}[ \u00a0](?:\d{6}|\d{2}[ \u00a0]\d{2}[ \u00a0]\d{2})\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "sozialversicherungsnummer",
        "versicherungsnummer",
        "svnr",
        "vsnr",
        "vnr",
        "sv-nummer",
        "sv-nr",
        "e-card",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "AT_SVNR",
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
        Drop a match that cannot be an issued Versicherungsnummer.

        :param pattern_text: the matched text, with or without spaces
        :return: True if the length, serial or check digit rule fails
        """
        return not self._is_valid_svnr("".join(pattern_text.split()))

    @classmethod
    def _is_valid_svnr(cls, digits: str) -> bool:
        if len(digits) != cls.SVNR_LENGTH or not digits.isdecimal():
            return False
        if digits[0] == "0":
            return False
        check_digit = cls._compute_check_digit(digits)
        if check_digit is None:
            return False
        return check_digit == int(digits[cls.CHECK_DIGIT_INDEX])

    @classmethod
    def _compute_check_digit(cls, digits: str) -> Optional[int]:
        """
        Return the check digit of a 10-digit SVNR, or None if never issued.

        :param digits: the 10 digits; the digit at the check position is ignored
        """
        index = cls.CHECK_DIGIT_INDEX
        weighted = digits[:index] + digits[index + 1 :]
        remainder = sum(w * int(d) for w, d in zip(cls.WEIGHTS, weighted)) % 11
        return None if remainder == 10 else remainder
