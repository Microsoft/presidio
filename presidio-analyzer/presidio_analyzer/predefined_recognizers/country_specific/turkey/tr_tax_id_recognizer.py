from typing import List, Optional, Tuple, Union

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class TrTaxIdRecognizer(PatternRecognizer):
    """
    Recognize Turkish Tax Identification Number (Vergi Kimlik Numarası / VKN).

    The Turkish Tax ID is a 10-digit number, issued by the Revenue
    Administration (Gelir İdaresi Başkanlığı / GİB) to every legal entity and
    to individuals who are not eligible for the 11-digit National ID (TCKN) --
    a foreign national doing business in Turkey, for example. It carries its
    own checksum, distinct from the TCKN's:

    - For i in 0..8 (0-indexed): tmp = (digit[i] + (9 - i)) % 10
    - If tmp == 9, it contributes 9 to the running total; otherwise it
      contributes (tmp * 2 ** (9 - i)) % 9
    - The 10th digit must equal (10 - total % 10) % 10

    Reference: the algorithm is undocumented by GİB itself but is the one
    implemented by GİB's own e-Fatura / e-Devlet integrations and widely
    reproduced in Turkish accounting and ERP software; see
    https://www.gib.gov.tr/ (Gelir İdaresi Başkanlığı).

    A `tax_id` column in a Turkish ERP genuinely mixes VKN (companies) and
    TCKN (sole traders): both are digit-string identifiers of adjacent
    length, so a checksum -- not a length check alone -- is what tells them
    apart. `TrNationalIdRecognizer` is the 11-digit counterpart.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "tr"

    PATTERNS = [
        Pattern(
            "TR_TAX_ID",
            r"\b[0-9]{10}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "vergi kimlik",
        "vergi kimlik no",
        "vergi kimlik numarası",
        "vkn",
        "vergi no",
        "vergi numarası",
        "mükellef",
        "tax id",
        "tax number",
        "turkish tax",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "tr",
        supported_entity: str = "TR_TAX_ID",
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

        return self._validate_checksum(sanitized_value)

    def _validate_checksum(self, vkn: str) -> bool:
        """
        Validate a Turkish Tax ID using the GİB checksum algorithm.

        :param vkn: The VKN to validate
        :return: True if checksum is valid, False otherwise
        """
        digits = [int(d) for d in vkn]

        total = 0
        for i in range(9):
            tmp = (digits[i] + 9 - i) % 10
            total += 9 if tmp == 9 else (tmp * (2 ** (9 - i))) % 9

        check_digit = (10 - total % 10) % 10
        return check_digit == digits[9]
