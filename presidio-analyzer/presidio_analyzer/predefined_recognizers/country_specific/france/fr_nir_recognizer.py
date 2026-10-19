"""Recognizer for the French NIR (Numéro d'Inscription au Répertoire)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FrNirRecognizer(PatternRecognizer):
    """Recognize the French NIR / social security number using regex + checksum.

    The NIR is a 15-digit identifier: 13 significant digits (sex, year and month
    of birth, department/country of birth, commune/country code, order number)
    followed by a 2-digit checksum computed as ``97 - (first_13_digits % 97)``.
    Corsican department codes (2A/2B) are substituted with 19/18 for the checksum,
    per INSEE's published algorithm.

    Format: S YY MM DD CCC OOO KK, written with or without spaces/dots
    (e.g. "2 91 05 99 338 076 92" or "291059933807692").

    Reference: https://www.insee.fr/fr/metadonnees/definition/c1409

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "fr"

    PATTERNS = [
        Pattern(
            "NIR (France)",
            r"\b[12][ .]?\d{2}[ .]?(?:0[1-9]|1[0-2]|[2-9]\d)[ .]?"
            r"(?:\d{2}|2[AB])[ .]?\d{3}[ .]?\d{3}[ .]?\d{2}\b",
            0.4,
        ),
    ]

    CONTEXT = [
        "sécurité sociale",
        "numéro de sécurité sociale",
        "n° de sécurité sociale",
        "nir",
        "carte vitale",
        "assurance maladie",
        "sécu",
        "ameli",
        # English equivalents, for bilingual documents/context
        "social security",
        "social security number",
        "france",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "FR_NIR",
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

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        cleaned = (
            pattern_text.replace(" ", "").replace(".", "").replace("-", "").upper()
        )
        if len(cleaned) != 15:
            return False

        digits_part = cleaned[:13]
        key_part = cleaned[13:15]

        # Corsican department substitution for checksum purposes: 2A -> 19, 2B -> 18
        checksum_input = digits_part.replace("2A", "19").replace("2B", "18")
        if not checksum_input.isdigit() or not key_part.isdigit():
            return False

        computed_key = 97 - (int(checksum_input) % 97)
        return computed_key == int(key_part)
