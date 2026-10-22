from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class JpCorporateNumberRecognizer(PatternRecognizer):
    """
    Recognize Japanese Corporate Number (法人番号 / Hojin Bangou).

    The Corporate Number is a 13-digit identifier assigned by the National Tax Agency
    (国税庁) to corporations and government entities in Japan.

    The format is C N1 N2 N3 N4 N5 N6 N7 N8 N9 N10 N11 N12 where:
    - C is the first digit (check digit).
    - N1 through N12 are the 12 base digits.

    Validation rules:
    - Must be exactly 13 digits.
    - Check digit C is at position 1 (the first digit from the left).
    - The check digit formula:
      Let P_n be the n-th digit of the 12 base digits counting from right to left
      (i.e. P_1 = N12, P_2 = N11, ..., P_12 = N1).
      The weight Q_n is:
        - If n is odd: Q_n = 1
        - If n is even: Q_n = 2
      Compute sum S = sum(P_n * Q_n) for n = 1 to 12.
      Let remainder R = S % 9.
      The check digit C is: C = 9 - R.

    Reference:
    https://www.houjin-bangou.nta.go.jp/houjinbangou-shitei/
    Ordinance on the Designation, etc. of Corporate Numbers
    (法人番号の指定等に関する省令), Article 3.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "jp"

    PATTERNS = [
        Pattern(
            "Corporate Number (Separated)",
            r"(?<!\d)\d{1}[\s-]\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)",
            0.5,
        ),
        Pattern(
            "Corporate Number (Contiguous)",
            r"(?<!\d)\d{13}(?!\d)",
            0.1,
        ),
    ]

    CONTEXT = [
        "法人番号",
        "会社番号",
        "国税庁法人番号",
        "Corporate Number",
        "corporate number",
        "Hojin Bangou",
        "hojin bangou",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ja",
        supported_entity: str = "JP_CORPORATE_NUMBER",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ):
        self.replacement_pairs = (
            replacement_pairs
            if replacement_pairs is not None
            else [("-", ""), (" ", "")]
        )
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Union[bool, None]:
        """
        Validate the pattern logic by running a checksum on a detected Corporate Number.

        :param pattern_text: The text detected by the regex engine.
        :return: True if validation is successful, False otherwise.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 13 or not sanitized_value.isdigit():
            return False

        return self._validate_checksum(sanitized_value)

    @staticmethod
    def _validate_checksum(corporate_number: str) -> bool:
        """Validate the check digit of a 13-digit Japanese Corporate Number."""
        check_digit = int(corporate_number[0])
        base_12 = corporate_number[1:]

        s = 0
        for n in range(1, 13):
            p_n = int(base_12[12 - n])
            q_n = 1 if n % 2 != 0 else 2
            s += p_n * q_n

        rem = s % 9
        expected_check_digit = 9 - rem
        return check_digit == expected_check_digit
