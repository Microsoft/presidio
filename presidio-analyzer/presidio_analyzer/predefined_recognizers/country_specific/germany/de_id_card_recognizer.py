from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DeIdCardRecognizer(PatternRecognizer):
    """
    Recognizes German national ID card numbers (Personalausweisnummern) using regex.

    The German Personalausweis (nPA – neuer Personalausweis) has been issued since
    November 2010. Its document number (Seriennummer/Dokumentennummer) is printed on
    the front of the card and encoded in the Machine Readable Zone (MRZ).

    Legal basis: Personalausweisgesetz (PAuswG), Personalausweisverordnung (PAuswV).
    Data protection: DSGVO Art. 4 Nr. 1 (personenbezogene Daten), BDSG.

    Format (nPA, since November 2010):
        - 9 characters from the ICAO restricted uppercase charset
          (excludes A, B, D, E, I, O, Q, S, U), as printed on the card.
        - Example: L01X00T47 (specimen card)
        - The ICAO Doc 9303 check digit is not part of the printed number:
          it follows the number in the MRZ (IDD<<L01X00T471...), so a
          10-character match is the number plus its check digit.

    Format (old Personalausweis, before November 2010):
        - Letter T followed by 8 digits (legacy 9-char format; no ICAO
          check digit — the trailing digit is part of the serial).
        - Example: T22000124

    Check digit algorithm (ICAO Doc 9303, nPA only):
        Weights 7, 3, 1 repeating on the 9 characters of the number with
        letters mapped A=10 … Z=35; the sum modulo 10 is the check digit.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    PATTERNS = [
        Pattern(
            "Personalausweisnummer nPA (ICAO charset, optional MRZ check digit)",
            r"\b[CFGHJKLMNPRTVWXYZ][CFGHJKLMNPRTVWXYZ0-9]{7}[0-9]\d?\b",
            0.4,
        ),
        Pattern(
            "Personalausweisnummer alt (T + 8 Ziffern)",
            r"\bT\d{8}\b",
            0.5,
        ),
    ]

    CONTEXT = [
        "personalausweis",
        "ausweis",
        "personalausweisnummer",
        "ausweisnummer",
        "ausweisdokument",
        "dokumentennummer",
        "seriennummer",
        "npa",
        "neuer personalausweis",
        "personalausweisgesetz",
        "pauwsg",
        "bundespersonalausweis",
        "identity card",
        "national id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_ID_CARD",
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
        Validate the nPA ICAO Doc 9303 check digit when it is present.

        The printed 9-character number carries no check digit, so it (like
        the legacy "T + 8 digits" format) is kept at pattern confidence
        (return ``None``). A 10-character match is the number followed by
        its MRZ check digit, which is verified.

        :param pattern_text: the text to validate (9 or 10 characters)
        :return: True if the ICAO check matches; False if it does not or the
                 value is malformed; None when there is no check digit.
        """
        pattern_text = pattern_text.upper().strip()

        if len(pattern_text) == 9:
            return None

        if len(pattern_text) != 10 or not pattern_text[-1].isdigit():
            return False

        weights = [7, 3, 1]
        total = 0
        for i, c in enumerate(pattern_text[:-1]):
            if c.isdigit():
                value = int(c)
            elif "A" <= c <= "Z":
                value = ord(c) - ord("A") + 10
            else:
                return False
            total += value * weights[i % 3]

        return (total % 10) == int(pattern_text[-1])
