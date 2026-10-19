from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer


class BrCpfRecognizer(PatternRecognizer):
    """
    Recognize the Brazilian individual taxpayer number (CPF).

    The CPF has 11 digits: 9 base digits and 2 check digits (modulo 11).
    Check digit 1 uses weights 10..2 over the 9 base digits, check digit 2 uses
    weights 11..2 over the base digits plus check digit 1. For each digit,
    remainder = sum % 11, and the digit is 0 if remainder < 2, else 11 - remainder.
    Numbers made of one repeated digit (e.g. 111.111.111-11) pass the formula
    but are never issued, so they are rejected.

    Reference: Receita Federal, https://www.gov.br/receitafederal/pt-br/assuntos/meu-cpf
    Implementation cross-checked with python-stdnum (stdnum.br.cpf) and the
    tarja library (https://github.com/macmaia/tarja).

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "br"

    PATTERNS = [
        Pattern("CPF (formatted)", r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", 0.5),
        Pattern(
            "CPF (irregular punctuation)",
            r"\b\d{3}[\s.]?\d{3}[\s.]?\d{3}[\s\-./]?\d{2}\b",
            0.3,
        ),
        Pattern("CPF (digits only)", r"\b\d{11}\b", 0.1),
    ]

    CONTEXT = [
        "cpf",
        "cadastro de pessoa fisica",
        "cadastro de pessoas fisicas",
        "cadastro de pessoa física",
        "cadastro de pessoas físicas",
        "inscrito no cpf",
        "portador do cpf",
        "contribuinte",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pt",
        supported_entity: str = "BR_CPF",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
    ):
        self.replacement_pairs = replacement_pairs or [
            ("-", ""),
            (".", ""),
            (" ", ""),
            ("/", ""),
            ("\n", ""),
        ]
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool indicating whether the validation was successful.
        """
        digits = self.__sanitize_value(pattern_text, self.replacement_pairs)
        if len(digits) != 11 or not digits.isdigit() or len(set(digits)) == 1:
            return False
        return self.__check_digits(digits[:9]) == digits[9:]

    @staticmethod
    def __check_digits(base: str) -> str:
        def digit(numbers: str) -> int:
            weight = len(numbers) + 1
            remainder = sum(int(d) * (weight - i) for i, d in enumerate(numbers)) % 11
            return 0 if remainder < 2 else 11 - remainder

        d1 = digit(base)
        d2 = digit(base + str(d1))
        return f"{d1}{d2}"

    @staticmethod
    def __sanitize_value(text: str, replacement_pairs: List[Tuple[str, str]]) -> str:
        for search_string, replacement_string in replacement_pairs:
            text = text.replace(search_string, replacement_string)
        return text
