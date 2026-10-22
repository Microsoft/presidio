from datetime import date
from typing import List, Optional, Tuple

from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer


class AeEmiratesIdRecognizer(PatternRecognizer):
    """
    Recognize United Arab Emirates Emirates ID numbers.

    The Emirates ID number is a 15-digit number issued by the Federal
    Authority for Identity, Citizenship, Customs and Port Security (ICP),
    formerly the Emirates Identity Authority. It is written in the format
    784-YYYY-NNNNNNN-C:

    - 784 is the ISO country code of the United Arab Emirates.
    - YYYY is a four-digit year, usually the holder's birth year; for
      residents it may instead be the year of first registration, so it is
      not a reliable date of birth.
    - NNNNNNN is a seven-digit serial number.
    - C is a single verification (check) digit.

    The number is also written as 15 continuous digits without dashes.

    Checksum note: the algorithm behind the verification digit is not
    published in an authoritative source, and no worked example with a full
    number could be found to test an implementation against. A regex101
    community library entry for this format states that the Luhn algorithm
    should be applied, but it provides no example number, so the parity of
    the doubling cannot be confirmed. Following the approach of the
    Pakistani CNIC recognizer, this recognizer therefore implements no
    checksum and deliberately does not promote matches on an unverified
    one; it identifies the number using regex, context words and sanity
    checks on the digits.

    Format reference: Emirates Identity Authority's description of the ID
    number structure (784 country code, four-digit year part, seven-digit
    serial part, one verification digit), as reported by Emirates247,
    "Emirates ID number allocated for life", 2016-01-17.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    :param replacement_pairs: List of tuples with potential replacement values
    for different strings to be used during pattern matching.
    This can allow a greater variety in input, for example by removing dashes or spaces.
    """

    COUNTRY_CODE = "ae"

    PATTERNS = [
        Pattern(
            "AE_EMIRATES_ID (strong)",
            r"\b784-[0-9]{4}-[0-9]{7}-[0-9]\b",
            0.65,
        ),
        Pattern(
            "AE_EMIRATES_ID (weak)",
            r"\b784[0-9]{12}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "emirates id",
        "emirates identity card",
        "uae national id",
        "identity card number",
        "uid",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "AE_EMIRATES_ID",
        replacement_pairs: Optional[List[Tuple[str, str]]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.replacement_pairs = (
            replacement_pairs if replacement_pairs else [("-", ""), (" ", "")]
        )
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text cannot be an AE_EMIRATES_ID entity.

        No verified checksum exists for this recognizer (see the class
        docstring), so invalidation is based on sanity checks: the sanitized
        value must be 15 digits starting with the 784 country code, the
        year part must be a plausible birth or registration year, and the
        serial part must not be a trivial sequential run such as 1234567,
        which is the serial used by published format examples.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated
        """
        sanitized_value = EntityRecognizer.sanitize_value(
            pattern_text, self.replacement_pairs
        )
        if len(sanitized_value) != 15 or not sanitized_value.isnumeric():
            return True
        if not sanitized_value.startswith("784"):
            return True
        if len(set(sanitized_value)) == 1:
            # cannot be all the same digit
            return True
        year = int(sanitized_value[3:7])
        if year < 1900 or year > date.today().year:
            # the year part is a birth or registration year, so values
            # outside the plausible range are not issued IDs
            return True
        if self._is_sequential(sanitized_value[7:14]):
            # the serial part cannot be a trivially sequential run
            return True
        return False

    @staticmethod
    def _is_sequential(digits: str) -> bool:
        """
        Check if the digits form a sequential run, allowing 9 to wrap to 0.

        For example, 1234567 ascends by one each step, and 7654321 descends
        by one each step.

        :param digits: Numeric string to check
        :return: True if every digit follows the previous one sequentially
        """
        values = [int(digit) for digit in digits]
        ascending = all(
            (values[i] + 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        descending = all(
            (values[i] - 1) % 10 == values[i + 1] for i in range(len(values) - 1)
        )
        return ascending or descending
