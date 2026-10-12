from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class KrBrnRecognizer(PatternRecognizer):
    """
    Recognize Korean Business Registration Number (BRN).

    The Korean Business Registration Number (BRN) is a 10-digit number
    assigned to businesses in South Korea for taxation purposes.

    The format is AAA-BB-CCCCC where:
    - AAA: District office code
    - BB: Type of business code
    - CCCCC: Serial number and check digit

    Reference: https://org-id.guide/list/KR-BRN

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    to be used during pattern matching (e.g., removing dashes).
    """

    COUNTRY_CODE = "kr"

    PATTERNS = [
        Pattern(
            "BRN (Weak)",
            r"(?<!\d)\d{3}-\d{2}-\d{5}(?!\d)",
            0.1,
        ),
        Pattern(
            "BRN (Very weak)",
            r"(?<!\d)\d{10}(?!\d)",
            0.05,
        ),
    ]

    CONTEXT = [
        "사업자등록번호",
        "사업자번호",
        "사업자",
        "BRN",
        "Business Registration Number",
        "Korean BRN",
        "business number",
        "tax registration number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ko",
        supported_entity: str = "KR_BRN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs if replacement_pairs else [("-", "")]

        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Union[bool, None]:
        """
        Validate the pattern logic by running a checksum on a detected BRN.

        :param pattern_text: The text detected by the regex engine.
        :return: True if validation is successful, False otherwise.
        """
        # Sanitize the value by removing dashes
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        # BRN must be exactly 10 digits
        if len(sanitized_value) != 10:
            return False

        if not sanitized_value.isdigit():
            return False

        return self._validate_checksum(sanitized_value)

    def _validate_checksum(self, brn: str) -> bool:
        """
        Validate the checksum of Korean Business Registration Number.

        The validation algorithm:
        1. Multiply the first 9 digits by the magic keys: [1, 3, 7, 1, 3, 7, 1, 3, 5].
        2. Sum the results of the first 8 multiplications.
        3. For the 9th digit (index 8):
            Add the product (digit * 5) AND the quotient of (digit * 5) / 10 to the sum.
        4. Take the remainder of the total sum divided by 10.
        5. Subtract the remainder from 10.
            The result (mod 10) should match the 10th digit.

        :param brn: The 10-digit BRN string to validate.
        :return: True if checksum is valid, False otherwise.
        """
        digits = [int(d) for d in brn]
        magic_keys = [1, 3, 7, 1, 3, 7, 1, 3, 5]

        # Step 1 & 2: Calculate sum for the first 8 digits
        total_sum = 0
        for i in range(8):
            total_sum += digits[i] * magic_keys[i]

        # Step 3: Special handling for the 9th digit
        last_key_mul = digits[8] * magic_keys[8]
        total_sum += (last_key_mul // 10) + last_key_mul

        # Step 4 & 5: Validate against the 10th check digit
        remainder = total_sum % 10
        check_digit = (10 - remainder) % 10

        return check_digit == digits[9]
