"""Tests for YAML recognizer configuration models."""
# ruff: noqa: D103,E501,F841,I001

import pytest
from presidio_analyzer.input_validation.yaml_recognizer_models import (
    BaseRecognizerConfig,
    CustomRecognizerConfig,
    LangExtractRecognizerConfig,
    LanguageContextConfig,
    PredefinedRecognizerConfig,
    RecognizerRegistryConfig,
)
from pydantic import ValidationError


def test_language_context_config_valid():
    """Test LanguageContextConfig validates correctly."""
    lang_config = LanguageContextConfig(
        language="en",
        context=["credit", "card"]
    )
    assert lang_config.language == "en"
    assert lang_config.context == ["credit", "card"]


def test_language_context_config_valid_with_region():
    """Test LanguageContextConfig with region code."""
    lang_config = LanguageContextConfig(
        language="en-US",
        context=["social", "security"]
    )
    assert lang_config.language == "en-US"
    assert lang_config.context == ["social", "security"]


def test_language_context_config_no_context():
    """Test LanguageContextConfig without context."""
    lang_config = LanguageContextConfig(language="es")
    assert lang_config.language == "es"
    assert lang_config.context is None


def test_language_context_config_invalid_language():
    """Test LanguageContextConfig rejects invalid language codes."""
    with pytest.raises(ValidationError) as exc_info:
        LanguageContextConfig(language="invalid")
    assert "Invalid language code format" in str(exc_info.value)


def test_language_context_config_invalid_format():
    """Test various invalid language formats."""
    invalid_languages = ["e", "eng", "EN", "en-us", "en-USA", "123", ""]

    for lang in invalid_languages:
        with pytest.raises(ValidationError):
            LanguageContextConfig(language=lang)


def test_base_recognizer_config_minimal():
    """Test minimal valid configuration."""
    config = BaseRecognizerConfig(name="test_recognizer")
    assert config.name == "test_recognizer"
    assert config.enabled is True
    assert config.type == "predefined"


def test_base_recognizer_config_full():
    """Test full configuration with all fields."""
    config = BaseRecognizerConfig(
        name="test_recognizer",
        enabled=False,
        type="custom",
        supported_language="en",
        context=["test", "context"],
        supported_entity="TEST_ENTITY"
    )
    assert config.name == "test_recognizer"
    assert config.enabled is False
    assert config.type == "custom"
    assert config.supported_language == "en"  # Preserved as-is
    assert config.supported_languages is None
    assert config.context == ["test", "context"]
    assert config.supported_entity == "TEST_ENTITY"  # Preserved as-is
    assert config.supported_entities is None


def test_language_fields_preserved():
    """Test that supported_language is preserved as-is (not normalized)."""
    config = BaseRecognizerConfig(
        name="test",
        supported_language="en"
    )
    assert config.supported_language == "en"
    assert config.supported_languages is None


def test_entity_fields_preserved():
    """Test that supported_entity is preserved as-is (not normalized)."""
    config = BaseRecognizerConfig(
        name="test",
        supported_entity="PERSON"
    )
    assert config.supported_entity == "PERSON"
    assert config.supported_entities is None


def test_cannot_specify_both_language_formats():
    """Test that specifying both language formats raises error."""
    with pytest.raises(ValidationError) as exc_info:
        BaseRecognizerConfig(
            name="test",
            supported_language="en",
            supported_languages=["es", "fr"]
        )
    assert "Cannot specify both 'supported_language' and 'supported_languages'" in str(exc_info.value)


def test_cannot_specify_both_entity_formats():
    """Test that specifying both entity formats raises error."""
    with pytest.raises(ValidationError) as exc_info:
        BaseRecognizerConfig(
            name="test",
            supported_entity="PERSON",
            supported_entities=["LOCATION", "ORG"]
        )
    assert "has both 'supported_entity' and 'supported_entities' specified" in str(exc_info.value)


def test_invalid_single_language_format():
    """Test validation of single language format."""
    with pytest.raises(ValidationError):
        BaseRecognizerConfig(
            name="test",
            supported_language="invalid"
        )


def test_context_with_multiple_languages_error():
    """Test that global context with multiple languages raises error."""
    with pytest.raises(ValidationError) as exc_info:
        BaseRecognizerConfig(
            name="test",
            supported_languages=["en", "es"],
            context=["global", "context"]
        )
    assert "Global context can only be used with a single language" in str(exc_info.value)


def test_context_with_single_language_valid():
    """Test that global context with single language is valid."""
    config = BaseRecognizerConfig(
        name="test",
        supported_languages=["en"],
        context=["global", "context"]
    )
    assert config.context == ["global", "context"]


def test_predefined_recognizer_config_defaults():
    """Test predefined recognizer with defaults."""
    config = PredefinedRecognizerConfig(name="CreditCardRecognizer")
    assert config.name == "CreditCardRecognizer"
    assert config.type == "predefined"
    assert config.enabled is True


def test_predefined_recognizer_config_with_language():
    """Test predefined recognizer with language specification."""
    config = PredefinedRecognizerConfig(
        name="CreditCardRecognizer",
        supported_language="en"
    )
    assert config.supported_language == "en"
    assert config.supported_languages is None


def test_custom_recognizer_config_with_patterns():
    """Test custom recognizer with patterns."""
    patterns = [
        {
            "name": "test_pattern",
            "regex": r"\b\d{4}-\d{4}-\d{4}-\d{4}\b",
            "score": 0.8
        }
    ]
    config = CustomRecognizerConfig(
        name="custom_test",
        supported_entity="CUSTOM_ENTITY",
        patterns=patterns
    )
    assert config.name == "custom_test"
    assert config.type == "custom"
    assert config.supported_entity == "CUSTOM_ENTITY"
    assert config.supported_entities is None
    assert config.patterns == patterns


def test_custom_recognizer_config_with_country_code():
    """Custom YAML model preserves normalized country_code for filtering."""
    config = CustomRecognizerConfig(
        name="custom_am",
        supported_entity="AM_NATIONAL_ID",
        country_code=" AM ",
        patterns=[{"name": "am_id", "regex": r"\d{10}", "score": 0.7}],
    )

    assert config.country_code == "am"
    assert config.model_dump()["country_code"] == "am"


def test_custom_recognizer_config_rejects_blank_country_code():
    """Blank YAML country_code values fail validation instead of being ignored."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="custom_blank_country",
            supported_entity="CUSTOM_ENTITY",
            country_code="   ",
            patterns=[{"name": "id", "regex": r"\d+", "score": 0.5}],
        )

    assert "country_code" in str(exc_info.value)
    assert "non-empty" in str(exc_info.value)


def test_custom_recognizer_config_rejects_multiple_country_codes():
    """country_code is intentionally a single string, not a list."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="custom_multi_country",
            supported_entity="CUSTOM_ENTITY",
            country_code=["us", "uk"],
            patterns=[{"name": "id", "regex": r"\d+", "score": 0.5}],
        )

    assert "country_code" in str(exc_info.value)


def test_recognizer_registry_config_preserves_custom_country_code_on_dump():
    """Validated registry YAML keeps custom country_code for loader kwargs."""
    config = RecognizerRegistryConfig(
        supported_languages=["en"],
        recognizers=[
            {
                "name": "custom_am",
                "type": "custom",
                "supported_entity": "AM_NATIONAL_ID",
                "country_code": "am",
                "patterns": [{"name": "am_id", "regex": r"\d{10}", "score": 0.7}],
            }
        ],
    )

    recognizer = config.recognizers[0]
    assert isinstance(recognizer, CustomRecognizerConfig)
    assert recognizer.country_code == "am"
    assert config.model_dump()["recognizers"][0]["country_code"] == "am"


def test_configuration_validator_uses_recognizer_specific_dump_rules():
    """Validated YAML should preserve recognizer-specific model_dump behavior."""
    from presidio_analyzer.input_validation.schemas import ConfigurationValidator

    raw_config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "HuggingFaceNerRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "supported_entities": ["PERSON"],
                "model_name": "custom/ner-model",
                "aggregation_strategy": "simple",
                "device": "cpu",
            },
            {
                "name": "GLiNERRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "model_name": "custom/gliner-model",
            },
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
            },
        ],
    }

    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        raw_config
    )
    hf_recognizer = validated["recognizers"][0]
    gliner_recognizer = validated["recognizers"][1]
    predefined_recognizer = validated["recognizers"][2]

    assert validated["global_regex_flags"] == 26
    assert hf_recognizer["enabled"] is True
    assert hf_recognizer["model_name"] == "custom/ner-model"
    assert "threshold" not in hf_recognizer
    assert "chunk_size" not in hf_recognizer
    assert "chunk_overlap" not in hf_recognizer
    assert "tokenizer_name" not in hf_recognizer
    assert gliner_recognizer["enabled"] is True
    assert gliner_recognizer["model_name"] == "custom/gliner-model"
    assert "threshold" not in gliner_recognizer
    assert "flat_ner" not in gliner_recognizer
    assert "entity_mapping" not in gliner_recognizer
    assert predefined_recognizer["name"] == "CreditCardRecognizer"
    assert predefined_recognizer["supported_language"] is None


def test_langextract_config_preserves_config_path():
    """A BasicLangExtractRecognizer YAML entry must keep ``config_path``.

    Regression: without a dedicated config model (extra="allow"), the strict
    ``PredefinedRecognizerConfig`` schema drops ``config_path``, so the recognizer
    silently falls back to its bundled default model config.
    """
    config = LangExtractRecognizerConfig(
        name="SmLlama32_3b",
        class_name="BasicLangExtractRecognizer",
        supported_languages=["en"],
        config_path="/path/to/langextract_config.yml",
    )
    assert config.config_path == "/path/to/langextract_config.yml"
    assert config.model_dump()["config_path"] == "/path/to/langextract_config.yml"


def test_langextract_config_selected_via_class_name():
    """``class_name: BasicLangExtractRecognizer`` selects the LangExtract model
    and preserves ``config_path`` (plus arbitrary extra kwargs) through the full
    registry validation used by AnalyzerEngineProvider."""
    from presidio_analyzer.input_validation.schemas import ConfigurationValidator

    raw_config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "SmLlama32_3b",
                "type": "predefined",
                "class_name": "BasicLangExtractRecognizer",
                "enabled": True,
                "supported_languages": ["en"],
                "config_path": "/path/to/langextract_config.yml",
            }
        ],
    }

    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        raw_config
    )
    lm_recognizer = validated["recognizers"][0]
    assert lm_recognizer["class_name"] == "BasicLangExtractRecognizer"
    assert lm_recognizer["config_path"] == "/path/to/langextract_config.yml"


def test_langextract_config_azure_variant_selected():
    """AzureOpenAILangExtractRecognizer also maps to the LangExtract config model."""
    config = RecognizerRegistryConfig(
        supported_languages=["en"],
        recognizers=[
            {
                "name": "AzureLM",
                "type": "predefined",
                "class_name": "AzureOpenAILangExtractRecognizer",
                "config_path": "/path/to/azure_config.yml",
            }
        ],
    )
    recognizer = config.recognizers[0]
    assert isinstance(recognizer, LangExtractRecognizerConfig)
    assert recognizer.config_path == "/path/to/azure_config.yml"


def test_custom_recognizer_config_with_deny_list():
    """Test custom recognizer with deny list only."""
    config = CustomRecognizerConfig(
        name="custom_test",
        supported_entity="CUSTOM_ENTITY",
        deny_list=["exclude", "this"],
        deny_list_score=0.1
    )
    assert config.deny_list == ["exclude", "this"]
    assert config.deny_list_score == 0.1


def test_custom_recognizer_config_omitted_deny_list_score_defaults_to_one():
    """Omitted deny_list_score should match PatternRecognizer's own default (1.0).

    PatternRecognizer.from_dict() forwards model_dump() output straight to the
    constructor, so the dumped value has to already be 1.0 for an omitted
    YAML field to behave the same as constructing PatternRecognizer directly.
    """
    config = CustomRecognizerConfig(
        name="custom_test",
        supported_entity="CUSTOM_ENTITY",
        deny_list=["exclude", "this"],
    )
    assert config.deny_list_score == 1.0
    assert config.model_dump()["deny_list_score"] == 1.0


def test_custom_recognizer_config_explicit_deny_list_score_kept_in_dump():
    """An explicitly set deny_list_score is preserved through model_dump()."""
    config = CustomRecognizerConfig(
        name="custom_test",
        supported_entity="CUSTOM_ENTITY",
        deny_list=["exclude", "this"],
        deny_list_score=0.1,
    )
    assert config.model_dump()["deny_list_score"] == 0.1


def test_custom_recognizer_config_invalid_patterns_not_list():
    """Test that patterns must be a list."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            patterns="not a list"
        )


def test_custom_recognizer_config_invalid_pattern_not_dict():
    """Test that each pattern must be a dict."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            patterns=["not a dict"]
        )


def test_custom_recognizer_config_pattern_missing_fields():
    """Test that patterns must have required fields."""
    required_fields = ["name", "regex", "score"]

    for field in required_fields:
        pattern = {"name": "test", "regex": r"\d+", "score": 0.5}
        del pattern[field]

        with pytest.raises(ValidationError) as exc_info:
            CustomRecognizerConfig(
                name="test",
                supported_entity="TEST",
                patterns=[pattern]
            )


def test_custom_recognizer_config_invalid_score_type():
    """Test that pattern score must be float."""
    pattern = {
        "name": "test",
        "regex": r"\d+",
        "score": "not a float"
    }
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            patterns=[pattern]
        )


def test_custom_recognizer_config_invalid_score_range():
    """Test that pattern score must be between 0 and 1."""
    invalid_scores = [-0.1, 1.1, 2.0]

    for score in invalid_scores:
        pattern = {
            "name": "test",
            "regex": r"\d+",
            "score": score
        }
        with pytest.raises(ValidationError) as exc_info:
            CustomRecognizerConfig(
                name="test",
                supported_entity="TEST",
                patterns=[pattern]
            )


@pytest.mark.parametrize(
    "regex, capture_group",
    [
        (r"id: (\d+)", 1),
        (r"id: (?P<value>\d+)", "value"),
        (r"id: (\d+)", None),
    ],
)
def test_custom_recognizer_config_pattern_capture_group_valid(regex, capture_group):
    """A capture_group that exists in the regex is accepted and kept in the dump."""
    pattern = {
        "name": "test",
        "regex": regex,
        "score": 0.5,
        "capture_group": capture_group,
    }
    config = CustomRecognizerConfig(
        name="test",
        supported_entity="TEST",
        patterns=[pattern]
    )

    assert config.model_dump()["patterns"] == [pattern]


@pytest.mark.parametrize(
    "regex, capture_group, expected_message",
    [
        (
            r"id: (\d+)",
            2,
            "Invalid pattern 'test': capture_group 2 is out of range: "
            "regex defines 1 capture group(s)",
        ),
        (
            r"id: (?P<value>\d+)",
            "number",
            "Invalid pattern 'test': capture_group 'number' is not a named group "
            "in the regex. Named groups: ['value']",
        ),
        (
            r"id: (\d+)",
            -1,
            "Invalid pattern 'test': capture_group must be a non-negative integer, "
            "got -1",
        ),
        (
            r"id: (\d+)",
            True,
            "Invalid pattern 'test': capture_group must be an int or a str, got bool",
        ),
        (
            r"id: (\d+)",
            [1],
            "Invalid pattern 'test': capture_group must be an int or a str, got list",
        ),
    ],
)
def test_custom_recognizer_config_pattern_capture_group_invalid(
    regex, capture_group, expected_message
):
    """An invalid capture_group fails at parse time with an actionable message."""
    pattern = {
        "name": "test",
        "regex": regex,
        "score": 0.5,
        "capture_group": capture_group,
    }
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            patterns=[pattern]
        )

    assert expected_message in str(exc_info.value)


def test_custom_recognizer_config_no_patterns_or_deny_list():
    """Test that custom recognizer must have patterns or deny_list."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST"
        )


def test_custom_recognizer_config_invalid_deny_list_score():
    """Test deny_list_score validation."""
    with pytest.raises(ValidationError):
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            deny_list=["test"],
            deny_list_score=1.5  # Invalid: > 1.0
        )

    with pytest.raises(ValidationError):
        CustomRecognizerConfig(
            name="test",
            supported_entity="TEST",
            deny_list=["test"],
            deny_list_score=-0.1  # Invalid: < 0.0
        )


def test_recognizer_registry_config_defaults():
    """Test registry config with defaults (requires at least one recognizer)."""
    config = RecognizerRegistryConfig(recognizers=["CreditCardRecognizer"])
    assert config.supported_languages is None
    assert config.global_regex_flags == 26
    assert len(config.recognizers) == 1


def test_recognizer_registry_config_valid_languages():
    """Test registry with valid languages."""
    config = RecognizerRegistryConfig(
        supported_languages=["en", "es", "fr-CA"],
        recognizers=["CreditCardRecognizer"]
    )
    assert config.supported_languages == ["en", "es", "fr-CA"]


def test_recognizer_registry_config_invalid_language():
    """Test registry with invalid language codes."""
    with pytest.raises(ValidationError):
        RecognizerRegistryConfig(
            supported_languages=["en", "invalid", "es"],
            recognizers=["CreditCardRecognizer"]
        )


def test_recognizer_registry_config_empty_languages():
    """Test registry with empty languages list."""
    config = RecognizerRegistryConfig(
        supported_languages=[],
        recognizers=["CreditCardRecognizer"]
    )
    assert config.supported_languages == []


def test_recognizer_registry_config_empty_recognizers():
    """Test that empty recognizers list raises a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        RecognizerRegistryConfig(
            recognizers=[],
            global_regex_flags=26
        )
    assert "empty recognizers list" in str(exc_info.value).lower()


def test_recognizer_registry_config_missing_recognizers():
    """Test that missing recognizers field raises a validation error."""
    with pytest.raises(ValidationError) as exc_info:
        RecognizerRegistryConfig(
            supported_languages=["en"],
            global_regex_flags=26
        )
    assert "empty recognizers list" in str(exc_info.value).lower()


def test_recognizer_registry_config_string_recognizers():
    """Test registry with string recognizers."""
    config = RecognizerRegistryConfig(
        recognizers=["credit_card", "email", "phone_number"]
    )
    assert len(config.recognizers) == 3
    assert all(isinstance(r, str) for r in config.recognizers)


def test_recognizer_registry_config_mixed_recognizers():
    """Test registry with mixed recognizer types and missing languages should fail."""
    custom_config = {
        "name": "custom_test",
        "type": "custom",
        "supported_entity": "TEST",
        "patterns": [{"name": "test", "regex": r"\d+", "score": 0.5}]
    }

    with pytest.raises(ValidationError) as exc_info:
        RecognizerRegistryConfig(
            recognizers=[
                "credit_card",  # string predefined
                {"name": "UrlRecognizer", "type": "predefined"},  # predefined
                custom_config  # custom without languages should trigger error
            ]
        )
    assert "Language configuration missing" in str(exc_info.value)


def test_recognizer_registry_config_only_predefined_no_languages():
    """Predefined recognizers without languages should be allowed (use defaults)."""
    config = RecognizerRegistryConfig(
        recognizers=[
            "credit_card",
            {"name": "UrlRecognizer", "type": "predefined"},
        ]
    )
    assert len(config.recognizers) == 2
    assert isinstance(config.recognizers[0], str)
    assert isinstance(config.recognizers[1], PredefinedRecognizerConfig)


def test_recognizer_registry_config_auto_detect_type():
    """Test auto-detection of recognizer type based on patterns and deny_list."""
    # Should be detected as custom due to patterns
    custom_with_patterns_config = {
        "name": "auto_custom_patterns",
        "supported_entity": "TEST",
        "supported_language": "en",
        "patterns": [{"name": "test", "regex": r"\d+", "score": 0.5}]
    }

    # Should be detected as custom due to deny_list
    custom_with_deny_list_config = {
        "name": "auto_custom_deny",
        "supported_entity": "TEST",
        "supported_language": "en",
        "deny_list": ["exclude_this"]
    }

    # Should be detected as predefined (no patterns or deny_list)
    predefined_config = {
        "name": "UrlRecognizer",
        "enabled": True
    }

    config = RecognizerRegistryConfig(
        supported_languages=["en"],  # Add global language to satisfy new validation
        recognizers=[custom_with_patterns_config, custom_with_deny_list_config, predefined_config]
    )

    assert isinstance(config.recognizers[0], CustomRecognizerConfig)
    assert config.recognizers[0].type == "custom"
    assert isinstance(config.recognizers[1], CustomRecognizerConfig)
    assert config.recognizers[1].type == "custom"
    assert isinstance(config.recognizers[2], PredefinedRecognizerConfig)
    assert config.recognizers[2].type == "predefined"



def test_complete_registry_scenario():
    """Test a complete registry configuration scenario."""
    registry_config = {
        "supported_languages": ["en", "es"],
        "recognizers": [
            "credit_card",  # String recognizer (kept as string)
            {
                "name": "EmailRecognizer",
                "type": "predefined",
                "enabled": True
            },
            {
                "name": "custom_pattern",
                "type": "custom",
                "supported_entity": "CUSTOM_ID",
                "supported_language": "en",
                "patterns": [
                    {
                        "name": "id_pattern",
                        "regex": r"ID-\d{6}",
                        "score": 0.9
                    }
                ]
            }
        ]
    }

    config = RecognizerRegistryConfig(**registry_config)
    assert len(config.recognizers) == 3
    assert isinstance(config.recognizers[0], str)
    assert isinstance(config.recognizers[1], PredefinedRecognizerConfig)
    assert isinstance(config.recognizers[2], CustomRecognizerConfig)



def test_error_handling_cascade():
    """Test that validation errors are properly cascaded."""
    # This should fail at the CustomRecognizerConfig level
    with pytest.raises(ValidationError) as exc_info:
        RecognizerRegistryConfig(
            recognizers=[
                {
                    "name": "invalid_custom",
                    "type": "custom",
                    "supported_entity": "TEST",
                    "supported_language": "en",  # Add language to avoid that error
                    "patterns": [
                        {
                            "name": "test",
                            "regex": r"\d+",
                            "score": 2.0  # Invalid score > 1.0
                        }
                    ]
                }
            ]
        )
    assert "Pattern score should be between 0 and 1" in str(exc_info.value)


def test_predefined_recognizer_config_valid_recognizer():
    """Test predefined recognizer with valid recognizer name."""
    # Test with a common recognizer that should exist
    config = PredefinedRecognizerConfig(name="CreditCardRecognizer")
    assert config.name == "CreditCardRecognizer"
    assert config.type == "predefined"


def test_predefined_recognizer_config_invalid_recognizer():
    """Test predefined recognizer with invalid recognizer name."""
    with pytest.raises(ValidationError) as exc_info:
        PredefinedRecognizerConfig(name="NonExistentRecognizer")


def test_predefined_recognizer_config_case_sensitive():
    """Test that recognizer names are case sensitive."""
    with pytest.raises(ValidationError) as exc_info:
        PredefinedRecognizerConfig(name="creditcardrecognizer")  # lowercase

    error_message = str(exc_info.value)
    assert "Predefined recognizer 'creditcardrecognizer' not found" in error_message


def test_custom_recognizer_config_predefined_name_error():
    """Test that using a predefined recognizer name for custom recognizer raises error."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="CreditCardRecognizer",  # This is a predefined recognizer
            type="custom",
            supported_entity="CREDIT_CARD",
            patterns=[{"name": "test", "regex": r"\d+", "score": 0.5}]
        )

    error_message = str(exc_info.value)
    assert "Recognizer 'CreditCardRecognizer' conflicts with a predefined" in error_message
    assert "Either use type: 'predefined' or choose a different name" in error_message


def test_custom_recognizer_config_predefined_name_error_without_required_fields():
    """Test that predefined name conflict is caught even when missing required fields."""
    with pytest.raises(ValidationError) as exc_info:
        CustomRecognizerConfig(
            name="UrlRecognizer",  # This is a predefined recognizer
            type="custom"
            # Intentionally missing supported_entity, patterns, and deny_list
        )

    error_message = str(exc_info.value)
    assert "conflicts with a predefined recognizer" in error_message or \
           "is a predefined recognizer but is marked as 'custom'" in error_message


def test_custom_recognizer_config_unique_name_valid():
    """Test that custom recognizers with unique names are valid."""
    config = CustomRecognizerConfig(
        name="MyCustomRecognizer",  # This should not exist as predefined
        type="custom",
        supported_entity="CUSTOM_ENTITY",
        patterns=[{"name": "test", "regex": r"\d+", "score": 0.5}]
    )
    assert config.name == "MyCustomRecognizer"
    assert config.type == "custom"


def test_custom_recognizer_config_predefined_name_validation_with_import_error():
    """Test that custom recognizers with unique names (not predefined) are valid.

    This test verifies that a custom recognizer can use a name that doesn't
    conflict with any predefined recognizers.
    """
    config = CustomRecognizerConfig(
        name="SomeUniqueRecognizer",
        type="custom",
        supported_entity="TEST",
        patterns=[{"name": "test", "regex": r"\d+", "score": 0.5}]
    )
    assert config.name == "SomeUniqueRecognizer"
    assert config.type == "custom"


def test_custom_recognizer_with_language_no_global_languages():
    """Custom recognizer specifying its own language should pass without global languages."""
    registry_config = {
        "recognizers": [
            {
                "name": "my_custom_with_lang",
                "type": "custom",
                "supported_entity": "TEST",
                "supported_language": "en",
                "patterns": [
                    {"name": "p", "regex": r"\d+", "score": 0.5}
                ]
            }
        ]
    }
    config = RecognizerRegistryConfig(**registry_config)
    assert len(config.recognizers) == 1
    assert isinstance(config.recognizers[0], CustomRecognizerConfig)
    assert config.recognizers[0].supported_language == "en"
    assert config.recognizers[0].supported_languages is None


def test_recognizer_registry_config_custom_name_with_hf_class():
    """Test that class_name takes priority over name for config selection."""
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        HuggingFaceRecognizerConfig,
        RecognizerRegistryConfig,
    )

    registry_config = {
        "recognizers": [
            {
                "name": "CustomKoreanWorker",
                "class_name": "HuggingFaceNerRecognizer",
                "type": "predefined",
                "supported_language": "ko",
                "supported_entities": ["PERSON"],
                "model_name": "TestModel/Ner"
            }
        ]
    }

    config = RecognizerRegistryConfig(**registry_config)
    recognizer = config.recognizers[0]

    assert isinstance(recognizer, HuggingFaceRecognizerConfig)
    assert recognizer.name == "CustomKoreanWorker"
    assert recognizer.class_name == "HuggingFaceNerRecognizer"
    assert recognizer.model_name == "TestModel/Ner"


def test_gliner_recognizer_config_model_name():
    """Test that GLiNERRecognizer model_name is preserved through config validation."""
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        GLiNERRecognizerConfig,
        RecognizerRegistryConfig,
    )

    registry_config = {
        "recognizers": [
            {
                "name": "GLiNERRecognizer",
                "type": "predefined",
                "supported_language": "en",
                "model_name": "custom/gliner-model",
                "threshold": 0.5,
                "flat_ner": False,
                "multi_label": True,
            }
        ]
    }

    config = RecognizerRegistryConfig(**registry_config)
    recognizer = config.recognizers[0]

    assert isinstance(recognizer, GLiNERRecognizerConfig)
    assert recognizer.model_name == "custom/gliner-model"
    assert recognizer.threshold == 0.5
    assert recognizer.flat_ner is False
    assert recognizer.multi_label is True


def test_gliner_recognizer_config_model_dump_excludes_none():
    """Test that GLiNERRecognizerConfig.model_dump excludes None fields by default."""
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        GLiNERRecognizerConfig,
    )

    config = GLiNERRecognizerConfig(
        name="GLiNERRecognizer",
        supported_language="en",
        model_name="custom/gliner-model",
    )
    dumped = config.model_dump()
    assert "model_name" in dumped
    assert dumped["model_name"] == "custom/gliner-model"
    # Fields not provided should be excluded, not set to None
    assert "flat_ner" not in dumped
    assert "threshold" not in dumped
    assert "entity_mapping" not in dumped


def test_gliner_recognizer_config_entity_mapping_and_supported_entities_mutually_exclusive():
    """Test that entity_mapping and supported_entities cannot both be set."""
    import pytest
    from pydantic import ValidationError

    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        GLiNERRecognizerConfig,
    )

    with pytest.raises(ValidationError, match="mutually exclusive"):
        GLiNERRecognizerConfig(
            name="GLiNERRecognizer",
            supported_language="en",
            entity_mapping={"person": "PERSON"},
            supported_entities=["PERSON"],
        )


def test_huggingface_recognizer_config_model_dump_excludes_none():
    """Test that HuggingFaceRecognizerConfig.model_dump excludes None fields by default."""
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        HuggingFaceRecognizerConfig,
    )

    config = HuggingFaceRecognizerConfig(
        name="HuggingFaceNerRecognizer",
        supported_language="en",
        model_name="custom/ner-model",
    )
    dumped = config.model_dump()
    assert "model_name" in dumped
    assert dumped["model_name"] == "custom/ner-model"
    # Fields not provided should be excluded, not set to None
    assert "tokenizer_name" not in dumped
    assert "threshold" not in dumped
    assert "label_mapping" not in dumped


def test_config_model_map_fallback_to_predefined():
    """Test CONFIG_MODEL_MAP falls back to Predefined for unknown class_name."""
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        PredefinedRecognizerConfig,
        RecognizerRegistryConfig,
    )

    registry_config = {
        "recognizers": [
            {
                "name": "MySpacy",
                "class_name": "SpacyRecognizer",
                "type": "predefined",
                "supported_language": "en",
            }
        ]
    }

    config = RecognizerRegistryConfig(**registry_config)
    recognizer = config.recognizers[0]

    assert isinstance(recognizer, PredefinedRecognizerConfig)
    assert recognizer.name == "MySpacy"
    assert recognizer.class_name == "SpacyRecognizer"


@pytest.mark.parametrize(
    "raw_thresholds",
    [True, "0.4", ["default", 0.4], {"default": "0.4"}, {"default": 0.4}],
)
def test_base_recognizer_score_thresholds_preserve_raw_values(raw_thresholds):
    config = BaseRecognizerConfig(
        name="CreditCardRecognizer", score_thresholds=raw_thresholds
    )

    assert config.model_dump()["score_thresholds"] == raw_thresholds
    assert type(config.model_dump()["score_thresholds"]) is type(raw_thresholds)


@pytest.mark.parametrize(
    "recognizer",
    [
        {
            "name": "CreditCardRecognizer",
            "type": "predefined",
            "score_thresholds": {"default": 0.4},
        },
        {
            "name": "custom_thresholds",
            "type": "custom",
            "supported_entity": "CUSTOM",
            "supported_language": "en",
            "patterns": [{"name": "custom", "regex": "x", "score": 0.5}],
            "score_thresholds": {"CUSTOM": 0.6},
        },
        {
            "name": "HuggingFaceNerRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"PERSON": 0.7},
        },
        {
            "name": "GLiNERRecognizer",
            "type": "predefined",
            "supported_language": "en",
            "score_thresholds": {"PERSON": 0.8},
        },
    ],
)
def test_registry_model_dump_preserves_score_thresholds_for_every_entry_type(
    recognizer,
):
    original = recognizer["score_thresholds"].copy()

    dumped = RecognizerRegistryConfig(recognizers=[recognizer]).model_dump()

    assert dumped["recognizers"][0]["score_thresholds"] == original


def test_registry_model_does_not_mutate_recognizer_input_when_inferring_type():
    recognizer = {
        "name": "custom_thresholds",
        "supported_entity": "CUSTOM",
        "supported_language": "en",
        "patterns": [{"name": "custom", "regex": "x", "score": 0.5}],
        "score_thresholds": {"default": 0.4},
    }
    original = recognizer.copy()

    RecognizerRegistryConfig(recognizers=[recognizer])

    assert recognizer == original
