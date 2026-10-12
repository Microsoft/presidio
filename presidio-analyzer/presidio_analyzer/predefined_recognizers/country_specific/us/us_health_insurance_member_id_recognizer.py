"""Recognizer for US health insurance member identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsHealthInsuranceMemberIdRecognizer(PatternRecognizer):
    """Recognize US health insurance member/subscriber IDs with context.

    US health insurance member identifiers are payer-specific and do not have a
    single universal checksum or format. To avoid broad matching of generic
    alphanumeric IDs, this recognizer requires both:
    - a plausible alphanumeric member ID pattern, and
    - nearby healthcare/insurance context.

    CMS consumer guidance explicitly labels the payer-assigned member number on
    a sample insurance card. Medicaid T-MSIS defines MEMBER-ID as the value shown
    on the insurance carrier's card and permits up to 20 characters. These
    sources establish the identifier and upper bound, not a universal syntax;
    the default regex is therefore a conservative, replaceable heuristic.
    Presidio applies ``re.IGNORECASE`` through its default global regex flags,
    so the uppercase character classes also match lowercase and mixed-case IDs.

    CMS card reference: https://www.cms.gov/files/document/11818-sample-insurance-card-english.pdf
    Medicaid data reference: https://www.medicaid.gov/tmsis/dataguide/v4/data-elements/tpl003036/

    :param patterns: List of patterns to be used by this recognizer
    :param context: List of context words which increase detection confidence
    :param supported_language: Language this recognizer supports
    :param supported_entity: The entity this recognizer can detect
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Health insurance member ID (weak)",
            r"\b(?=[A-Z0-9-]{6,20}\b)(?=[A-Z0-9-]*[A-Z])"
            r"(?=[A-Z0-9-]*\d)[A-Z]{1,5}-?[A-Z0-9]{5,14}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "member",
        "subscriber",
        "insurance",
        "policy",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_HEALTH_INSURANCE_MEMBER_ID",
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
