from datetime import datetime
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class FiPersonalIdentityCodeRecognizer(PatternRecognizer):
    """
    Recognizes and validates Finnish Personal Identity Codes (Henkilötunnus).

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "fi"

    PATTERNS = [
        Pattern(
            "Finnish Personal Identity Code (Medium)",
            r"\b(\d{6})([-+ABCDEFYXWVU])(\d{3})([0123456789ABCDEFHJKLMNPRSTUVWXY])\b",
            0.5,
        ),
        Pattern(
            "Finnish Personal Identity Code (Very Weak)",
            r"(\d{6})([-+ABCDEFYXWVU])(\d{3})([0123456789ABCDEFHJKLMNPRSTUVWXY])",
            0.1,
        ),
    ]
    CONTEXT = ["hetu", "henkilötunnus", "personbeteckningen", "personal identity code"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "fi",
        supported_entity: str = "FI_PERSONAL_IDENTITY_CODE",
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
        """Validate the pattern by using the control character."""

        # More information on the validation logic from:
        # https://dvv.fi/en/personal-identity-code
        # Under "How is the control character for a personal identity code calculated?".
        if len(pattern_text) != 11:
            return False

        date_part = pattern_text[0:6]
        # The 7th character encodes the century, which is needed to validate the
        # date: strptime only sees the 2-digit year (and maps it to the 2000s),
        # so "290200+..." (29 Feb 1800) is wrongly accepted even though 1800 is
        # not a leap year. Resolve the century from the separator and validate
        # against the full year.
        century_by_separator = {
            "+": 1800,
            "-": 1900,
            "Y": 1900,
            "X": 1900,
            "W": 1900,
            "V": 1900,
            "U": 1900,
            "A": 2000,
            "B": 2000,
            "C": 2000,
            "D": 2000,
            "E": 2000,
            "F": 2000,
        }
        # The separator is constrained to the keys above by the pattern, so a
        # default is only a safeguard for direct calls with other text.
        century = century_by_separator.get(pattern_text[6], 2000)
        try:
            # Checking if we do not have invalid dates e.g. 310211.
            datetime(
                century + int(date_part[4:6]),
                int(date_part[2:4]),
                int(date_part[0:2]),
            )
        except ValueError:
            return False
        individual_number = pattern_text[7:10]
        # The control character is defined in upper case; the pattern is matched
        # case-insensitively, so upper-case it before comparing or a valid code
        # written with a lower-case control character would be rejected.
        control_character = pattern_text[-1].upper()
        valid_control_characters = "0123456789ABCDEFHJKLMNPRSTUVWXY"
        number_to_check = int(date_part + individual_number)
        return valid_control_characters[number_to_check % 31] == control_character
