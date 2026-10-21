from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class ThTninRecognizer(PatternRecognizer):
    """
    Recognize Thai National ID Number (TNIN).

    The Thai National ID Number (TNIN) is a unique 13-digit number
    issued to all Thai residents.

    The format is N1N2N3N4N5N6N7N8N9N10N11N12N13 where:
    - N1-N12 are the main digits
    - N13 is a check digit calculated using the preceding 12 digits

    The ID card prints the number grouped as N1 N2-N5 N6-N10 N11-N12 N13
    (``1 2345 67890 12 3``), and it is often written with dashes
    (``1-2345-67890-12-3``). Both groupings are matched, with one separator
    used throughout; separators are removed before validation.

    Validation rules:
    - Must be exactly 13 digits
    - First digit (N1) cannot be 0
    - Second digit (N2) cannot be 0
    - Second and third digits (N2N3) cannot be: 28, 29, 59, 68, 69, 78, 79,
      87, 88, 89, 97, 98, 99
      These second and third digits in Thai ID number correspond to Thai provinces,
      so we exclude non-existent or unassigned combinations in Thailand's
      administrative division system. See ISO 3166-2:TH for reference.
    - The 13th digit is a checksum computed modulo 11 from the first 12 digits

    Checksum algorithm:
    - Label first 12 digits N1…N12 (left to right)
    - Compute S = 13·N1 + 12·N2 + … + 2·N12
    - Let x = S mod 11
    - Then check digit N13 = (11 − x) mod 10
    - Equivalently: if x ≤ 1 then N13 = 1 − x; otherwise N13 = 11 − x

    Reference: https://th.wikipedia.org/wiki/เลขประจำตัวประชาชนไทย
               https://th.wikipedia.org/wiki/ISO_3166-2:TH


    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "th"

    # N2N3: province code, excluding unassigned combinations (see docstring)
    _PROVINCE = r"(?:[134][0-9]|2[0-7]|5[0-8]|[67][01234567]|[89][0123456])"

    PATTERNS = [
        Pattern(
            "TNIN (Medium)",
            r"\b[1-9]" + _PROVINCE + r"\d{10}\b",
            0.5,
        ),
        Pattern(
            "TNIN grouped (Medium)",
            # Not part of a longer run of digits grouped with the same separator
            r"(?<!\d)(?:(?<!\d )(?=\d )|(?<!\d-)(?=\d-))[1-9](?P<sep>[ -])"
            + _PROVINCE
            + r"\d{2}(?P=sep)\d{5}(?P=sep)\d{2}(?P=sep)\d(?!\d)(?!(?P=sep)\d)",
            0.5,
        ),
    ]

    CONTEXT = [
        "Thai National ID",
        "Thai ID Number",
        "TNIN",
        "เลขประจำตัวประชาชน",
        "เลขบัตรประชาชน",
        "รหัสปชช",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "th",
        supported_entity: str = "TH_TNIN",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs is not None
            else [("-", ""), (" ", "")]
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

    def validate_result(self, pattern_text: str) -> Union[bool, None]:
        """
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool or None, indicating whether the validation was successful.
        """
        # Pre-processing before validation checks
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        # Check if the sanitized value has the correct length (13 digits)
        if len(sanitized_value) != 13:
            return False

        # Check if all characters are digits
        if not sanitized_value.isdigit():
            return False

        # Validate TNIN checksum (format validation is handled by regex)
        return self._validate_checksum(sanitized_value)

    def _validate_checksum(self, tnin: str) -> bool:
        """
        Validate the checksum of Thai TNIN.

        Checksum algorithm:
        - Label first 12 digits N1…N12 (left to right)
        - Compute S = 13·N1 + 12·N2 + … + 2·N12
        - Let x = S mod 11
        - Then check digit N13 = (11 − x) mod 10

        :param tnin: The TNIN to validate
        :return: True if checksum is valid, False otherwise
        """
        # Calculate weighted sum: 13*N1 + 12*N2 + ... + 2*N12
        weights = list(range(13, 1, -1))  # [13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2]

        total_sum = 0
        for i in range(12):  # First 12 digits
            total_sum += weights[i] * int(tnin[i])

        # Calculate x = S mod 11
        x = total_sum % 11

        # Calculate expected check digit: (11 - x) mod 10
        if x <= 1:
            expected_check_digit = 1 - x
        else:
            expected_check_digit = 11 - x

        # Compare with actual check digit
        actual_check_digit = int(tnin[12])

        return expected_check_digit == actual_check_digit
