import pytest
from presidio_analyzer import AnalyzerEngine, PatternRecognizer, RecognizerRegistry
from presidio_analyzer.predefined_recognizers import (
    UsClaimNumberRecognizer,
    UsPrescriptionNumberRecognizer,
    UsPriorAuthorizationNumberRecognizer,
    UsProviderTaxIdRecognizer,
    UsReferralNumberRecognizer,
)

from tests import assert_result


@pytest.fixture(scope="module")
def analyze_with_recognizer(spacy_nlp_engine):
    """Return an administrative ID analyzer using production spaCy tokenization."""

    def analyze(text, entity, recognizer, score_threshold=0.6):
        registry = RecognizerRegistry()
        registry.add_recognizer(recognizer)
        analyzer = AnalyzerEngine(registry=registry, nlp_engine=spacy_nlp_engine)
        return analyzer.analyze(
            text=text,
            language="en",
            entities=[entity],
            score_threshold=score_threshold,
        )

    return analyze


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_positions",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-987654321 approved for treatment.",
            ((20, 32),),
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Processed healthcare claim CLM456789123 was paid.",
            ((27, 39),),
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription number RX789456123 was filled by the pharmacy.",
            ((20, 31),),
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Infusion referral number INF2025001234 is ready for scheduling.",
            ((25, 38),),
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Provider Tax ID 12-3456789 belongs to the billing provider.",
            ((16, 26),),
        ),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_has_context_then_detected(
    recognizer, entity, text, expected_positions, analyze_with_recognizer
):
    """Test context enhancement raises matches above the caller threshold."""
    results = analyze_with_recognizer(text, entity, recognizer)
    results = sorted(results, key=lambda result: result.start)
    assert len(results) == len(expected_positions)
    for result, (start, end) in zip(results, expected_positions):
        assert_result(result, entity, start, end, 0.7)


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_value",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "pRiOr AuThOrIzAtIoN pa-123456",
            "pa-123456",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "cLaIm clm123456",
            "clm123456",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "pReScRiPtIoN rX123456",
            "rX123456",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "rEfErRaL inf123456",
            "inf123456",
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "bIlLiNg PrOvIdEr eIn: 12-3456789",
            "12-3456789",
        ),
        # fmt: on
    ],
)
def test_admin_id_matching_is_case_insensitive(
    recognizer, entity, text, expected_value, analyze_with_recognizer
):
    """Test mixed-case labels and prefixes are detected."""
    results = analyze_with_recognizer(text, entity, recognizer)
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(results[0], entity, start, start + len(expected_value), 0.7)


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_values",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-123456; prior authorization PA-654321.",
            ["PA-123456", "PA-654321"],
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim CLM123456 and claim CLM654321.",
            ["CLM123456", "CLM654321"],
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription RX123456 and prescription RX654321.",
            ["RX123456", "RX654321"],
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Referral REF123456 and referral INF654321.",
            ["REF123456", "INF654321"],
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Provider EIN 12-3456789 and provider TIN 20-1234567.",
            ["12-3456789", "20-1234567"],
        ),
        # fmt: on
    ],
)
def test_when_text_has_multiple_admin_ids_then_all_are_detected(
    recognizer, entity, text, expected_values, analyze_with_recognizer
):
    """Test every contextual administrative ID in one input is returned."""
    results = sorted(
        analyze_with_recognizer(text, entity, recognizer),
        key=lambda result: result.start,
    )
    assert [text[result.start : result.end] for result in results] == expected_values


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_value",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-123456.",
            "PA-123456",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim CLM123456,",
            "CLM123456",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription RX123456;",
            "RX123456",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Referral REF123456.",
            "REF123456",
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Provider EIN 12-3456789.",
            "12-3456789",
        ),
        # fmt: on
    ],
)
def test_admin_id_matching_ignores_trailing_punctuation(
    recognizer, entity, text, expected_value, analyze_with_recognizer
):
    """Test trailing sentence punctuation stays outside the result span."""
    results = analyze_with_recognizer(text, entity, recognizer)
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(results[0], entity, start, start + len(expected_value), 0.7)


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_value",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-123456",
            "PA-123456",
        ),
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization PA-123456789012",
            "PA-123456789012",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim CLM123456",
            "CLM123456",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim CLM123456789012345",
            "CLM123456789012345",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription RX123456",
            "RX123456",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription RX123456789012",
            "RX123456789012",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Referral REF123456",
            "REF123456",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Referral INF123456789012",
            "INF123456789012",
        ),
        # fmt: on
    ],
)
def test_admin_id_minimum_and_maximum_lengths_are_detected(
    recognizer, entity, text, expected_value, analyze_with_recognizer
):
    """Test each variable-length administrative ID at its exact boundaries."""
    results = analyze_with_recognizer(text, entity, recognizer)
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(results[0], entity, start, start + len(expected_value), 0.7)


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-12345",
        ),
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-1234567890123",
        ),
        (UsClaimNumberRecognizer(), "US_CLAIM_NUMBER", "CLM12345"),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "CLM1234567890123456",
        ),
        (UsPrescriptionNumberRecognizer(), "US_PRESCRIPTION_NUMBER", "RX12345"),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "RX1234567890123",
        ),
        (UsReferralNumberRecognizer(), "US_REFERRAL_NUMBER", "REF12345"),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "INF1234567890123",
        ),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-123456"),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-12345678"),
        # fmt: on
    ],
)
def test_too_short_and_too_long_admin_ids_do_not_match(
    recognizer, entity, text, analyze_with_recognizer
):
    """Test values one digit outside each supported length do not match."""
    assert analyze_with_recognizer(text, entity, recognizer, score_threshold=0) == []


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_value, expected_score",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Prior authorization number: 987654321 approved.",
            "987654321",
            0.7,
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim number: 1234567890123 was paid.",
            "1234567890123",
            0.7,
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Claim ID 123456789012345 was paid.",
            "123456789012345",
            0.7,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Rx #1234567",
            "1234567",
            0.6,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Prescription number: 7654321",
            "7654321",
            0.7,
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "prescription 4455667",
            "4455667",
            0.7,
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Infusion referral number: 2025001234",
            "2025001234",
            0.7,
        ),
        # fmt: on
    ],
)
def test_when_admin_id_follows_label_then_identifier_only_is_detected(
    recognizer,
    entity,
    text,
    expected_value,
    expected_score,
    analyze_with_recognizer,
):
    """Test labels enable bare numeric IDs without entering the result span."""
    results = analyze_with_recognizer(text, entity, recognizer)
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(
        results[0], entity, start, start + len(expected_value), expected_score
    )


@pytest.mark.parametrize(
    "text, expected_value",
    [
        ("Billing provider EIN: 12-3456789", "12-3456789"),
        ("Rendering provider TIN 20-1234567", "20-1234567"),
        ("Healthcare provider tax number: 67-1234567", "67-1234567"),
        ("Billing provider: 99-1234567", "99-1234567"),
        ("Provider TIN# 12-3456789", "12-3456789"),
        ("Billing provider EIN No. 20-1234567", "20-1234567"),
    ],
)
def test_when_provider_ein_has_provider_tax_label_then_detected(
    text, expected_value, analyze_with_recognizer
):
    """Test valid EINs immediately following provider tax labels are detected."""
    results = analyze_with_recognizer(
        text,
        "US_PROVIDER_TAX_ID",
        UsProviderTaxIdRecognizer(),
    )
    start = text.index(expected_value)
    assert len(results) == 1
    assert_result(
        results[0],
        "US_PROVIDER_TAX_ID",
        start,
        start + len(expected_value),
        0.7,
    )


def test_when_number_has_different_workflow_label_then_prescription_not_detected(
    analyze_with_recognizer,
):
    """Test a claim label does not support a prescription number match."""
    recognizer = UsPrescriptionNumberRecognizer()
    assert (
        analyze_with_recognizer(
            "The claim 1234567 was paid",
            "US_PRESCRIPTION_NUMBER",
            recognizer,
        )
        == []
    )


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-987654321",
        ),
        (UsClaimNumberRecognizer(), "US_CLAIM_NUMBER", "CLM456789123"),
        (UsPrescriptionNumberRecognizer(), "US_PRESCRIPTION_NUMBER", "RX789456123"),
        (UsReferralNumberRecognizer(), "US_REFERRAL_NUMBER", "INF2025001234"),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-3456789"),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_lacks_context_then_below_threshold(
    recognizer, entity, text, analyze_with_recognizer
):
    """Test normal analyzer calls suppress pattern-only matches."""
    assert analyze_with_recognizer(text, entity, recognizer) == []


@pytest.mark.parametrize(
    "recognizer, entity, text",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "Order number PA-987654321 is ready.",
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            "Tracking number CLM456789123 is active.",
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "Case number RX789456123 is pending.",
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            "Claim number INF2025001234 was denied.",
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            "Invoice number 12-3456789 was posted.",
        ),
        # fmt: on
    ],
)
def test_when_us_healthcare_admin_id_has_unrelated_context_then_not_detected(
    recognizer, entity, text, analyze_with_recognizer
):
    """Test similar-looking workflow IDs stay below the threshold."""
    assert analyze_with_recognizer(text, entity, recognizer) == []


@pytest.mark.parametrize(
    "text",
    [
        "Provider phone extension 12-3456789",
        "provider 00-0000000 listed",
        "Employee tax ID 12-3456789",
    ],
)
def test_when_ein_lacks_provider_tax_label_then_not_detected(
    text, analyze_with_recognizer
):
    """Test generic provider or tax wording cannot promote an EIN-shaped value."""
    assert (
        analyze_with_recognizer(
            text,
            "US_PROVIDER_TAX_ID",
            UsProviderTaxIdRecognizer(),
        )
        == []
    )


@pytest.mark.parametrize(
    "invalid_prefix",
    [
        "00",
        "07",
        "08",
        "09",
        "17",
        "18",
        "19",
        "28",
        "29",
        "49",
        "69",
        "70",
        "78",
        "79",
        "89",
        "96",
        "97",
    ],
)
def test_when_provider_ein_prefix_is_not_irs_valid_then_not_detected(
    invalid_prefix, analyze_with_recognizer
):
    """Test values outside the IRS-assigned EIN prefix set do not match."""
    text = f"Provider Tax ID {invalid_prefix}-1234567"
    assert (
        analyze_with_recognizer(
            text,
            "US_PROVIDER_TAX_ID",
            UsProviderTaxIdRecognizer(),
            score_threshold=0,
        )
        == []
    )


@pytest.mark.parametrize(
    "recognizer, entity, text, expected_score",
    [
        # fmt: off
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            "PA-987654321",
            0.1,
        ),
        (UsClaimNumberRecognizer(), "US_CLAIM_NUMBER", "CLM456789123", 0.1),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            "RX789456123",
            0.1,
        ),
        (UsReferralNumberRecognizer(), "US_REFERRAL_NUMBER", "INF2025001234", 0.1),
        (UsProviderTaxIdRecognizer(), "US_PROVIDER_TAX_ID", "12-3456789", 0.1),
        # fmt: on
    ],
)
def test_explicit_request_threshold_can_return_pattern_only_matches(
    recognizer, entity, text, expected_score, analyze_with_recognizer
):
    """Test callers can opt into raw pattern matches for structured analysis."""
    results = analyze_with_recognizer(text, entity, recognizer, score_threshold=0)
    assert len(results) == 1
    assert_result(results[0], entity, 0, len(text), expected_score)


@pytest.mark.parametrize(
    "recognizer, entity, expected_context",
    [
        (
            UsPriorAuthorizationNumberRecognizer(),
            "US_PRIOR_AUTHORIZATION_NUMBER",
            ["authorization", "auth", "preauthorization", "approval"],
        ),
        (
            UsClaimNumberRecognizer(),
            "US_CLAIM_NUMBER",
            ["claim", "billing"],
        ),
        (
            UsPrescriptionNumberRecognizer(),
            "US_PRESCRIPTION_NUMBER",
            ["prescription", "pharmacy", "medication"],
        ),
        (
            UsReferralNumberRecognizer(),
            "US_REFERRAL_NUMBER",
            ["referral", "infusion", "specialty", "referring"],
        ),
        (
            UsProviderTaxIdRecognizer(),
            "US_PROVIDER_TAX_ID",
            ["tax", "tin", "ein", "billing"],
        ),
    ],
)
def test_us_healthcare_admin_recognizer_metadata(recognizer, entity, expected_context):
    """Test entity metadata and context without a recognizer threshold."""
    assert isinstance(recognizer, PatternRecognizer)
    assert PatternRecognizer in type(recognizer).__bases__
    assert recognizer.COUNTRY_CODE == "us"
    assert recognizer.supported_entities == [entity]
    assert recognizer.supported_language == "en"
    assert recognizer.context == expected_context
    assert recognizer.score_thresholds == {}
