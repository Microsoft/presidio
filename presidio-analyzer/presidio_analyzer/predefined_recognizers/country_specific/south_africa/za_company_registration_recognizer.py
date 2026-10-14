from datetime import date
from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ZaCompanyRegistrationRecognizer(PatternRecognizer):
    """
    Recognize South African company registration numbers (CIPC).

    Modern private and public companies use ``YYYY/NNNNNN/NN`` (year,
    sequence, company-type suffix). Legacy formats include prefixed codes
    such as ``CK`` (close corporation) and other CIPC entity prefixes.

    Reference:
    https://support.tradeshield.ai/support/solutions/articles/153000256853-cipc-company-codes-types-status-the-complete-guide

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    LEGACY_PREFIXES = frozenset({"CK", "K", "T", "W", "B", "M", "N", "NR"})

    PATTERNS = [
        Pattern(
            "South African Company Registration (modern)",
            r"\b(?:19|20)\d{2}/\d{6}/\d{2}\b",
            0.4,
        ),
        Pattern(
            "South African Company Registration (legacy)",
            r"\b(?:CK|K|T|W|B|M|N|NR)\d{4}/\d{6}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "cipc",
        "company registration",
        "registration number",
        "close corporation",
        "company reg",
        "enterprise number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_COMPANY_REGISTRATION",
        name: Optional[str] = None,
    ):
        patterns = self.PATTERNS if patterns is None else patterns
        context = self.CONTEXT if context is None else context
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        text = pattern_text.upper()
        parts = text.split("/")
        if len(parts) == 3 and parts[0].isdigit():
            return self._validate_modern_format(text)
        if len(parts) == 2:
            return self._validate_legacy_format(text)
        return False

    def _validate_modern_format(self, text: str) -> bool:
        parts = text.split("/")
        if len(parts) != 3:
            return False
        year_part, sequence_part, type_part = parts
        if not (
            year_part.isdigit()
            and sequence_part.isdigit()
            and type_part.isdigit()
        ):
            return False
        if len(year_part) != 4 or len(sequence_part) != 6 or len(type_part) != 2:
            return False
        year = int(year_part)
        return 1800 <= year <= date.today().year

    def _validate_legacy_format(self, text: str) -> bool:
        slash_index = text.index("/")
        prefix = text[:slash_index]
        sequence = text[slash_index + 1 :]
        if not sequence.isdigit() or len(sequence) != 6:
            return False
        for legacy_prefix in sorted(self.LEGACY_PREFIXES, key=len, reverse=True):
            if prefix.startswith(legacy_prefix):
                year_part = prefix[len(legacy_prefix) :]
                if len(year_part) == 4 and year_part.isdigit():
                    year = int(year_part)
                    return 1800 <= year <= date.today().year
        return False
