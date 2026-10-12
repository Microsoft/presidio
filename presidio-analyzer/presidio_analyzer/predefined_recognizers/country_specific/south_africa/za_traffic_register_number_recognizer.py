from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer

from .za_id_number_recognizer import ZaIdNumberRecognizer


class ZaTrafficRegisterNumberRecognizer(PatternRecognizer):
    """
    Recognize South African eNaTIS traffic register numbers (TRN).

    Traffic register numbers are 13-digit identifiers assigned to
    foreigners and organisations on the eNaTIS system. They share length
    with South African ID numbers but use a different validation scheme.

    Reference:
    https://www.gov.za/services/driving-licence-driving/apply-traffic-register-number

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words to increase confidence in detection
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "za"

    TRN_LENGTH = 13

    PATTERNS = [
        Pattern(
            "South African Traffic Register Number",
            r"\b\d{13}\b",
            0.05,
        ),
    ]

    CONTEXT = [
        "traffic register",
        "traffic register number",
        "trn",
        "enatis",
        "natis",
        "vehicle register",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "ZA_TRAFFIC_REGISTER_NUMBER",
        name: Optional[str] = None,
    ):
        patterns = self.PATTERNS if patterns is None else patterns
        context = self.CONTEXT if context is None else context
        self._id_validator = ZaIdNumberRecognizer()
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def validate_result(self, pattern_text: str) -> bool:  # noqa: D102
        if len(pattern_text) != self.TRN_LENGTH or not pattern_text.isdigit():
            return False
        return not self._id_validator.validate_result(pattern_text)
