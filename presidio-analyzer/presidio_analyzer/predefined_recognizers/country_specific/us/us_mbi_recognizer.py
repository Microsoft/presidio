"""Recognizer for US Medicare Beneficiary Identifier (MBI)."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsMbiRecognizer(PatternRecognizer):
    """Recognize US Medicare Beneficiary Identifier (MBI) using regex.

    The MBI is an 11-character identifier used by Medicare. The format follows
    specific rules defined by CMS (Centers for Medicare & Medicaid Services):
    https://www.cms.gov/medicare/new-medicare-card/understanding-new-medicare-beneficiary-identifier-mbi

    Format: C A AN N A AN N A A N N
    Where:
    - C = numeric character (0-9)
    - A = alphabetic character (excluding S, L, O, I, B, Z)
    - AN = alphanumeric character (numeric or alphabetic, excluding S, L, O, I, B, Z)

    Position rules:
    - Positions 1, 4, 7, 10, 11: numeric (0-9)
    - Positions 2, 5, 8, 9: alphabetic
    - Positions 3, 6: alphanumeric

    Example: 1EG4-TE5-MK73 (dashes are for display only)

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "us"

    # Valid letters: A-Z excluding S, L, O, I, B, Z
    # Valid letters are: A, C, D, E, F, G, H, J, K, M, N, P, Q, R, T, U, V, W, X, Y
    VALID_LETTERS = "ACDEFGHJKMNPQRTUVWXY"
    VALID_ALPHANUMERIC = "0-9ACDEFGHJKMNPQRTUVWXY"

    # Regex building blocks
    _NUM = "[0-9]"
    _ALPHA = f"[{VALID_LETTERS}]"
    _ALPHANUM = f"[{VALID_ALPHANUMERIC}]"

    # Full MBI pattern:
    # Pos: 1   2      3        4   5      6        7   8      9      10  11
    #      NUM ALPHA  ALPHANUM NUM ALPHA  ALPHANUM NUM ALPHA  ALPHA  NUM NUM

    # Pattern without dashes (11 consecutive characters)
    _MBI_NO_DASH = (
        f"{_NUM}{_ALPHA}{_ALPHANUM}{_NUM}"
        f"{_ALPHA}{_ALPHANUM}{_NUM}"
        f"{_ALPHA}{_ALPHA}{_NUM}{_NUM}"
    )

    # Pattern with dashes in XXXX-XXX-XXXX format
    _MBI_WITH_DASH = (
        f"{_NUM}{_ALPHA}{_ALPHANUM}{_NUM}-"
        f"{_ALPHA}{_ALPHANUM}{_NUM}-"
        f"{_ALPHA}{_ALPHA}{_NUM}{_NUM}"
    )

    PATTERNS = [
        Pattern(
            "MBI (weak)",
            rf"\b{_MBI_NO_DASH}\b",
            0.3,
        ),
        Pattern(
            "MBI (medium)",
            rf"\b{_MBI_WITH_DASH}\b",
            0.5,
        ),
    ]

    CONTEXT = [
        "medicare",
        "mbi",
        "beneficiary",
        "cms",
        "medicaid",
        "hic",  # Health Insurance Claim number (predecessor)
        "hicn",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_MBI",
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
