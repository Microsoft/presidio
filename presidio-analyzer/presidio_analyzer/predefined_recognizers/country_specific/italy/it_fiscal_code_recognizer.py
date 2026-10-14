from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ItFiscalCodeRecognizer(PatternRecognizer):
    """
    Recognizes IT Fiscal Code using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "it"

    PATTERNS = [
        Pattern(
            "Fiscal Code",
            (
                r"(?i)((?:[A-Z][AEIOU][AEIOUX]|[AEIOU]X{2}"
                r"|[B-DF-HJ-NP-TV-Z]{2}[A-Z]){2}"
                r"(?:[\dLMNP-V]{2}(?:[A-EHLMPR-T](?:[04LQ][1-9MNP-V]|[15MR][\dLMNP-V]"
                r"|[26NS][0-8LMNP-U])|[DHPS][37PT][0L]|[ACELMRT][37PT][01LM]"
                r"|[AC-EHLMPR-T][26NS][9V])|(?:[02468LNQSU][048LQU]"
                r"|[13579MPRTV][26NS])B[26NS][9V])(?:[A-MZ][1-9MNP-V][\dLMNP-V]{2}"
                r"|[A-M][0L](?:[1-9MNP-V][\dLMNP-V]|[0L][1-9MNP-V]))[A-Z])"
            ),
            0.3,
        ),
    ]
    CONTEXT = ["codice fiscale", "cf"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "it",
        supported_entity: str = "IT_FISCAL_CODE",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> Optional[bool]:
        """
        Validate the pattern logic e.g., by running checksum on a detected pattern.

        :param pattern_text: the text to validated.
        Only the part in text that was detected by the regex engine
        :return: A bool indicating whether the validation was successful.
        """
        pattern_text = pattern_text.upper()
        control = pattern_text[-1]
        text_to_validate = pattern_text[:-1]
        odd_values = text_to_validate[0::2]
        even_values = text_to_validate[1::2]

        # Odd values
        map_odd = {
            "0": 1,
            "1": 0,
            "2": 5,
            "3": 7,
            "4": 9,
            "5": 13,
            "6": 15,
            "7": 17,
            "8": 19,
            "9": 21,
            "A": 1,
            "B": 0,
            "C": 5,
            "D": 7,
            "E": 9,
            "F": 13,
            "G": 15,
            "H": 17,
            "I": 19,
            "J": 21,
            "K": 2,
            "L": 4,
            "M": 18,
            "N": 20,
            "O": 11,
            "P": 3,
            "Q": 6,
            "R": 8,
            "S": 12,
            "T": 14,
            "U": 16,
            "V": 10,
            "W": 22,
            "X": 25,
            "Y": 24,
            "Z": 23,
        }

        # The pattern's \d and case-insensitive [A-Z] also match non-ASCII
        # characters (fullwidth digits, the Kelvin sign) that have no checksum value.
        if any(char not in map_odd for char in text_to_validate):
            return False

        odd_sum = 0
        for char in odd_values:
            odd_sum += map_odd[char]

        # Even values
        map_even = {
            "0": 0,
            "1": 1,
            "2": 2,
            "3": 3,
            "4": 4,
            "5": 5,
            "6": 6,
            "7": 7,
            "8": 8,
            "9": 9,
            "A": 0,
            "B": 1,
            "C": 2,
            "D": 3,
            "E": 4,
            "F": 5,
            "G": 6,
            "H": 7,
            "I": 8,
            "J": 9,
            "K": 10,
            "L": 11,
            "M": 12,
            "N": 13,
            "O": 14,
            "P": 15,
            "Q": 16,
            "R": 17,
            "S": 18,
            "T": 19,
            "U": 20,
            "V": 21,
            "W": 22,
            "X": 23,
            "Y": 24,
            "Z": 25,
        }

        even_sum = 0
        for char in even_values:
            even_sum += map_even[char]

        # Mod value
        map_mod = {
            0: "A",
            1: "B",
            2: "C",
            3: "D",
            4: "E",
            5: "F",
            6: "G",
            7: "H",
            8: "I",
            9: "J",
            10: "K",
            11: "L",
            12: "M",
            13: "N",
            14: "O",
            15: "P",
            16: "Q",
            17: "R",
            18: "S",
            19: "T",
            20: "U",
            21: "V",
            22: "W",
            23: "X",
            24: "Y",
            25: "Z",
        }
        check_value = map_mod[((odd_sum + even_sum) % 26)]

        if check_value == control:
            result = True
        else:
            result = None

        return result
