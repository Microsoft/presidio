from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class ZaLicensePlateRecognizer(PatternRecognizer):
    """
    Recognize South African vehicle licence plates.

    Provincial formats vary; common layouts include compact suffix forms
    (e.g. ``KD93GKGP``), spaced 2023+ layouts (e.g. ``DK 28 LF GP``), and
    prefix-digit forms (e.g. ``GET 103 WP``).

    Reference:
    https://en.wikipedia.org/wiki/Vehicle_registration_plates_of_South_Africa

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
        for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "za"

    PROVINCE_SUFFIXES = frozenset(
        {"GP", "ZN", "WP", "EC", "NC", "FS", "LP", "MP", "NW"}
    )

    PATTERNS = [
        Pattern(
            "ZA Licence Plate (compact)",
            r"\b[A-Z]{2,4}\d{2,4}[A-Z]{0,4}(?:GP|ZN|WP|EC|NC|FS|LP|MP|NW)\b",
            0.3,
        ),
        Pattern(
            "ZA Licence Plate (spaced)",
            r"\b[A-Z]{2}\s?\d{2}\s?[A-Z]{2}\s?(?:GP|ZN|WP|EC|NC|FS|LP|MP|NW)\b",
            0.3,
        ),
        Pattern(
            "ZA Licence Plate (prefix digits)",
            r"\b[A-Z]{2,3}\s?\d{2,3}\s?(?:GP|ZN|WP|EC|NC|FS|LP|MP|NW)\b",
            0.3,
        ),
        Pattern(
            "ZA Licence Plate (EC numeric prefix)",
            r"\b\d{2,3}\s?[A-Z]{2,3}\s?EC\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "licence plate",
        "license plate",
        "number plate",
        "registration",
        "vehicle registration",
        "natis",
        "enatis",
        "plate number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_LICENSE_PLATE",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        if replacement_pairs is not None:
            self.replacement_pairs = replacement_pairs
        else:
            self.replacement_pairs = [("-", ""), (" ", "")]
        patterns = self.PATTERNS if patterns is None else patterns
        context = self.CONTEXT if context is None else context
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        sanitized = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        ).upper()

        if len(sanitized) < 5:
            return False

        suffix = sanitized[-2:]
        if suffix not in self.PROVINCE_SUFFIXES:
            return False

        body = sanitized[:-2]
        if not body or not any(char.isalpha() for char in body):
            return False

        return True
