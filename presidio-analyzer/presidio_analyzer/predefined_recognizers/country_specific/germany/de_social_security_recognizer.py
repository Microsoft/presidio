import re
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DeSocialSecurityRecognizer(PatternRecognizer):
    """
    Recognizes German Rentenversicherungsnummer (RVNR / Sozialversicherungsnummer).

    The Rentenversicherungsnummer (also called Versicherungsnummer or RVNR) is a
    unique 12-character identifier assigned to every person insured under the German
    statutory pension insurance scheme (gesetzliche Rentenversicherung). It encodes
    date of birth, gender information, and a serial number.

    Legal basis: § 147 SGB VI (Sozialgesetzbuch Sechstes Buch – Gesetzliche
    Rentenversicherung), § 33a SGB I.
    Data protection: DSGVO Art. 4 Nr. 1 (personenbezogene Daten), BDSG.

    Format (12 characters):
        Pos 1–2:   Bereichsnummer (2 digits, issuing regional office code, 01–99)
        Pos 3–4:   Geburtstag (birth day, 01–31; or 51–81 with +50
                   Ergänzungsmerkmal to disambiguate otherwise identical
                   numbers — gender-agnostic)
        Pos 5–6:   Geburtsmonat (birth month, 01–12)
        Pos 7–8:   Geburtsjahr (last 2 digits of birth year)
        Pos 9:     Buchstabenkennung (first letter of birth surname, A–Z)
        Pos 10–11: Seriennummer / Geschlechtskennung (00–49 male,
                   50–99 female)
        Pos 12:    Prüfziffer (check digit)

    Example: 15070649C103 (canonical example, DRV technical documentation)

    Check digit algorithm (VKVV § 4 / Deutsche Rentenversicherung):
        1. Replace the letter at position 9 with its 2-digit ordinal value
           (A=01, B=02, …, Z=26). This yields 12 data digits (positions
           1–8 of the original, plus 2 letter-ordinal digits, plus
           positions 10–11) followed by the check digit at position 12.
        2. Apply weights [2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1] to the 12
           data digits (the check digit itself is not part of the
           weighted sum).
        3. For each product, take the cross-sum (Quersumme) of its digits
           (products < 10 remain unchanged; e.g. 35 → 3+5 = 8).
        4. Sum all 12 cross-sums, compute sum mod 10.
        5. The result must equal the check digit at position 12.

    Worked example for 15070649C103:
        effective = '15070649' + '03' (C=03) + '10' = '150706490310'
        × weights = 2,5,0,35,0,6,8,9,0,3,2,0
        cross-sums = 2,5,0, 8,0,6,8,9,0,3,2,0 = 43
        43 mod 10 = 3 → matches check digit '3'

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    PATTERNS = [
        Pattern(
            "Rentenversicherungsnummer (Strict, with birth date structure)",
            r"\b\d{2}"
            r"(0[1-9]|[12]\d|3[01]|5[1-9]|[67]\d|8[01])"  # day: 01-31 or 51-81
            r"(0[1-9]|1[0-2])"  # month 01-12
            r"\d{2}"  # year
            r"[A-Z]"  # surname initial
            r"\d{2}"  # serial
            r"[0-9]\b",  # check digit
            0.5,
        ),
        Pattern(
            "Rentenversicherungsnummer (Relaxed)",
            r"\b\d{8}[A-Z]\d{3}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "rentenversicherungsnummer",
        "sozialversicherungsnummer",
        "versicherungsnummer",
        "rvnr",
        "svnr",
        "sv-nummer",
        "rente",
        "rentenversicherung",
        "deutsche rentenversicherung",
        "drv",
        "sozialversicherung",
        "sozialversicherungsausweis",
        "rentenausweis",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_SOCIAL_SECURITY",
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
        Validate the Rentenversicherungsnummer using the VKVV § 4 checksum.

        Algorithm source: Verordnung über die Vergabe der Versicherungsnummer
        (VKVV) § 4, Deutsche Rentenversicherung technical specification.

        Additionally enforces the birth-day (01–31 or 51–81 with +50
        Ergänzungsmerkmal) and birth-month (01–12) ranges from the spec
        so that a relaxed-pattern match with an impossible date cannot
        be promoted to MAX_SCORE by a lucky checksum collision.

        :param pattern_text: the text to validate (12 characters)
        :return: True if valid, False if invalid
        """
        pattern_text = pattern_text.upper().strip()

        if len(pattern_text) != 12:
            return False

        if not re.match(r"^\d{8}[A-Z]\d{3}$", pattern_text):
            return False

        # VKVV § 4: Pos 3–4 encodes the birth day (01–31, or 51–81 with
        # +50 Ergänzungsmerkmal); Pos 5–6 the birth month (01–12). These
        # are structural invariants of a real RVNR — enforce them here so
        # that a relaxed-pattern match with an impossible date cannot be
        # promoted to MAX_SCORE by a lucky checksum.
        day = int(pattern_text[2:4])
        month = int(pattern_text[4:6])
        if not (1 <= day <= 31 or 51 <= day <= 81):
            return False
        if not 1 <= month <= 12:
            return False

        letter = pattern_text[8]
        letter_val = str(ord(letter) - ord("A") + 1).zfill(2)

        effective = pattern_text[:8] + letter_val + pattern_text[9:11]

        check_digit = int(pattern_text[11])
        weights = [2, 1, 2, 5, 7, 1, 2, 1, 2, 1, 2, 1]

        total = 0
        for digit_char, weight in zip(effective, weights):
            product = int(digit_char) * weight
            total += (product // 10) + (product % 10)

        return (total % 10) == check_digit
