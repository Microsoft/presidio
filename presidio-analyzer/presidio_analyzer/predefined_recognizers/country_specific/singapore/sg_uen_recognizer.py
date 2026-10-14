from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

# This class includes references to an UEN checksum validation implementation
# written in Javascript which can be found at:
# https://gist.github.com/mervintankw/90d5660c6ab03a83ddf77fa8199a0e52


class SgUenRecognizer(PatternRecognizer):
    """
    Recognize Singapore UEN (Unique Entity Number) using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "sg"

    PATTERNS = [
        Pattern(
            "UEN (low)",
            r"\b\d{8}[A-Z]\b|\b\d{9}[A-Z]\b|\b[TSR]\d{2}[A-Z]{2}\d{4}[A-Z]\b",
            0.3,
        )
    ]

    CONTEXT = ["uen", "unique entity number", "business registration", "ACRA"]

    UEN_FORMAT_A_WEIGHT = (10, 4, 9, 3, 8, 2, 7, 1)
    UEN_FORMAT_A_ALPHABET = "XMKECAWLJDB"
    UEN_FORMAT_B_WEIGHT = (10, 8, 6, 4, 9, 7, 5, 3, 1)
    UEN_FORMAT_B_ALPHABET = "ZKCMDNERGWH"
    UEN_FORMAT_C_WEIGHT = (4, 3, 5, 3, 10, 2, 2, 5, 7)
    UEN_FORMAT_C_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWX0123456789"
    UEN_FORMAT_C_PREFIX = {"T", "S", "R"}
    UEN_FORMAT_C_ENTITY_TYPE = {
        "LP",
        "LL",
        "FC",
        "PF",
        "RF",
        "MQ",
        "MM",
        "NB",
        "CC",
        "CS",
        "MB",
        "FM",
        "GS",
        "DP",
        "CP",
        "NR",
        "CM",
        "CD",
        "MD",
        "HS",
        "VH",
        "CH",
        "MH",
        "CL",
        "XL",
        "CX",
        "HC",
        "RP",
        "TU",
        "TC",
        "FB",
        "FN",
        "PA",
        "PB",
        "SS",
        "MC",
        "SM",
        "GA",
        "GB",
    }

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "SG_UEN",
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
        # The prefix, entity-type and check letters are defined in upper case;
        # the pattern is matched case-insensitively, so normalize before the
        # checksum or a valid UEN written in lower case would be rejected.
        pattern_text = pattern_text.upper()

        if len(pattern_text) == 9:
            # Checksum validation for UEN format A
            return self.validate_uen_format_a(pattern_text)
        elif len(pattern_text) == 10 and pattern_text[0].isalpha():
            # Checksum validation for UEN format C
            return self.validate_uen_format_c(pattern_text)
        elif len(pattern_text) == 10:
            # Checksum validation for UEN format B
            return self.validate_uen_format_b(pattern_text)

        return False

    @staticmethod
    def validate_uen_format_a(uen: str) -> bool:
        """
        Validate the UEN format A using checksum.

        :param uen: The UEN to validate.
        :return: True if the UEN is valid according to its respective
        format, False otherwise.
        """
        check_digit = uen[-1]

        weighted_sum = sum(
            int(n) * w for n, w in zip(uen[:-1], SgUenRecognizer.UEN_FORMAT_A_WEIGHT)
        )

        checksum = SgUenRecognizer.UEN_FORMAT_A_ALPHABET[weighted_sum % 11]

        return check_digit == checksum

    @staticmethod
    def validate_uen_format_b(uen: str) -> bool:
        """
        Validate the UEN format B using checksum.

        :param uen: The UEN to validate.
        :return: True if the UEN is valid according to its respective
        format, False otherwise.
        """
        check_digit = uen[-1]
        year_of_registration = int(uen[0:4])

        # Check if the year of registration is not in the future
        if year_of_registration > date.today().year:
            return False

        weighted_sum = sum(
            int(n) * w for n, w in zip(uen[:-1], SgUenRecognizer.UEN_FORMAT_B_WEIGHT)
        )

        checksum = SgUenRecognizer.UEN_FORMAT_B_ALPHABET[weighted_sum % 11]

        return check_digit == checksum

    @staticmethod
    def validate_uen_format_c(uen: str) -> bool:
        """
        Validate the UEN format C using checksum.

        :param uen: The UEN to validate.
        :return: True if the UEN is valid according to its respective
        format, False otherwise.
        """
        check_digit = uen[-1]

        if uen[0] not in SgUenRecognizer.UEN_FORMAT_C_PREFIX:
            return False

        entity_type = uen[3:5]

        if entity_type not in SgUenRecognizer.UEN_FORMAT_C_ENTITY_TYPE:
            return False

        # The pattern's \d also matches non-ASCII digits, which are not in the alphabet.
        if any(n not in SgUenRecognizer.UEN_FORMAT_C_ALPHABET for n in uen[:-1]):
            return False

        weighted_sum = sum(
            SgUenRecognizer.UEN_FORMAT_C_ALPHABET.index(n) * w
            for n, w in zip(uen[:-1], SgUenRecognizer.UEN_FORMAT_C_WEIGHT)
        )

        checksum = SgUenRecognizer.UEN_FORMAT_C_ALPHABET[(weighted_sum - 5) % 11]

        return check_digit == checksum
