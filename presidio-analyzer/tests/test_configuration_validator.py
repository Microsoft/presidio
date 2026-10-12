"""Tests for the Pydantic-based validation system using existing adapted classes."""
# ruff: noqa: D103,E501

import pytest
from presidio_analyzer.input_validation import ConfigurationValidator

# ========== Language Code Validation Tests ==========

def test_validate_language_codes_valid():
    """Test valid language codes."""
    valid_languages = ["en", "es", "fr", "de"]
    result = ConfigurationValidator.validate_language_codes(valid_languages)
    assert result == valid_languages


def test_validate_language_codes_valid_with_country():
    """Test valid language codes with country codes."""
    valid_languages = ["en-US", "en-GB", "es-ES"]
    result = ConfigurationValidator.validate_language_codes(valid_languages)
    assert result == valid_languages


def test_validate_language_codes_invalid_format():
    """Test invalid language code format."""
    invalid_languages = ["english", "EN", "e", "en-us"]
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_language_codes(invalid_languages)
    assert "Invalid language code format" in str(exc_info.value)


def test_validate_language_codes_mixed_invalid():
    """Test mixed valid and invalid language codes."""
    mixed_languages = ["en", "invalid_lang", "es"]
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_language_codes(mixed_languages)
    assert "Invalid language code format" in str(exc_info.value)


# ========== File Path Validation Tests ==========

def test_file_path_validation_success(tmp_path):
    """Test file path validation with existing file."""
    test_file = tmp_path / "test.yaml"
    test_file.write_text("test: content")

    validated_path = ConfigurationValidator.validate_file_path(str(test_file))
    assert validated_path == test_file


def test_file_path_validation_with_path_object(tmp_path):
    """Test file path validation with Path object."""
    test_file = tmp_path / "test.yaml"
    test_file.write_text("test: content")

    validated_path = ConfigurationValidator.validate_file_path(test_file)
    assert validated_path == test_file


def test_file_path_validation_nonexistent():
    """Test file path validation with non-existent file."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_file_path("/nonexistent/file.yaml")

    assert "does not exist" in str(exc_info.value)


def test_file_path_validation_directory(tmp_path):
    """Test file path validation with directory instead of file."""
    test_dir = tmp_path / "test_directory"
    test_dir.mkdir()

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_file_path(test_dir)

    assert "not a file" in str(exc_info.value)


# ========== Score Threshold Validation Tests ==========

def test_validate_score_threshold_valid():
    """Test valid score thresholds."""
    valid_thresholds = [0.0, 0.5, 1.0, 0.25, 0.75]
    for threshold in valid_thresholds:
        result = ConfigurationValidator.validate_score_threshold(threshold)
        assert result == threshold


def test_validate_score_threshold_above_one():
    """Test score threshold above 1.0."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_score_threshold(1.5)
    assert "must be between 0.0 and 1.0" in str(exc_info.value)


def test_validate_score_threshold_negative():
    """Test negative score threshold."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_score_threshold(-0.1)
    assert "must be between 0.0 and 1.0" in str(exc_info.value)


def test_validate_score_threshold_way_above():
    """Test score threshold far above valid range."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_score_threshold(100.0)
    assert "must be between 0.0 and 1.0" in str(exc_info.value)


@pytest.mark.parametrize("threshold", [True, False, "0.5", None, [], {}])
def test_validate_score_threshold_non_numeric(threshold):
    """Test score threshold rejects booleans and non-numeric values."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_score_threshold(threshold)
    assert "must be numeric" in str(exc_info.value)


# ========== NLP Configuration Validation Tests ==========

def test_configuration_validator_nlp_config_valid():
    """Test ConfigurationValidator accepts valid NLP validation."""
    valid_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "en", "model_name": "en_core_web_lg"}
        ]
    }

    validated = ConfigurationValidator.validate_nlp_configuration(valid_config)
    assert validated == valid_config


def test_nlp_config_multiple_models():
    """Test NLP configuration with multiple models."""
    valid_config = {
        "nlp_engine_name": "spacy",
        "models": [
            {"lang_code": "en", "model_name": "en_core_web_lg"},
            {"lang_code": "es", "model_name": "es_core_news_lg"}
        ]
    }

    validated = ConfigurationValidator.validate_nlp_configuration(valid_config)
    assert validated == valid_config


def test_configuration_validator_nlp_config_missing_fields():
    """Test ConfigurationValidator rejects NLP config with missing required fields."""
    invalid_config = {
        "nlp_engine_name": "spacy"
        # Missing "models" field
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)

    assert "missing required fields" in str(exc_info.value)


def test_nlp_config_missing_nlp_engine_name():
    """Test NLP config missing nlp_engine_name."""
    invalid_config = {
        "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "missing required fields" in str(exc_info.value)


def test_nlp_config_not_dict():
    """Test NLP configuration that is not a dictionary."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration("not a dict")
    assert "must be a dictionary" in str(exc_info.value)


def test_nlp_config_models_not_list():
    """Test NLP configuration with models not as list."""
    invalid_config = {
        "nlp_engine_name": "spacy",
        "models": {"lang_code": "en", "model_name": "en_core_web_lg"}
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "Models must be a non-empty list" in str(exc_info.value)


def test_nlp_config_models_empty_list():
    """Test NLP configuration with empty models list."""
    invalid_config = {
        "nlp_engine_name": "spacy",
        "models": []
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "Models must be a non-empty list" in str(exc_info.value)


def test_nlp_config_model_not_dict():
    """Test NLP configuration with model that is not a dict."""
    invalid_config = {
        "nlp_engine_name": "spacy",
        "models": ["en_core_web_lg"]
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "Each model must be a dictionary" in str(exc_info.value)


def test_nlp_config_model_missing_lang_code():
    """Test NLP configuration with model missing lang_code."""
    invalid_config = {
        "nlp_engine_name": "spacy",
        "models": [{"model_name": "en_core_web_lg"}]
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "must have 'lang_code' and 'model_name'" in str(exc_info.value)


def test_nlp_config_model_missing_model_name():
    """Test NLP configuration with model missing model_name."""
    invalid_config = {
        "nlp_engine_name": "spacy",
        "models": [{"lang_code": "en"}]
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_nlp_configuration(invalid_config)
    assert "must have 'lang_code' and 'model_name'" in str(exc_info.value)


# ========== Recognizer Registry Configuration Tests ==========

def test_recognizer_registry_valid_custom_recognizer():
    """Test valid recognizer registry configuration with custom recognizer."""
    valid_config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CustomRecognizer",
                "type": "custom",
                "supported_entity": "CUSTOM_ENTITY",
                "patterns": [
                    {
                        "name": "pattern1",
                        "regex": "test",
                        "score": 0.5
                    }
                ]
            }
        ]
    }

    result = ConfigurationValidator.validate_recognizer_registry_configuration(valid_config)
    assert result is not None
    assert "recognizers" in result


def test_recognizer_registry_valid_predefined_recognizer():
    """Test valid recognizer registry configuration with predefined recognizer."""
    valid_config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined"
            }
        ]
    }

    result = ConfigurationValidator.validate_recognizer_registry_configuration(valid_config)
    assert result is not None


def test_recognizer_registry_empty_recognizers_list():
    """Test recognizer registry with empty recognizers list."""
    invalid_config = {
        "supported_languages": ["en"],
        "recognizers": []
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_recognizer_registry_configuration(invalid_config)
    assert "Invalid recognizer registry configuration" in str(exc_info.value)


def test_configuration_validator_recognizer_registry_unknown_keys():
    """Test ConfigurationValidator rejects recognizer registry config with unknown keys."""
    invalid_config = {
        "supported_languages": ["en"],
        "global_regex_flags": 26,
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined"
            }
        ],
        "invalid_field": "value",
        "typo_key": 456
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_recognizer_registry_configuration(invalid_config)
    assert "Invalid recognizer registry configuration" in str(exc_info.value)


# ========== Analyzer Configuration Tests ==========

def test_configuration_validator_analyzer_config_valid():
    """Test ConfigurationValidator accepts valid analyzer validation."""
    valid_config = {
        "supported_languages": ["en", "es"],
        "default_score_threshold": 0.5,
        "nlp_configuration": {
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        }
    }

    validated = ConfigurationValidator.validate_analyzer_configuration(valid_config)
    assert validated == valid_config


def test_analyzer_config_rejects_removed_recognizer_score_thresholds_key():
    with pytest.raises(ValueError, match="Unknown configuration key"):
        ConfigurationValidator.validate_analyzer_configuration(
            {
                "supported_languages": ["en"],
                "recognizer_score_thresholds": {"CreditCardRecognizer": 0.4},
            }
        )


def test_registry_config_preserves_valid_score_thresholds():
    valid_config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "score_thresholds": {"default": 0.4, "CREDIT_CARD": 0.7},
            }
        ],
    }

    validated = ConfigurationValidator.validate_recognizer_registry_configuration(
        valid_config
    )

    assert validated["recognizers"][0]["score_thresholds"] == {
        "default": 0.4,
        "CREDIT_CARD": 0.7,
    }


@pytest.mark.parametrize(
    "score_thresholds",
    [False, 0, "", [], {"default": True}, {"default": "0.4"}],
)
def test_registry_config_rejects_uncoerced_invalid_score_thresholds(
    score_thresholds,
):
    config = {
        "supported_languages": ["en"],
        "recognizers": [
            {
                "name": "CreditCardRecognizer",
                "type": "predefined",
                "score_thresholds": score_thresholds,
            }
        ],
    }

    with pytest.raises(ValueError):
        ConfigurationValidator.validate_recognizer_registry_configuration(config)


def test_analyzer_config_minimal():
    """Test minimal valid analyzer configuration."""
    valid_config = {
        "supported_languages": ["en"]
    }

    validated = ConfigurationValidator.validate_analyzer_configuration(valid_config)
    assert validated == valid_config


def test_analyzer_config_with_recognizer_registry():
    """Test analyzer configuration with recognizer registry."""
    valid_config = {
        "supported_languages": ["en"],
        "recognizer_registry": {
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "CreditCardRecognizer",
                    "type": "predefined"
                }
            ]
        }
    }

    validated = ConfigurationValidator.validate_analyzer_configuration(valid_config)
    assert validated is not None


def test_configuration_validator_analyzer_config_invalid_threshold():
    """Test ConfigurationValidator rejects invalid score threshold."""
    invalid_config = {
        "supported_languages": ["en"],
        "default_score_threshold": 1.5  # Invalid: > 1.0
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)

    assert "must be between 0.0 and 1.0" in str(exc_info.value)


@pytest.mark.parametrize("threshold", [True, "0.5"])
def test_configuration_validator_analyzer_config_non_numeric_threshold(threshold):
    """Test ConfigurationValidator rejects non-numeric score thresholds."""
    invalid_config = {
        "supported_languages": ["en"],
        "default_score_threshold": threshold,
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)

    assert "must be numeric" in str(exc_info.value)


def test_analyzer_config_not_dict():
    """Test analyzer configuration that is not a dictionary."""
    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration("not a dict")
    assert "must be a dictionary" in str(exc_info.value)


def test_configuration_validator_analyzer_config_unknown_keys():
    """Test ConfigurationValidator rejects analyzer config with unknown keys."""
    invalid_config = {
        "supported_languages": ["en"],
        "default_score_threshold": 0.5,
        "unknown_key": "some_value",
        "another_typo": 123
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)
    assert "Unknown configuration key" in str(exc_info.value)


def test_analyzer_config_invalid_languages():
    """Test analyzer configuration with invalid language codes."""
    invalid_config = {
        "supported_languages": ["invalid_lang"]
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)
    assert "Invalid language code format" in str(exc_info.value)


def test_analyzer_config_invalid_nlp_nested():
    """Test analyzer configuration with invalid nested NLP config."""
    invalid_config = {
        "supported_languages": ["en"],
        "nlp_configuration": {
            "nlp_engine_name": "spacy"
            # Missing models
        }
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)
    assert "missing required fields" in str(exc_info.value)


def test_analyzer_config_invalid_recognizer_registry_nested():
    """Test analyzer configuration with invalid nested recognizer registry."""
    invalid_config = {
        "supported_languages": ["en"],
        "recognizer_registry": {
            "recognizers": []  # Empty list not allowed
        }
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_analyzer_configuration(invalid_config)
    assert "Invalid recognizer registry configuration" in str(exc_info.value)


def test_analyzer_config_threshold_at_boundaries():
    """Test analyzer configuration with threshold at boundaries."""
    # Test 0.0
    config_zero = {
        "supported_languages": ["en"],
        "default_score_threshold": 0.0
    }
    validated = ConfigurationValidator.validate_analyzer_configuration(config_zero)
    assert validated["default_score_threshold"] == 0.0

    # Test 1.0
    config_one = {
        "supported_languages": ["en"],
        "default_score_threshold": 1.0
    }
    validated = ConfigurationValidator.validate_analyzer_configuration(config_one)
    assert validated["default_score_threshold"] == 1.0


def test_analyzer_config_all_fields():
    """Test analyzer configuration with all fields populated."""
    valid_config = {
        "supported_languages": ["en", "es"],
        "default_score_threshold": 0.7,
        "nlp_configuration": {
            "nlp_engine_name": "spacy",
            "models": [
                {"lang_code": "en", "model_name": "en_core_web_lg"},
                {"lang_code": "es", "model_name": "es_core_news_lg"}
            ]
        },
        "recognizer_registry": {
            "supported_languages": ["en"],
            "global_regex_flags": 26,
            "recognizers": [
                {
                    "name": "CreditCardRecognizer",
                    "type": "predefined"
                }
            ]
        }
    }

    validated = ConfigurationValidator.validate_analyzer_configuration(valid_config)
    assert validated == valid_config

