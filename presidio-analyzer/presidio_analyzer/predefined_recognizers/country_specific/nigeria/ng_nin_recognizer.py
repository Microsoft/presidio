from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class NgNinRecognizer(PatternRecognizer):
    """
    Recognizes Nigerian National Identification Number (NIN).

    The NIN is an 11-digit number issued by the National Identity Management
    Commission (NIMC). The last digit is a Verhoeff checksum.

    Reference: https://nimc.gov.ng/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "ng"

    PATTERNS = [
        Pattern(
            "NIN (Very Weak)",
            r"\b\d{11}\b",
            0.01,
        ),
    ]

    CONTEXT = [
        "nin",
        "national identification number",
        "national identity number",
        "nimc",
        "national identity",
        "nigeria id",
        "nigerian identification",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "NG_NIN",
        name: Optional[str] = None,
    ) -> None:
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:
        """Validate the NIN by checking length, digits, and Verhoeff checksum."""
        return self.__check_nin(pattern_text)

    def __check_nin(self, value: str) -> bool:
        return (
            len(value) == 11 and value.isnumeric() and self._is_verhoeff_number(value)
        )

    @staticmethod
    def _is_verhoeff_number(value: str) -> bool:
        """
        Check if the digits pass the Verhoeff checksum.

        The digit string is used directly (not ``int(value)``) so a leading
        zero is preserved — an 11-digit NIN such as ``00000000005`` must not be
        shortened before the checksum is computed.

        :param value: Numeric NIN string to validate
        :return: True if the number passes the Verhoeff checksum
        """
        __d__ = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
            [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
            [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
            [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
            [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
            [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
            [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
            [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
            [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
        ]
        __p__ = [
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
            [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
            [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
            [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
            [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
            [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
            [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
            [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
        ]
        __inv__ = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

        c = 0
        inverted_number = list(map(int, reversed(value)))
        for i in range(len(inverted_number)):
            c = __d__[c][__p__[i % 8][inverted_number[i]]]
        return __inv__[c] == 0
