from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class PhTinRecognizer(PatternRecognizer):
    """
    Recognizes Philippines Taxpayer Identification Number (TIN).

    The TIN is a 9 or 12-digit number issued by the Bureau of Internal Revenue (BIR).
    The 9th digit is a check digit calculated using a weighted modulo 11 algorithm.
    The last 3 digits (in the 12-digit version) represent the branch code (default 000).

    Formats: XXXXXXXXX, XXXXXXXXXXXX, XXX-XXX-XXX, or XXX-XXX-XXX-XXX
    Reference: https://www.bir.gov.ph/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    """

    COUNTRY_CODE = "ph"

    PATTERNS = [
        Pattern(
            "TIN (Low)",
            r"\b(\d{3}-\d{3}-\d{3}(-\d{3})?)\b",
            0.05,
        ),
        Pattern(
            "TIN (Very Low)",
            r"\b(\d{9}|\d{12})\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "tin",
        "taxpayer identification number",
        "bir",
        "taxpayer id",
        "tax id",
        "rdo",
        "revenue district office",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "PH_TIN",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the Philippines TIN fails weighted modulo 11 validation.

        :param pattern_text: The text to validate
        :return: True if invalid, False otherwise
        """
        return not self._is_valid_tin(pattern_text)

    def _is_valid_tin(self, pattern_text: str) -> bool:
        """Validate the Philippines TIN using weighted modulo 11."""
        # Clean the input
        for search, replace in self.replacement_pairs:
            pattern_text = pattern_text.replace(search, replace)

        if not pattern_text.isdigit():
            return False

        if len(pattern_text) not in (9, 12):
            return False

        # Weights for the first 8 digits
        weights = [9, 8, 7, 6, 5, 4, 3, 2]

        # Calculate sum of first 8 digits multiplied by weights
        total_sum = 0
        for i in range(8):
            total_sum += int(pattern_text[i]) * weights[i]

        # Modulo 11 of the sum
        remainder = total_sum % 11

        # The 9th digit is the check digit
        # Note: If remainder is 10, it's usually not issued or handled specifically.
        # Most implementations for BIR TIN treat the remainder as the check digit.
        check_digit = int(pattern_text[8])

        return remainder == check_digit
