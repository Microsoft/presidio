from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class InUpiRecognizer(PatternRecognizer):
    """
    Recognizes Indian UPI (Unified Payments Interface) IDs.

    UPI IDs are used for digital payments in India and follow the format:
    username@bankhandle (e.g., shaurya@okicici, 9876543210@paytm)

    Common UPI handles include: okicici, okhdfcbank, okaxis, paytm,
    ybl, upi, apl, ibl, axl, timecosmos, waicici, wahdfcbank

    This recognizer identifies UPI IDs using regex and context words.
    Reference: https://www.npci.org.in/what-we-do/upi/product-overview

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "in"

    PATTERNS = [
        Pattern(
            "UPI ID (High)",
            r"\b([a-zA-Z0-9.\-_]{2,256}@(okicici|okhdfcbank|okaxis|oksbi|paytm|ybl|upi|apl|ibl|axl|waicici|wahdfcbank|timecosmos|rapl|mbk|ikwik|freecharge))(?![\w.-])",
            0.7,
        ),
        Pattern(
            "UPI ID (Medium)",
            r"\b([a-zA-Z0-9.\-_]{2,256}@[a-zA-Z]{2,64})(?![\w.-])",
            0.2,
        ),
    ]

    CONTEXT = [
        "upi",
        "upi id",
        "payment",
        "gpay",
        "phonepe",
        "paytm",
        "bhim",
        "transfer",
        "pay",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IN_UPI",
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )
