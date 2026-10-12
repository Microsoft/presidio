from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FrNirRecognizer(PatternRecognizer):
    """
    Recognizes the French NIR (numéro de sécurité sociale) using regex and key.

    The NIR (numéro d'inscription au répertoire national d'identification des
    personnes physiques) is the French social security number assigned by INSEE
    to every person born in France or registered with the French social security
    system. It is printed on the carte Vitale and used across health insurance,
    pension and payroll systems.

    Format (13 digits followed by a 2-digit key, 15 characters in total,
    commonly written with spaces between groups):
        - Pos 1:     sex — 1 (male) or 2 (female); 3, 4, 7 and 8 are used for
                     persons whose registration is in progress (temporary NIR)
        - Pos 2–3:   last two digits of the year of birth
        - Pos 4–5:   month of birth — 01–12; 13, 20–42 and 50–99 encode an
                     unknown or incomplete month
        - Pos 6–7:   département of birth — 01–95, 2A/2B (Corsica), 96, 99
                     (born abroad); overseas départements use three digits
                     (970–989) followed by a two-digit commune code
        - Pos 8–10:  INSEE commune code (or country code when born abroad)
        - Pos 11–13: order number within the month and commune (001–999)
        - Pos 14–15: key (clé de contrôle), 01–97

    Key algorithm: key = 97 - (N mod 97), where N is the 13-digit number.
    For Corsican départements the letters are replaced before the computation:
    2A -> 19 and 2B -> 18.

    Only the 15-character form (with key) is detected: the key is the sole
    checksum of the NIR, so a 13-digit number without it cannot be validated.

    Sources: INSEE, "Numéro d'inscription au répertoire",
    https://www.insee.fr/fr/metadonnees/definition/c1409 and
    https://fr.wikipedia.org/wiki/Numéro_de_sécurité_sociale_en_France

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "fr"

    PATTERNS = [
        Pattern(
            "NIR (medium)",
            r"\b[123478] ?\d{2} ?(?:0[1-9]|1[0-3]|[23]\d|4[0-2]|[5-9]\d)"
            r" ?(?:0[1-9]|[1-9]\d|2[AB]) ?\d{3} ?\d{3} ?\d{2}\b",
            0.4,
        ),
    ]

    CONTEXT = [
        "numéro de sécurité sociale",
        "sécurité sociale",
        "insee",
        "carte vitale",
        "sécu",
        "immatriculation",
        "assuré social",
        "social security number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "fr",
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

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate the NIR key (clé de contrôle).

        :param pattern_text: the text detected by the regex, 15 characters
            once spaces are removed
        :return: True if the key matches the 13-digit number, False otherwise
        """
        nir = pattern_text.replace(" ", "").upper()
        if len(nir) != 15 or not nir[13:].isdigit():
            return False

        key = self._compute_key(nir[:13])
        if key is None:
            return False

        return key == int(nir[13:])

    @staticmethod
    def _compute_key(number: str) -> Optional[int]:
        """
        Compute the key of a 13-character NIR body.

        Corsican département codes are substituted before the modulo:
        2A -> 19 and 2B -> 18.

        :param number: the 13 characters preceding the key, upper-cased
        :return: the expected 2-digit key, or None if the body is not numeric
            after the Corsica substitution
        """
        if len(number) != 13:
            return None

        department = number[5:7]
        if department == "2A":
            number = number[:5] + "19" + number[7:]
        elif department == "2B":
            number = number[:5] + "18" + number[7:]

        if not number.isdigit():
            return None

        return 97 - int(number) % 97
