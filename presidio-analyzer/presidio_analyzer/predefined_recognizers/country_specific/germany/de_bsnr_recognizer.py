from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class DeBsnrRecognizer(PatternRecognizer):
    r"""
    Recognizes German Betriebsstättennummer (BSNR).

    The BSNR is a 9-digit practice / site-of-care number assigned by the
    regional Kassenärztliche Vereinigung (KV) to each approved practice
    location (Betriebsstätte) participating in the German statutory health
    insurance system.  It appears in billing records, treatment documents, and
    statutory healthcare communications and reveals the treating facility,
    making it sensitive under DSGVO.

    Legal basis: § 75 Abs. 7 SGB V (Sozialgesetzbuch Fünftes Buch).
    Standard: KBV-Richtlinie nach § 75 Abs. 7 SGB V zur Vergabe der Arzt-,
    Betriebsstätten-, Praxisnetz- sowie der Netzverbundnummern.
    Data protection: DSGVO Art. 9 (Gesundheitsdaten), BDSG § 22.

    Format (9 digits):
        Pos 1–2:  KV-Bereichskennzeichen (regional KV code, e.g. 02 Hamburg,
                  38 Nordrhein, 72 Berlin; see VALID_KV_CODES below for the
                  full whitelist per KBV Arztnummern-Richtlinie Anlage 1)
        Pos 3–9:  Laufende Nummer (sequential number assigned by KV)

    Examples (fictitious): 021234568, 381789045, 721234567

    Accuracy note: The BSNR has no public Prüfziffer algorithm, so
    validate_result cannot give positive evidence of a real BSNR; it can
    only drop clearly invalid inputs (wrong length, non-digit, all-zero).
    All structurally-plausible 9-digit inputs therefore return ``None``
    from validate_result: the match keeps its base pattern score (0.2)
    and the ContextAwareEnhancer drives final confidence via context
    words ("Betriebsstättennummer", "BSNR", "Praxis", …).

    VALID_KV_CODES below lists the 2-digit regional codes documented in
    KBV Arztnummern-Richtlinie Anlage 1. It is retained for reference
    and future opt-in strict validation but is intentionally NOT used
    to upgrade whitelisted-prefix matches to MAX_SCORE — the `\b\d{9}\b`
    pattern is too broad to justify that upgrade on a 2-digit-prefix
    check alone.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "de"

    # Valid KV regional codes per KBV Arztnummern-Richtlinie Anlage 1.
    # Includes the standard 17 KV regions, the KBV itself, and Anlage-8 BMV-Ä
    # special codes for Krankenhäuser.
    VALID_KV_CODES = frozenset(
        {
            "01",  # Schleswig-Holstein
            "02",  # Hamburg
            "03",  # Bremen
            "17",  # Niedersachsen
            "20",  # Westfalen-Lippe
            "35",  # Krankenhäuser (Anlage 8 BMV-Ä)
            "38",  # Nordrhein
            "46",  # Hessen
            "51",  # Rheinland-Pfalz
            "52",  # Baden-Württemberg
            "71",  # Bayern
            "72",  # Berlin
            "73",  # Saarland
            "74",  # KBV (Kassenärztliche Bundesvereinigung)
            "78",  # Mecklenburg-Vorpommern
            "83",  # Brandenburg
            "88",  # Sachsen-Anhalt
            "93",  # Thüringen
            "98",  # Sachsen
        }
    )

    PATTERNS = [
        Pattern(
            "Betriebsstättennummer BSNR (9 digits)",
            r"\b\d{9}\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "betriebsstättennummer",
        "betriebsstätten-nummer",
        "bsnr",
        "betriebsstätte",
        "praxisnummer",
        "arztpraxis",
        "praxis",
        "kassenärztliche vereinigung",
        "kv-nummer",
        "kv nummer",
        "praxisadresse",
        "praxisstandort",
        "nebenbetriebsstätte",
        "hauptbetriebsstätte",
        "behandlungsort",
        "vertragsarztpraxis",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "de",
        supported_entity: str = "DE_BSNR",
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
        r"""
        Validate the BSNR structurally.

        BSNR has no publicly documented Prüfziffer algorithm, so this
        method can only drop clearly invalid inputs. It does NOT promote
        structurally-valid matches to MAX_SCORE — the ``\b\d{9}\b``
        base pattern is too broad for that to be safe on a 2-digit
        prefix check alone. Final confidence on valid-shaped BSNRs is
        driven by context words via the ContextAwareEnhancer.

        :param pattern_text: the text to validate (9 digits)
        :return: False if the input is malformed (wrong length,
                 non-digit, or all-zero); None otherwise (keep pattern
                 score, let context drive confidence).
        """
        pattern_text = pattern_text.strip()

        if len(pattern_text) != 9 or not pattern_text.isdigit():
            return False

        if pattern_text == "000000000":
            return False

        return None
