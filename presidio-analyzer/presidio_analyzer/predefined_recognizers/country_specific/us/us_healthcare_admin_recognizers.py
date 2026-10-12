"""Recognizers for US healthcare administrative identifiers."""

from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UsPriorAuthorizationNumberRecognizer(PatternRecognizer):
    """Recognize US healthcare prior authorization numbers with context.

    CMS identifies prior authorization and referral numbers as payer-assigned
    values. There is no universal US syntax. The primary pattern anchors a
    numeric identifier on its label, while a weak prefixed pattern supports
    structured data containing values such as ``PA-987654321``.

    Reference: https://www.cms.gov/outreach-and-education/mln/wbt/mln4462429-mln-wbt-1500/1500/lesson04/18/index.html
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Prior authorization number (labelled)",
            r"(?<=\b(?:prior\s+authorization|prior\s+auth|preauthorization|"
            r"pre-auth|authorization)(?:\s*(?:#|no\.?|number|id)\s*:?\s*|"
            r"\s*:\s*|\s+))"
            r"(?:PA-?)?\d{6,12}\b",
            0.35,
        ),
        Pattern(
            "Prior authorization number (weak prefixed)",
            r"\bPA-?\d{6,12}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "authorization",
        "auth",
        "preauthorization",
        "approval",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRIOR_AUTHORIZATION_NUMBER",
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


class UsClaimNumberRecognizer(PatternRecognizer):
    """Recognize US healthcare claim numbers with billing/claims context.

    CMS describes a claim number as the reference number shown on an
    explanation of benefits, but does not prescribe a universal syntax. The
    primary pattern anchors a numeric identifier on its claim label, while a
    weak prefixed pattern supports structured data containing ``CLM`` values.

    Reference: https://www.cms.gov/medical-bill-rights/help/guides/explanation-of-benefits
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Claim number (labelled)",
            r"(?<=\b(?:claim|medical\s+claim|healthcare\s+claim)"
            r"(?:\s*(?:#|no\.?|number|id)\s*:?\s*|\s*:\s*|\s+))"
            r"(?:CLM-?)?\d{6,15}\b",
            0.35,
        ),
        Pattern(
            "Claim number (weak prefixed)",
            r"\bCLM-?\d{6,15}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "claim",
        "billing",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_CLAIM_NUMBER",
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


class UsPrescriptionNumberRecognizer(PatternRecognizer):
    """Recognize US prescription numbers with pharmacy context.

    CMS defines the prescription/service reference number as a pharmacy-assigned
    alphanumeric value. Because there is no universal syntax, the primary
    pattern anchors a numeric identifier on an ``Rx`` or ``prescription`` label.
    A weak prefixed pattern remains available for structured data.

    Reference: https://www.cms.gov/files/document/cms-medicare-part-d-340b-repository-companion-guide-v-1.pdf
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Prescription number (Rx labelled)",
            r"(?<=\brx(?:\s*(?:#|no\.?|number|id)\s*:?\s*|\s*:\s*|\s+))"
            r"(?:RX-?)?\d{6,12}\b",
            0.6,
        ),
        Pattern(
            "Prescription number (labelled)",
            r"(?<=\bprescription"
            r"(?:\s*(?:#|no\.?|number|id)\s*:?\s*|\s*:\s*|\s+))"
            r"(?:RX-?)?\d{6,12}\b",
            0.35,
        ),
        Pattern(
            "Prescription number (weak prefixed)",
            r"\bRX-?\d{6,12}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "prescription",
        "pharmacy",
        "medication",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PRESCRIPTION_NUMBER",
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


class UsReferralNumberRecognizer(PatternRecognizer):
    """Recognize US healthcare referral numbers with referral context.

    CMS documents referral numbers as payer-assigned values reported in the same
    CMS-1500 field as prior authorization numbers. There is no universal syntax.
    The primary pattern anchors a numeric identifier on its referral label, and
    a weak prefixed pattern supports structured ``REF`` or ``INF`` values.

    Reference: https://www.cms.gov/outreach-and-education/mln/wbt/mln4462429-mln-wbt-1500/1500/lesson04/18/index.html
    """

    COUNTRY_CODE = "us"

    PATTERNS = [
        Pattern(
            "Referral number (labelled)",
            r"(?<=\b(?:referral|infusion\s+referral)"
            r"(?:\s*(?:#|no\.?|number|id)\s*:?\s*|\s*:\s*|\s+))"
            r"(?:(?:REF|INF)-?)?\d{6,12}\b",
            0.35,
        ),
        Pattern(
            "Referral number (weak prefixed)",
            r"\b(?:REF|INF)-?\d{6,12}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "referral",
        "infusion",
        "specialty",
        "referring",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_REFERRAL_NUMBER",
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


class UsProviderTaxIdRecognizer(PatternRecognizer):
    """Recognize US provider TIN/EIN values with healthcare provider context.

    CMS uses a provider's EIN or SSN as the billing provider tax ID. This
    recognizer intentionally matches only the IRS-defined EIN format and valid
    two-digit EIN prefixes to avoid treating SSNs as provider organization IDs.

    CMS reference: https://www.cms.gov/outreach-and-education/mln/wbt/mln4462429-mln-wbt-1500/1500/lesson04/12/index.html
    IRS prefix reference: https://www.irs.gov/businesses/small-businesses-self-employed/valid-eins
    """

    COUNTRY_CODE = "us"

    # The IRS prefix list excludes 00, 07-09, 17-19, 28-29, 49, 69-70,
    # 78-79, 89, and 96-97.
    VALID_EIN_PREFIX = (
        r"(?:0[1-6]|1[0-6]|2[0-7]|3[0-9]|4[0-8]|5[0-9]|6[0-8]|"
        r"7[1-7]|8[0-8]|9[0-5]|9[89])"
    )

    PATTERNS = [
        Pattern(
            "Provider tax ID (labelled)",
            r"(?<=\b(?:(?:(?:billing|rendering|healthcare)\s+provider|"
            r"provider\s+organization|provider)\s+(?:tax\s*(?:id|number|"
            r"identification\s+number)|tin|ein)|billing\s+provider)"
            r"(?:\s*(?:#|no\.?|number|id)\s*:?\s*|\s*:\s*|\s+))"
            + VALID_EIN_PREFIX
            + r"-\d{7}\b",
            0.35,
        ),
        Pattern(
            "Provider tax ID (weak valid EIN)",
            r"\b" + VALID_EIN_PREFIX + r"-\d{7}\b",
            0.1,
        ),
    ]

    CONTEXT = [
        "tax",
        "tin",
        "ein",
        "billing",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "US_PROVIDER_TAX_ID",
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
