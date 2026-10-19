from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzDateRecognizer(PatternRecognizer):
    """
    Recognizes dates written in Czech notation.

    Czech dates are written day-first with an ordinal dot after the day
    (and month), either fully numeric ("12. 4. 1985", "12.4.1985") or
    with the month name in genitive or nominative form
    ("12. dubna 1985"). The generic ``DateRecognizer`` only covers
    English/ISO formats, and no Czech NER model emitting DATE labels is
    available, so this pattern recognizer provides DATE_TIME coverage
    for Czech-language pipelines.

    Emits the standard ``DATE_TIME`` entity so downstream configuration
    (anonymizer operators, allow-lists) treats Czech dates like any
    other date.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    # Month names in genitive (as used in dates) and nominative form.
    # Longer alternatives come first so e.g. "července" is preferred
    # over its prefix "červen".
    _MONTHS = (
        "ledna|leden|února|únor|března|březen|dubna|duben|"
        "května|květen|července|červenec|června|červen|"
        "srpna|srpen|září|října|říjen|listopadu|listopad|"
        "prosince|prosinec"
    )

    PATTERNS = [
        Pattern(
            "Czech date (d. month yyyy)",
            rf"\b(?:0?[1-9]|[12]\d|3[01])\.?\s(?:{_MONTHS})\s(?:\d{{4}})\b",
            0.6,
        ),
        Pattern(
            "Czech date (d. m. yyyy)",
            r"\b(?:0?[1-9]|[12]\d|3[01])\.\s?(?:0?[1-9]|1[0-2])\.\s?\d{4}\b",
            0.6,
        ),
        Pattern(
            "Czech date (d. month, no year)",
            rf"\b(?:0?[1-9]|[12]\d|3[01])\.?\s(?:{_MONTHS})\b",
            0.2,
        ),
    ]

    CONTEXT = [
        "datum",
        "data",
        "dne",
        "den",
        "narození",
        "narozen",
        "narozena",
        "narodil",
        "narodila",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "DATE_TIME",
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
