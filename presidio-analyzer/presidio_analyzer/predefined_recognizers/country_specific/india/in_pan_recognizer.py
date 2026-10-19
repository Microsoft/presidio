from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class InPanRecognizer(PatternRecognizer):
    """
    Recognizes Indian Permanent Account Number ("PAN").

    The Permanent Account Number (PAN) is a ten digit alpha-numeric code
    with the last digit being a check digit calculated using a
    modified modulus 10 calculation.
    This recognizer identifies PAN using regex and context words.
    Reference: https://en.wikipedia.org/wiki/Permanent_account_number,
               https://incometaxindia.gov.in/Forms/tps/1.Permanent%20Account%20Number%20(PAN).pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "PAN (High)",
            r"\b([A-Za-z]{3}[AaBbCcFfGgHhJjLlPpTt]{1}[A-Za-z]{1}[0-9]{4}[A-Za-z]{1})\b",
            0.5,
        ),
        Pattern(
            "PAN (Medium)",
            r"\b([A-Za-z]{5}[0-9]{4}[A-Za-z]{1})\b",
            0.1,
        ),
        Pattern(
            "PAN (Low)",
            r"\b((?=[\w@#$%^?~-]*?[a-zA-Z])(?=[\w@#$%^?~-]*?[0-9]{4})[\w@#$%^?~-]{10})\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "permanent account number",
        "pan",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_PAN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs if replacement_pairs else [("-", ""), (" ", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )
