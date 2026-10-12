from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class KrDriverLicenseRecognizer(PatternRecognizer):
    """
    Recognize Korean Driver's License Number.

    The Korean Driver's License Number consists of 12 digits,
    typically formatted as AA-BB-CCCCCC-DD.

    Format Breakdown:
    - AA: Regional code
    - BB: Year of issuance (last two digits of the year)
    - CCCCCC: Serial number
    - DD: Check digit (Verification number; not publicly disclosed)

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes.
    """

    COUNTRY_CODE = "kr"

    PATTERNS = [
        Pattern(
            "Driver License (very weak)",
            r"(?<!\d)(\d{2})[- ]?(\d{2})[- ]?(\d{6})[- ]?(\d{2})(?!\d)",
            0.05,
        )
    ]

    CONTEXT = [
        "운전면허",
        "운전면허번호",
        "면허번호",
        "Korean driver license",
        "Korean driver's license",
    ]

    REGION_CODES = {
        "11",
        "12",
        "13",
        "14",
        "15",
        "16",
        "17",
        "18",
        "19",
        "20",
        "21",
        "22",
        "23",
        "24",
        "25",
        "26",
        "28",
    }

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ko",
        supported_entity: str = "KR_DRIVER_LICENSE",
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

    def validate_result(self, pattern_text: str) -> bool:
        """
        Validate length, region code.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool or None, indicating whether the validation was successful.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 12:
            return False

        if not sanitized_value.isdigit():
            return False

        region_code = sanitized_value[:2]
        if region_code not in self.REGION_CODES:
            return False

        return True
