from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class CzBirthNumberRecognizer(PatternRecognizer):
    """
    Recognizes the Czech birth number (rodné číslo).

    The rodné číslo is the national identification number assigned to every
    person registered in the Czech Republic. It encodes the date of birth and
    sex of the holder and is the most sensitive Czech personal identifier,
    appearing on birth certificates, identity cards and health documents.

    Legal basis: § 13 zákona č. 133/2000 Sb., o evidenci obyvatel a rodných
    číslech. Data protection: GDPR Art. 87 (national identification numbers),
    zákon č. 110/2019 Sb.

    Format: YYMMDD/SSS (9 digits, issued until 1953) or YYMMDD/SSSS
    (10 digits, issued since 1954), optionally written without the slash.

        - YY: year of birth (2 digits)
        - MM: month of birth; +50 for women. Since 2004 also +20 (men) and
          +70 (women) when the serial pool for a day is exhausted
          (valid ranges: 01-12, 21-32, 51-62, 71-82)
        - DD: day of birth (01-31)
        - SSS(S): serial suffix; 10-digit numbers carry a check digit

    Checksum (10-digit numbers only): the whole number must be divisible
    by 11. Numbers issued between 1954 and 1985 may instead satisfy the
    historical exception where the first 9 digits mod 11 equal 10 and the
    check digit is 0.

    Examples (fictitious): 780123/0107, 855612/0111

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "cz"

    # Month field: 01-12 (men), 21-32 (men, post-2004), 51-62 (women),
    # 71-82 (women, post-2004). Day field: 01-31.
    _MM = r"(?:0[1-9]|1[0-2]|2[1-9]|3[0-2]|5[1-9]|6[0-2]|7[1-9]|8[0-2])"
    _DD = r"(?:0[1-9]|[12]\d|3[01])"

    PATTERNS = [
        Pattern(
            "Rodné číslo (YYMMDD/SSSS)",
            rf"(?<![\w/-])\d{{2}}{_MM}{_DD}/\d{{3,4}}(?![\w/-])",
            0.5,
        ),
        Pattern(
            "Rodné číslo (no separator)",
            rf"(?<![\w/.-])\d{{2}}{_MM}{_DD}\d{{3,4}}(?![\w/-])",
            0.3,
        ),
    ]

    CONTEXT = [
        "rodné",
        "rodného",
        "rodným",
        "narození",
        "narozen",
        "narozena",
        "rodne cislo",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "cs",
        supported_entity: str = "CZ_BIRTH_NUMBER",
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
        Validate the rodné číslo using the official mod 11 rule.

        10-digit numbers (issued since 1954) must be divisible by 11, or
        satisfy the 1954-1985 historical exception (first 9 digits mod 11
        equal 10 with a 0 check digit). A checksum pass promotes the match
        to MAX_SCORE.

        A checksum failure returns ``None`` instead of ``False``: the date
        part is already enforced by the pattern, 9-digit numbers carry no
        check digit at all, and real-world data contains legacy numbers, so
        the match keeps its base pattern score and the ContextAwareEnhancer
        drives the final confidence via context words ("rodné číslo", ...).

        :param pattern_text: the text to validate (with or without slash)
        :return: True if the checksum is valid, False if structurally
                 impossible, None to fall back to the pattern score
        """
        digits = pattern_text.replace("/", "").strip()

        if not digits.isdigit() or len(digits) not in (9, 10):
            return False

        # The serial suffix 000 was never assigned.
        if digits[6:].lstrip("0") == "":
            return False

        if len(digits) == 9:
            # Pre-1954 numbers have no check digit.
            return None

        if int(digits) % 11 == 0:
            return True

        # Historical exception for ~1000 numbers issued 1954-1985.
        if int(digits[:9]) % 11 == 10 and digits[9] == "0":
            return True

        return None
