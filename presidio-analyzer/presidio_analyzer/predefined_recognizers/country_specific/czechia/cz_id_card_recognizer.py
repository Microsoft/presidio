from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzIdCardRecognizer(PatternRecognizer):
    r"""
    Recognizes Czech identity card numbers (číslo občanského průkazu).

    The občanský průkaz is the mandatory Czech identity card. Machine
    readable cards issued since the early 2000s (including the current
    eOP) carry a 9-digit document number printed on the front side and
    in the MRZ.

    Legal basis: zákon č. 269/2021 Sb., o občanských průkazech.
    Data protection: GDPR Art. 4 Nr. 1, zákon č. 110/2019 Sb.

    Format (9 digits): no publicly documented check digit exists, so
    ``validate_result`` cannot give positive evidence of a real document
    number; it only drops clearly invalid inputs (all-zero). All
    structurally plausible 9-digit inputs return ``None``: the match
    keeps its base pattern score (0.2) and the ContextAwareEnhancer
    drives the final confidence via context words ("občanský průkaz",
    "číslo OP", ...).

    Legacy booklet-style identity cards used letter-prefixed serial
    formats that are no longer issued; they are explicitly out of scope.

    Examples (fictitious): 123456789, 987654321

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    PATTERNS = [
        Pattern(
            "Občanský průkaz (9 digits)",
            r"(?<![\w/.-])\d{9}(?![\w/-])",
            0.2,
        ),
    ]

    CONTEXT = [
        "občanský",
        "občanského",
        "občanském",
        "občanka",
        "průkaz",
        "průkazu",
        "průkazem",
        "totožnost",
        "totožnosti",
        "obcansky prukaz",
        "doklad",
        "dokladu",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "CZ_ID_CARD",
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
        Validate the identity card number structurally.

        The občanský průkaz number has no publicly documented check digit,
        so this method only drops clearly invalid inputs. Final confidence
        on valid-shaped numbers is driven by context words via the
        ContextAwareEnhancer.

        :param pattern_text: the text to validate (9 digits)
        :return: False if malformed or all-zero, None otherwise (keep
                 pattern score, let context drive confidence)
        """
        pattern_text = pattern_text.strip()

        if len(pattern_text) != 9 or not pattern_text.isdigit():
            return False

        if pattern_text == "000000000":
            return False

        return None
