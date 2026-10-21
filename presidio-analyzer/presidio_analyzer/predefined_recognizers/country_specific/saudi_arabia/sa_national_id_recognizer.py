from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class SaNationalIdRecognizer(PatternRecognizer):
    """
    Recognize Saudi Arabia National ID and Iqama (residence permit) numbers.

    The Saudi national identification number is a 10-digit number where:
    - The first digit is 1 for citizens (national ID) or 2 for residents
      (Iqama); any other leading digit is invalid.
    - The 10th digit is a Luhn check digit (ISO/IEC 7812) computed over the
      first nine digits: digits in odd positions (1st, 3rd, 5th, 7th, 9th)
      are doubled and the digits of each product are summed together with
      the remaining digits, and the check digit makes the total divisible
      by 10. For example, the base 110179827 gives a processed sum of 32,
      so the check digit is (10 - (32 % 10)) % 10 = 8 and 1101798278 is a
      valid number.

    Format reference: Microsoft Learn, "Saudi Arabia National ID" sensitive
    information type definition (10 consecutive digits). The Luhn checksum
    follows the implementation of the open-source luhn-validator and
    luhncheck packages, which both use Saudi national and resident ID
    numbers as their worked example.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "sa"

    PATTERNS = [
        Pattern(
            "SA_NATIONAL_ID",
            r"\b[12][0-9]{9}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "iqama",
        "national id",
        "national identification number",
        "residence permit",
        "saudi",
        "kingdom of saudi arabia",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "SA_NATIONAL_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = replacement_pairs if replacement_pairs else []

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
        Validate the pattern logic by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool or None, indicating whether the validation was successful.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 10 or not sanitized_value.isdigit():
            return False

        if sanitized_value[0] not in ("1", "2"):
            return False

        # All-same-digit values are trivially not issued IDs. One of them
        # (2222222222) passes the raw Luhn check, so reject them explicitly.
        if len(set(sanitized_value)) == 1:
            return False

        return self._validate_checksum(sanitized_value)

    def _validate_checksum(self, number: str) -> bool:
        """
        Validate a Saudi national identification number with the Luhn checksum.

        Digits in odd positions (counting from 1 at the left) are doubled and
        the digits of each product are summed; the number is valid when the
        total over all ten digits is divisible by 10.

        :param number: The 10-digit number to validate
        :return: True if checksum is valid, False otherwise
        """
        total = 0
        for index, digit_char in enumerate(number):
            digit = int(digit_char)
            if index % 2 == 0:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit

        return total % 10 == 0
