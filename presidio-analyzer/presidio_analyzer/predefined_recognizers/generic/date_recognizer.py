import re
from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

_MONTHS = {
    month: number
    for number, month in enumerate(
        "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split(), start=1
    )
}


class DateRecognizer(PatternRecognizer):
    """
    Recognize date using regex.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    PATTERNS = [
        Pattern(
            "Datetime (yyyy-mm-ddThh:mm[:ss[.f]] with timezone)",
            r"\b(?:(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d:[0-5]\d\.\d+([+-][0-2]\d:[0-5]\d|Z))|(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z))|(\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])T[0-2]\d:[0-5]\d([+-][0-2]\d:[0-5]\d|Z)))\b",
            0.8,
        ),
        Pattern(
            "mm/dd/yyyy or mm/dd/yy",
            r"\b(([1-9]|0[1-9]|1[0-2])/([1-9]|0[1-9]|[1-2][0-9]|3[0-1])/(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd/mm/yyyy or dd/mm/yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])/([1-9]|0[1-9]|1[0-2])/(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "yyyy/mm/dd",
            r"\b(\d{4}/([1-9]|0[1-9]|1[0-2])/([1-9]|0[1-9]|[1-2][0-9]|3[0-1]))\b",
            0.6,
        ),
        Pattern(
            "mm-dd-yyyy",
            r"\b(([1-9]|0[1-9]|1[0-2])-([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-\d{4})\b",
            0.6,
        ),
        Pattern(
            "dd-mm-yyyy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-([1-9]|0[1-9]|1[0-2])-\d{4})\b",
            0.6,
        ),
        Pattern(
            "yyyy-mm-dd",
            r"\b(\d{4}-([1-9]|0[1-9]|1[0-2])-([1-9]|0[1-9]|[1-2][0-9]|3[0-1]))\b",
            0.6,
        ),
        Pattern(
            "dd.mm.yyyy or dd.mm.yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])\.([1-9]|0[1-9]|1[0-2])\.(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd-MMM-yyyy or dd-MMM-yy",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "MMM-yyyy or MMM-yy",
            r"\b((JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-(\d{4}|\d{2}))\b",
            0.6,
        ),
        Pattern(
            "dd-MMM or dd-MMM",
            r"\b(([1-9]|0[1-9]|[1-2][0-9]|3[0-1])-(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC))\b",
            0.6,
        ),
        Pattern(
            "mm/yyyy or m/yyyy",
            r"\b(([1-9]|0[1-9]|1[0-2])/\d{4})\b",
            0.2,
        ),
        Pattern(
            "mm/yy or m/yy",
            r"\b(([1-9]|0[1-9]|1[0-2])/\d{2})\b",
            0.1,
        ),
    ]

    CONTEXT = ["date", "birthday"]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "DATE_TIME",
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

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Drop matches that cannot be a real calendar date, such as 2021-02-30.

        The numeric patterns overlap (dd/mm and mm/dd), so a match is only
        dropped when no reading of its parts (year-month-day, month-day-year
        or day-month-year) is a valid date.

        :param pattern_text: Text detected as pattern by regex
        :return: True if the text cannot be a real date
        """
        month_name = re.search(r"[A-Za-z]{3}", pattern_text)
        numbers = [int(n) for n in re.findall(r"\d+", pattern_text.split("T")[0])]
        if month_name:
            month = _MONTHS.get(month_name.group().upper())
            if month is None or not re.match(r"\d", pattern_text):
                return False  # month-year only: nothing to check
            if len(numbers) == 1:
                readings = [(2000, month, numbers[0])]  # no year: allow 29 Feb
            else:
                readings = [(numbers[1], month, numbers[0])]
        elif len(numbers) == 3:
            first, second, third = numbers
            if re.match(r"\d{4}\D", pattern_text):
                readings = [(first, second, third)]
            else:
                readings = [(third, first, second), (third, second, first)]
        else:
            return False

        return not any(self._is_date(*reading) for reading in readings)

    @staticmethod
    def _is_date(year: int, month: int, day: int) -> bool:
        # A two-digit year may be 19xx or 20xx; only 00 differs for leap years.
        years = [year] if year >= 100 else [1900 + year, 2000 + year]
        for y in years:
            try:
                date(y, month, day)
                return True
            except ValueError:
                continue
        return False
