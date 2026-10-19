from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class KrBankAccountRecognizer(PatternRecognizer):
    """
    Recognize Korean bank account numbers.

    Korean bank account numbers are 10-14 digit identifiers issued in
    bank-specific segment layouts, commonly written with hyphens
    (e.g. NongHyup's 302-XXXX-XXXX-XX personal accounts, KB Kookmin and
    Korea Post's XXXXXX-XX-XXXXXX, or common three-segment forms such as
    110-234-567890). No unified national format or check digit exists, so
    precision comes from structural patterns plus negative lookaheads that
    exclude look-alike shapes: Korean phone numbers (mobile 010/011/016-019,
    Seoul 02 and regional area codes, 070 VoIP, 050X safe numbers, 080
    toll-free), resident and business registration numbers (the latter
    written XXX-XX-XXXXX) and calendar dates. A match must span the whole
    hyphenated number, so a segment run inside a longer number (e.g. a card
    number) is not reported.

    Reference: per-bank layouts (e.g. NongHyup's 3YY-XXXX-XXXX-CC
    personal accounts) are documented at
    https://namu.wiki/w/%EA%B3%84%EC%A2%8C%EB%B2%88%ED%98%B8
    Patterns were validated in a production Korean PII-masking deployment.

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "kr"

    PATTERNS = [
        Pattern(
            "NH 4-segment account (Medium)",
            r"(?<!\d)(?<!\d-)302-\d{3,4}-\d{3,4}-\d{2}(?!-?\d)",
            0.6,
        ),
        Pattern(
            "Hyphenated 3-segment account (Weak)",
            r"(?<!\d)(?<!\d-)"
            r"(?!0(?:1[016789]|2|[3-6][1-5]|70|50\d|80)-\d{3,4}-\d{4}(?!\d))"
            r"(?!\d{3}-\d{2}-\d{5}(?!\d))"
            r"(?!\d{4}[-./]\d{1,2}[-./]\d{1,2}(?!\d))(?=(?:\d-?){9,16}(?!\d))"
            r"\d{2,3}-\d{2,6}-\d{1,7}(?!-?\d)",
            0.3,
        ),
        Pattern(
            "KB Kookmin / Korea Post 6-2-6 account (Weak)",
            r"(?<!\d)(?<!\d-)\d{6}-\d{2}-\d{6}(?!-?\d)",
            0.3,
        ),
        Pattern(
            "Mixed-separator account (Very weak)",
            r"(?<!\d)(?<!\d-)(?!\d{6}-?\d{7}(?!\d))"
            r"(?!0(?:1[016789]|2|[3-6][1-5]|70|50\d|80)[- ]?\d{3,4}[- ]?\d{4}(?!\d))"
            r"(?!\d{3}-\d{2}-\d{5}(?!\d))"
            r"(?!\d{4}[-./]\d{1,2}[-./]\d{1,2}(?!\d))(?=(?:\d[- ]?){9,16}(?!\d))"
            r"\d{2,4}(?:[- ]?\d{2,6})(?:[- ]?\d{1,7})(?:[- ]?\d{1,3})?(?!-?\d)",
            0.15,
        ),
    ]

    CONTEXT = [
        "계좌",
        "계좌번호",
        "예금주",
        "송금",
        "입금",
        "입금계좌",
        "출금",
        "이체",
        "타행",
        "은행",
        "bank account",
        "account number",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "ko",
        supported_entity: str = "KR_BANK_ACCOUNT",
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
