"""Taiwan National ID Recognizer."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class TwNationalIdRecognizer(PatternRecognizer):
    """Recognize Taiwan National ID using patterns and checksums."""

    PATTERNS = [
        Pattern(
            "TW National ID (Strict)",
            r"(?<![A-Za-z0-9])[A-Z][1289][0-9]{8}(?![A-Za-z0-9])",
            0.3,
        )
    ]

    CONTEXT = [
        "身分證",
        "統一證號",
        "國民身分證",
        "tw id",
        "taiwan id",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "zh",
        supported_entity: str = "TW_NATIONAL_ID",
    ):
        """Initialize Taiwan National ID Recognizer."""
        patterns = patterns if patterns is not None else self.PATTERNS
        context = context if context is not None else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject invalid Taiwan ID structures via Modulus-10 checksum.

        Validation applies the standard weighted modulus-10 algorithm.
        """
        if len(pattern_text) != 10:
            return True

        # Presidio uses IGNORECASE by default; explicitly reject
        # lowercase initial letters
        first_char = pattern_text[0]
        if not first_char.isupper():
            return True

        letter_codes = {
            "A": 10,
            "B": 11,
            "C": 12,
            "D": 13,
            "E": 14,
            "F": 15,
            "G": 16,
            "H": 17,
            "I": 34,
            "J": 18,
            "K": 19,
            "L": 20,
            "M": 21,
            "N": 22,
            "O": 35,
            "P": 23,
            "Q": 24,
            "R": 25,
            "S": 26,
            "T": 27,
            "U": 28,
            "V": 29,
            "W": 32,
            "X": 30,
            "Y": 31,
            "Z": 33,
        }

        if first_char not in letter_codes:
            return True

        if pattern_text[1] not in ("1", "2", "8", "9"):
            return True

        try:
            code = letter_codes[first_char]
            n1 = code // 10
            n2 = code % 10

            digits = [n1, n2] + [int(char) for char in pattern_text[1:]]
            weights = [1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1]
            total = sum(d * w for d, w in zip(digits, weights))

            return total % 10 != 0
        except ValueError:
            return True
