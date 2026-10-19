from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ZaIncomeTaxNumberRecognizer(PatternRecognizer):
    """
    Recognize South African SARS income tax reference numbers.

    Income tax reference numbers are 10-digit numeric identifiers issued
    by SARS. They commonly start with ``0``, ``1``, ``2``, ``3``, or ``9``.
    The last digit is a check digit calculated with the Luhn (modulus 10)
    algorithm. VAT numbers also have 10 digits but start with ``4`` — use
    ``ZA_VAT_NUMBER`` for those instead.

    Reference:
    https://www.taxtim.com/za/tax-guides/get-a-tax-number
    https://www.oecd.org/tax/automatic-exchange/crs-implementation-and-assistance/tax-identification-numbers/South-Africa-TIN.pdf

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    TAX_NUMBER_LENGTH = 10
    ALLOWED_LEADING_DIGITS = frozenset({"0", "1", "2", "3", "9"})

    PATTERNS = [
        Pattern(
            "South African Income Tax Number",
            r"\b[01239]\d{9}\b",
            0.05,
        ),
    ]

    CONTEXT = [
        "sars",
        "tax reference",
        "income tax",
        "tax number",
        "itr",
        "taxpayer",
        "tax registration",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_INCOME_TAX_NUMBER",
        name: Optional[str] = None,
    ):
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
        return (
            len(pattern_text) == self.TAX_NUMBER_LENGTH
            and pattern_text.isdigit()
            and pattern_text[0] in self.ALLOWED_LEADING_DIGITS
            and self._is_luhn_valid(pattern_text)
        )

    @staticmethod
    def _is_luhn_valid(value: str) -> bool:
        digits = [int(digit) for digit in value]
        checksum = 0
        parity = len(digits) % 2

        for index, digit in enumerate(digits):
            if index % 2 == parity:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit

        return checksum % 10 == 0
