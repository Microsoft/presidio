from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DePassportRecognizer(PatternRecognizer):
    """
    Recognizes German passport numbers (Reisepassnummern) using regex.

    German passports are issued by the Bundesdruckerei on behalf of the
    Bundesrepublik Deutschland. The document number consists of 9 alphanumeric
    characters and appears on the data page and in the Machine Readable Zone (MRZ).

    Legal basis: Passgesetz (PassG) § 4, Passverordnung (PassV).
    Data protection: DSGVO Art. 4 Nr. 1 (personenbezogene Daten), BDSG.

    Format (9 characters total):
        - Uppercase letters from the limited set C, F, G, H, J, K, L, M, N,
          P, R, T, V, W, X, Y, Z and digits 0–9, as printed on the data page.
        - Example: C01X00T47 (specimen passport)
        - The ICAO Doc 9303 check digit is not part of the printed number:
          it follows the number in the MRZ (C01X00T478D<<...), so a
          10-character match is the number plus its check digit.

    Character set excludes visually ambiguous letters (A, B, D, E, I, O, Q,
    S, U) per ICAO Doc 9303 Machine Readable Travel Documents.

    Check digit algorithm (ICAO Doc 9303):
        - Letters A=10, B=11, …, Z=35; digits keep their face value.
        - Apply weights 7, 3, 1 repeating to the 9 characters of the number.
        - Sum the products, take sum mod 10 — that is the check digit.

    Worked example for C01X00T47:
        values = 12, 0, 1, 33, 0, 0, 29, 4, 7
        weights = 7, 3, 1, 7, 3, 1, 7, 3, 1
        products = 84, 0, 1, 231, 0, 0, 203, 12, 7 → sum = 538
        538 mod 10 = 8 → the MRZ reads C01X00T478

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    # Only the ICAO-restricted charset is used. A previous relaxed
    # pattern allowing any [A-Z] first character was removed: it would
    # accept forbidden letters (A, B, D, E, I, O, Q, S, U) and
    # validate_result would still compute a MRZ check digit for them,
    # occasionally upgrading non-German or obviously-invalid strings to
    # MAX_SCORE. The strict pattern already covers every legitimate
    # German passport number.
    PATTERNS = [
        Pattern(
            "Reisepassnummer (Strict ICAO charset)",
            r"\b[CFGHJKLMNPRTVWXYZ][CFGHJKLMNPRTVWXYZ0-9]{7}[0-9]\d?(?:\b|(?=D<))",
            0.4,
        ),
    ]

    CONTEXT = [
        "reisepass",
        "pass",
        "passnummer",
        "reisepassnummer",
        "passport",
        "passport number",
        "pass-nr",
        "dokumentennummer",
        "bundesrepublik deutschland",
        "ausweisdokument",
        "mrz",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_PASSPORT",
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
        Validate the ICAO Doc 9303 check digit when it is present.

        Algorithm source: ICAO Doc 9303 Part 3 — Machine Readable Travel
        Documents. The printed 9-character number carries no check digit and
        is kept at pattern confidence (return ``None``). A 10-character match
        is the number followed by its MRZ check digit: weights 7, 3, 1
        repeating over the 9 characters, letters mapped A=10 … Z=35, sum
        modulo 10.

        :param pattern_text: the text to validate (9 or 10 characters)
        :return: True if the check digit is valid; False if it is not or the
                 value is malformed; None when there is no check digit.
        """
        pattern_text = pattern_text.upper().strip()

        # ICAO Doc 9303 excludes these visually-ambiguous letters from
        # travel-document serial numbers. Reject outright so the weighted
        # checksum cannot accidentally mark a non-ICAO string as valid.
        forbidden = set("ABDEIOQSU")
        if any(c in forbidden for c in pattern_text[:9]):
            return False

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
