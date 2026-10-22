from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class JpMyNumberRecognizer(PatternRecognizer):
    """
    Recognize Japanese Individual Number (My Number / 個人番号).

    The Individual Number (My Number / マイナンバー) is a 12-digit number
    assigned to every resident in Japan for social security, tax, and
    disaster response.

    The format is N1N2N3N4N5N6N7N8N9N10N11C where:
    - N1 through N11 are digits.
    - C is the 12th digit (check digit).

    Validation rules:
    - Must be exactly 12 digits.
    - The 12th digit is a checksum calculated modulo 11 from the first 11 digits:
      Let P_n be the n-th digit counting from right to left before the check digit
      (i.e. P_1 = N11, P_2 = N10, ..., P_11 = N1).
      The weight Q_n is:
        - If 1 <= n <= 6: Q_n = n + 1
        - If 7 <= n <= 11: Q_n = n - 5
      Compute sum S = sum(P_n * Q_n) for n = 1 to 11.
      Let remainder R = S % 11.
      The check digit C is:
        - If R <= 1: C = 0
        - If R > 1: C = 11 - R

    Reference:
    https://www.digital.go.jp/policies/posts/mynumber_resources
    Enforcement Regulations for the Act on the Use of Numbers to Identify a
    Specific Individual in the Administrative Procedure
    (行政手続における特定の個人を識別するための番号の利用等に関する法律施行規則),
    Article 5.

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
            "My Number (Separated)",
            r"(?<!\d)\d{4}[\s-]\d{4}[\s-]\d{4}(?!\d)",
            0.5,
        ),
        Pattern(
            "My Number (Contiguous)",
            r"(?<!\d)\d{12}(?!\d)",
            0.1,
        ),
    ]

    CONTEXT = [
        "マイナンバー",
        "個人番号",
        "マイナンバーカード",
        "個人番号カード",
        "通知カード",
        "My Number",
        "my number",
        "Individual Number",
        "individual number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ja",
        supported_entity: str = "JP_MY_NUMBER",
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
        Validate the pattern logic by running a checksum on a detected My Number.

        :param pattern_text: The text detected by the regex engine.
        :return: True if validation is successful, False otherwise.
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )

        if len(sanitized_value) != 12 or not sanitized_value.isdigit():
            return False

        return self._validate_checksum(sanitized_value)

    @staticmethod
    def _validate_checksum(my_number: str) -> bool:
        """Validate the check digit of a 12-digit Japanese My Number."""
        s = 0
        for n in range(1, 12):
            p_n = int(my_number[11 - n])
            q_n = n + 1 if 1 <= n <= 6 else n - 5
            s += p_n * q_n

        rem = s % 11
        expected_check_digit = 0 if rem <= 1 else 11 - rem
        return int(my_number[11]) == expected_check_digit
