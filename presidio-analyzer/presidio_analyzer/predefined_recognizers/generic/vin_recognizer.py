from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class VinRecognizer(PatternRecognizer):
    """
    Recognize Vehicle Identification Numbers (VIN) using regex.

    VINs are 17-character identifiers assigned to motor vehicles per ISO 3779.
    The letters I, O, and Q are excluded to avoid confusion with 1 and 0.
    Position 9 is a check digit in North American VINs (FMVSS 115).

    ref:
    - https://en.wikipedia.org/wiki/Vehicle_identification_number
    - https://www.nhtsa.gov/vin-decoder
    """

    TRANSLITERATION = {
        "A": 1,
        "B": 2,
        "C": 3,
        "D": 4,
        "E": 5,
        "F": 6,
        "G": 7,
        "H": 8,
        "J": 1,
        "K": 2,
        "L": 3,
        "M": 4,
        "N": 5,
        "P": 7,
        "R": 9,
        "S": 2,
        "T": 3,
        "U": 4,
        "V": 5,
        "W": 6,
        "X": 7,
        "Y": 8,
        "Z": 9,
    }

    WEIGHTS = [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2]

    # WMI first character 1-5 indicates North America (ISO 3780 region codes).
    NA_WMI_PREFIXES = frozenset("12345")

    PATTERNS = [
        Pattern(
            "VIN",
            r"\b[A-HJ-NPR-Z0-9]{17}\b",
            0.5,
        ),
    ]

    CONTEXT = [
        "vin",
        "vehicle identification",
        "vehicle identification number",
        "chassis",
        "chassis number",
        "vehicle",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "VIN",
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
        Validate the North American mod-11 check digit at position 9.

        For North American VINs (WMI prefix 1-5), a mismatched check digit
        returns False so invalid NA VINs are filtered out. For other regions,
        returns None on mismatch so the base pattern score is preserved.

        :param pattern_text: Text detected as pattern by regex
        :return: True if mod-11 check digit matches (any region), False if
            NA-applicable and mismatched or structurally invalid, None if
            non-NA and mismatched
        """
        vin = pattern_text.upper()
        if len(vin) != 17:
            return False

        total = 0
        for index, char in enumerate(vin):
            if char.isdigit():
                value = int(char)
            elif char in self.TRANSLITERATION:
                value = self.TRANSLITERATION[char]
            else:
                return False
            total += value * self.WEIGHTS[index]

        remainder = total % 11
        expected = "X" if remainder == 10 else str(remainder)
        actual = vin[8]

        if actual == expected:
            return True
        if vin[0] in self.NA_WMI_PREFIXES:
            return False
        return None
