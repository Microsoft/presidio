from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class ZaVatNumberRecognizer(PatternRecognizer):
    """
    Recognize South African VAT registration numbers.

    South African VAT numbers are 10 digits and always start with ``4``.

    Reference:
    https://meta.cdq.com/DataModel:CDQ/Business_Partner/Identifier/ZA_VAT

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    VAT_LENGTH = 10
    VAT_PREFIX = "4"

    PATTERNS = [
        Pattern(
            "South African VAT Number",
            r"\b4\d{9}\b",
            0.3,
        ),
    ]

    CONTEXT = [
        "vat",
        "vat number",
        "vat registration",
        "tax invoice",
        "sars",
        "value added tax",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_VAT_NUMBER",
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
        return (
            len(pattern_text) == self.VAT_LENGTH
            and pattern_text.isdigit()
            and pattern_text.startswith(self.VAT_PREFIX)
        )
