from typing import List, Optional, Tuple

from presidio_analyzer import Pattern, PatternRecognizer

# Receita Federal, CNPJ alfanumerico FAQ (official example 12.ABC.345/01DE-35):
# https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/perguntas-e-respostas/cnpj/cnpj-alfanumerico.pdf  # noqa: E501
# Serpro, check digit calculation:
# https://www.serpro.gov.br/menu/noticias/videos/calculodvcnpjalfanaumerico.pdf


class BrCnpjRecognizer(PatternRecognizer):
    """
    Recognize the Brazilian company registration number (CNPJ).

    Covers both the numeric and the alphanumeric format.

    Since July 2026 the Receita Federal issues alphanumeric CNPJs: the first 12
    positions accept [0-9A-Z] and the 2 check digits stay numeric. Existing
    numeric CNPJs remain valid and the same algorithm covers both:
    each character is worth ord(c) - 48 (digits 0-9, letters A-Z = 17-42);
    check digit 1 uses weights 5,4,3,2,9,8,7,6,5,4,3,2; check digit 2 uses
    6,5,4,3,2,9,8,7,6,5,4,3,2 over the 12 positions plus check digit 1.
    For each digit, remainder = sum % 11, and the digit is 0 if remainder < 2,
    else 11 - remainder.

    Reference: Receita Federal, CNPJ alfanumerico FAQ (official example
    12.ABC.345/01DE-35), and Serpro, check digit calculation. Both links are
    at the top of this file.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    """

    COUNTRY_CODE = "br"

    PATTERNS = [
        Pattern(
            "CNPJ (formatted)",
            r"\b[0-9A-Za-z]{2}\.[0-9A-Za-z]{3}\.[0-9A-Za-z]{3}/[0-9A-Za-z]{4}-\d{2}\b",
            0.5,
        ),
        Pattern("CNPJ (compact)", r"\b[0-9A-Za-z]{12}\d{2}\b", 0.1),
    ]

    CONTEXT = [
        "cnpj",
        "cadastro nacional da pessoa juridica",
        "cadastro nacional da pessoa jurídica",
        "inscrita no cnpj",
        "inscrita sob o",
        "pessoa juridica",
        "pessoa jurídica",
        "empresa",
    ]

    _WEIGHTS_1 = (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)
    _WEIGHTS_2 = (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "pt",
        supported_entity: str = "BR_CNPJ",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
    ):
        self.replacement_pairs = replacement_pairs or [
            ("-", ""),
            (".", ""),
            ("/", ""),
            (" ", ""),
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
        value = self.__sanitize_value(pattern_text, self.replacement_pairs).upper()
        if len(value) != 14 or not value[12:].isdigit():
            return False
        if not all(c.isdigit() or "A" <= c <= "Z" for c in value):
            return False
        if len(set(value)) == 1:
            return False
        d1 = self.__digit(value[:12], self._WEIGHTS_1)
        d2 = self.__digit(value[:12] + str(d1), self._WEIGHTS_2)
        return value[12:] == f"{d1}{d2}"

    @staticmethod
    def __digit(chars: str, weights: Tuple[int, ...]) -> int:
        remainder = sum((ord(c) - 48) * w for c, w in zip(chars, weights)) % 11
        return 0 if remainder < 2 else 11 - remainder

    @staticmethod
    def __sanitize_value(text: str, replacement_pairs: List[Tuple[str, str]]) -> str:
        for search_string, replacement_string in replacement_pairs:
            text = text.replace(search_string, replacement_string)
        return text
