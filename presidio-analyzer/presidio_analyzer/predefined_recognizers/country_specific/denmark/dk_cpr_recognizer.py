# -*- coding: utf-8 -*-
"""Danish CPR number (personnummer) recognizer.

The CPR number is a 10-digit personal identifier assigned to every Danish
resident. Its structure is ``DDMMYY-SSSS``:

* ``DDMMYY`` is the date of birth.
* ``SSSS`` is a sequence number whose first digit, combined with the two-digit
  year, encodes the birth century (see the official century table published by
  CPR-kontoret in "Personnummeret i CPR-systemet").
* The final digit was historically a modulus-11 control digit computed over all
  ten digits with weights ``4 3 2 7 6 5 4 3 2 1``.

CPR-kontoret abolished the mandatory modulus-11 check in 2007 because several
birth dates had exhausted their supply of control-digit-valid sequence numbers.
Numbers issued since then are not guaranteed to satisfy modulus-11. The
recognizer therefore treats a passing checksum as confirmation but never rejects
a candidate solely because the checksum fails, so that valid post-2007 numbers
are still detected.

References
* CPR-kontoret, "Opbygning af CPR-nummeret" - structure and century table:
  https://www.cpr.dk/cpr-systemet/opbygning-af-cpr-nummeret
* CPR-kontoret, "Personnummeret i CPR" (PDF) - structure and modulus-11 weights:
  https://www.cpr.dk/media/17534/personnummeret-i-cpr.pdf
* CPR-kontoret, "Personnumre uden kontrolciffer (modulus 11 kontrol)" - CPR
  numbers issued since 2007 are not guaranteed to satisfy modulus-11 and are
  fully valid:
  https://www.cpr.dk/cpr-systemet/personnumre-uden-kontrolciffer-modulus-11-kontrol
"""

from __future__ import annotations

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DkCprRecognizer(PatternRecognizer):
    """Recognizes and validates Danish CPR numbers (personnummer).

    Validation pipeline:
    * Normalise to ten digits.
    * Validate the date component, deriving the full four-digit year from the
      century table so leap days are handled correctly.
    * Apply the modulus-11 checksum as confirmation only: a pass promotes the
      match, a failure leaves the pattern score untouched (never invalidates).
    """

    COUNTRY_CODE = "dk"

    # Modulus-11 weights applied to the ten digits, most significant first.
    _MOD11_WEIGHTS = (4, 3, 2, 7, 6, 5, 4, 3, 2, 1)

    PATTERNS = [
        Pattern(
            "Danish CPR (Medium)",
            r"\b\d{6}-\d{4}\b",
            0.5,
        ),
        Pattern(
            "Danish CPR (Weak)",
            r"\b\d{10}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "cpr",
        "cpr-nummer",
        "cpr nr",
        "cpr-nr",
        "personnummer",
        "personnr",
        "central person register",
        "civil registration",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "da",
        supported_entity: str = "DK_CPR_NUMBER",
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

    @staticmethod
    def _numeric_part(cpr: str) -> str:
        """Return only the digit characters of a CPR string."""
        return "".join(filter(str.isdigit, cpr))

    @staticmethod
    def _full_year(year_two: int, seventh_digit: int) -> int:
        """Derive the four-digit birth year from the century table.

        ``year_two`` is the two-digit year (``YY``); ``seventh_digit`` is the
        first digit of the sequence number.
        """
        if seventh_digit <= 3:
            return 1900 + year_two
        if seventh_digit == 4 or seventh_digit == 9:
            return 2000 + year_two if year_two <= 36 else 1900 + year_two
        # seventh_digit in 5..8
        return 2000 + year_two if year_two <= 57 else 1800 + year_two

    @classmethod
    def _has_valid_date(cls, cpr: str) -> bool:
        """Validate the date component, resolving the century for leap days."""
        try:
            day = int(cpr[0:2])
            month = int(cpr[2:4])
            year_two = int(cpr[4:6])
            seventh_digit = int(cpr[6])
        except (ValueError, IndexError):
            return False

        if not 1 <= month <= 12:
            return False

        year = cls._full_year(year_two, seventh_digit)
        days_in_month = [
            31,
            29 if (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ]
        return 1 <= day <= days_in_month[month - 1]

    @classmethod
    def _is_mod11_valid(cls, cpr: str) -> bool:
        """Modulus-11 checksum over the ten digits with the CPR weights."""
        total = sum(int(d) * w for d, w in zip(cpr, cls._MOD11_WEIGHTS))
        return total % 11 == 0

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """Validate a candidate CPR number.

        Returns ``True`` when the checksum confirms the number, ``False`` when
        the structure or date is invalid, and ``None`` when the number is
        structurally valid but fails the (post-2007 optional) checksum.
        """
        num = self._numeric_part(pattern_text)
        if len(num) != 10:
            return False

        if not self._has_valid_date(num):
            return False

        if self._is_mod11_valid(num):
            return True

        return None
