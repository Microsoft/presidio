# ruff: noqa: D103,D200,D205,E501,F841,I001

import pytest
import re
from pathlib import Path
from typing import List
from inspect import signature
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistryProvider
from presidio_analyzer.recognizer_registry.recognizers_loader_utils import RecognizerConfigurationLoader
from presidio_analyzer import RecognizerRegistry


def assert_default_configuration(
    recognizer_registry: RecognizerRegistry, mandatory_recognizers: List[str]
):
    assert recognizer_registry.supported_languages == ["en"]
    assert recognizer_registry.global_regex_flags == re.DOTALL | re.MULTILINE | re.IGNORECASE
    names = [recognizer.name for recognizer in recognizer_registry.recognizers]
    for predefined_recognizer in mandatory_recognizers:
        assert predefined_recognizer in names


def test_recognizer_registry_provider_default_configuration(mandatory_recognizers):
    provider = RecognizerRegistryProvider()
    recognizer_registry = provider.create_recognizer_registry()
    assert_default_configuration(recognizer_registry, mandatory_recognizers)


def test_recognizer_registry_provider_configuration_file():
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/test_recognizer_registry.yaml")
    provider = RecognizerRegistryProvider(test_yaml)
    recognizer_registry = provider.create_recognizer_registry()
    assert recognizer_registry.supported_languages == ["en", "es"]
    assert recognizer_registry.global_regex_flags == 26
    assert len(recognizer_registry.recognizers) == 5
    assert [recognizer.supported_language for recognizer in recognizer_registry.recognizers if recognizer.name == "ItFiscalCodeRecognizer"] == ["en", "es"]
    assert [recognizer.supported_language for recognizer in recognizer_registry.recognizers if recognizer.name == "CreditCardRecognizer"] == ["en"]
    assert [recognizer.supported_language for recognizer in recognizer_registry.recognizers if recognizer.name == "ExampleCustomRecognizer"] == ["en", "es"]
    spanish_recognizer = [recognizer for recognizer in recognizer_registry.recognizers if recognizer.name == "ExampleCustomRecognizer" and recognizer.supported_language == "es"][0]
    assert spanish_recognizer.context == ["tarjeta", "credito"]
    credit_card = next(
        recognizer
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "CreditCardRecognizer"
    )
    assert credit_card.score_thresholds == {
        "default": 0.4,
        "CREDIT_CARD": 0.8,
    }
    assert all(
        recognizer.score_thresholds == {"ZIP": 0.6}
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "ExampleCustomRecognizer"
    )


def test_recognizer_registry_provider_inline_thresholds_attach_to_instance():
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "CreditCardRecognizer",
                    "type": "predefined",
                    "supported_language": "en",
                    "score_thresholds": {"default": 0.4},
                }
            ],
        }
    )

    recognizer = provider.create_recognizer_registry().recognizers[0]

    assert recognizer.score_thresholds == {"default": 0.4}


def test_recognizer_registry_provider_omitted_deny_list_score_defaults_to_one():
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "Titles",
                    "supported_entity": "TITLE",
                    "deny_list": ["Mr.", "Mrs."],
                }
            ],
        }
    )

    recognizer = provider.create_recognizer_registry().recognizers[0]

    assert recognizer.deny_list_score == 1.0
    assert all(pattern.score == 1.0 for pattern in recognizer.patterns)


def test_recognizer_registry_provider_explicit_deny_list_score_is_honored():
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "Titles",
                    "supported_entity": "TITLE",
                    "deny_list": ["Mr.", "Mrs."],
                    "deny_list_score": 0.3,
                }
            ],
        }
    )

    recognizer = provider.create_recognizer_registry().recognizers[0]

    assert recognizer.deny_list_score == 0.3
    assert all(pattern.score == 0.3 for pattern in recognizer.patterns)


def test_recognizer_registry_provider_omitted_thresholds_default_to_empty():
    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "recognizers": [
                {
                    "name": "CreditCardRecognizer",
                    "type": "predefined",
                    "supported_language": "en",
                }
            ],
        }
    )

    recognizer = provider.create_recognizer_registry().recognizers[0]

    assert recognizer.score_thresholds == {}


@pytest.mark.parametrize(
    "score_thresholds",
    [True, False, 0, "", "0.4", [], {"": 0.4}, {"default": True}, {"default": 1.1}],
)
def test_recognizer_registry_provider_rejects_invalid_score_thresholds(
    score_thresholds,
):
    with pytest.raises(ValueError):
        RecognizerRegistryProvider(
            registry_configuration={
                "supported_languages": ["en"],
                "recognizers": [
                    {
                        "name": "CreditCardRecognizer",
                        "type": "predefined",
                        "score_thresholds": score_thresholds,
                    }
                ],
            }
        )


def test_recognizer_registry_provider_configuration_file_load_predefined(mandatory_recognizers):
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/test_recognizers.yaml")
    provider = RecognizerRegistryProvider(test_yaml)
    recognizer_registry = provider.create_recognizer_registry()
    assert recognizer_registry.supported_languages == ["en"]
    assert recognizer_registry.global_regex_flags == 26
    assert len(recognizer_registry.recognizers) == 2
    assert [recognizer.supported_language for recognizer in recognizer_registry.recognizers if recognizer.name == "TitleRecognizer"] == ["en"]
    assert [recognizer.supported_language for recognizer in recognizer_registry.recognizers if recognizer.name == "ZipCodeRecognizer"] == ["en"]
    zipcode_recognizer = [recognizer for recognizer in recognizer_registry.recognizers if recognizer.name == "ZipCodeRecognizer" and recognizer.supported_language == "en"][0]
    assert zipcode_recognizer.context == ["zip", "code"]


def test_recognizer_registry_provider_missing_conf_file_expect_default_configuration(mandatory_recognizers):
    test_yaml = Path("missing.yaml")
    provider = RecognizerRegistryProvider(test_yaml)
    recognizer_registry = provider.create_recognizer_registry()
    assert_default_configuration(recognizer_registry, mandatory_recognizers)


def test_recognizer_registry_provider_corrupt_conf_file_fail(mandatory_recognizers):
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/recognizers_error.yaml")

    with pytest.raises(TypeError):
        RecognizerRegistryProvider(
            conf_file=test_yaml
        )


def test_recognizer_registry_provider_conf_file_valid_missing_keys_fail():
    """Test that a config file with invalid keys (no mandatory keys) raises an error."""
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/recognizer_configuration_missing_keys.yaml")

    # Config file with no mandatory keys should raise ValueError
    with pytest.raises(ValueError, match="does not contain any of the mandatory keys"):
        RecognizerRegistryProvider(conf_file=test_yaml)



def test_recognizer_registry_provider_when_conf_file_and_registry_configuration_fail():
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/recognizer_configuration_missing_keys.yaml")
    registry_configuration = {"supported_languages": ["de", "es"]}

    with pytest.raises(ValueError):
        RecognizerRegistryProvider(
            conf_file=test_yaml, registry_configuration=registry_configuration
        )


def test_recognizer_provider_with_minimal_creates_empty_registry():
    this_path = Path(__file__).parent.absolute()
    minimal_yaml = Path(this_path, "conf/test_minimal_registry_conf.yaml")
    provider = RecognizerRegistryProvider(conf_file=minimal_yaml)
    registry = provider.create_recognizer_registry()

    assert len(registry.recognizers) == 1


def test_recognizer_provider_with_nlp_reco_only_creates_nlp_recognizer():
    this_path = Path(__file__).parent.absolute()
    nlp_reco_path = Path(this_path, "conf/test_nlp_recognizer_only_conf.yaml")
    provider = RecognizerRegistryProvider(conf_file=nlp_reco_path)
    registry = provider.create_recognizer_registry()

    assert len(registry.recognizers) == 1
    assert isinstance(registry.recognizers[0], SpacyRecognizer)


def test_default_attributes_equal_recognizer_registry_signature():
    registry_init_signature = signature(RecognizerRegistry)
    registry_fields = set(registry_init_signature.parameters.keys())

    registry_provider = RecognizerRegistryProvider()
    provider_fields = set(RecognizerConfigurationLoader.mandatory_keys)

    assert registry_fields == provider_fields


def test_recognizer_registry_provider_missing_language_config_raises():
    """
    Test that a recognizer configuration without language info gets the default languages.
    """
    from presidio_analyzer.recognizer_registry.recognizer_registry_provider import RecognizerRegistryProvider
    # Configuration with no supported_languages and no recognizer language
    registry_configuration = {
        "recognizers": [
            {
                "name": "CustomRecognizer",
                "type": "custom",
                "supported_entity": "CUSTOM_ENTITY",
                "patterns": [
                    {"name": "custom", "regex": "test", "score": 0.5}
                ],
                # No supported_language or supported_languages
            }
        ]
    }
    # When registry_configuration is passed, it gets merged with defaults
    # so supported_languages gets filled in and recognizers get created for default languages
    provider = RecognizerRegistryProvider(registry_configuration=registry_configuration)
    # Verify that defaults were applied
    assert provider.configuration.get("supported_languages") is not None
    registry = provider.create_recognizer_registry()
    # Verify registry was created successfully with default language
    assert len(registry.recognizers) > 0


# Tests for missing required and optional fields in YAML configuration

def test_missing_recognizers_raises_exception():
    """Test that missing recognizers raises an exception."""
    this_path = Path(__file__).parent.absolute()
    conf_file = Path(this_path, "conf/missing_recognizers.yaml")

    with pytest.raises(ValueError) as exc_info:
        RecognizerRegistryProvider(conf_file=conf_file)

    assert "recognizers" in str(exc_info.value)
    assert "mandatory" in str(exc_info.value).lower()


def test_missing_global_regex_flags_uses_default():
    """Test that missing global_regex_flags uses default value without error."""
    this_path = Path(__file__).parent.absolute()
    conf_file = Path(this_path, "conf/missing_global_regex_flags.yaml")

    # Should not raise an exception
    provider = RecognizerRegistryProvider(conf_file=conf_file)
    registry = provider.create_recognizer_registry()

    # Check that default value was used (26 = re.DOTALL | re.MULTILINE | re.IGNORECASE)
    assert registry.global_regex_flags == 26
    assert registry.supported_languages == ["en"]


def test_valid_configuration_passes():
    """Test that a valid configuration passes validation."""
    from presidio_analyzer.input_validation import ConfigurationValidator

    config = {
        "supported_languages": ["en", "es"],
        "recognizers": ["CreditCardRecognizer", "EmailRecognizer"],
        "global_regex_flags": 26,
    }

    validated = ConfigurationValidator.validate_recognizer_registry_configuration(config)

    assert validated is not None
    assert validated["supported_languages"] == ["en", "es"]
    assert validated["global_regex_flags"] == 26


def test_valid_configuration_without_global_regex_flags():
    """Test that configuration without global_regex_flags uses default without error."""
    from presidio_analyzer.input_validation import ConfigurationValidator

    config = {
        "supported_languages": ["en"],
        "recognizers": ["CreditCardRecognizer"],
    }

    # Should not raise an exception
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(config)

    # Check default value was set
    assert validated["global_regex_flags"] == 26
    assert validated["supported_languages"] == ["en"]


def test_recognizers_none_raises_exception():
    """Test that recognizers explicitly set to None raises an exception."""
    from presidio_analyzer.input_validation import ConfigurationValidator

    config = {
        "supported_languages": ["en"],
        "recognizers": None,
        "global_regex_flags": 26,
    }

    with pytest.raises(ValueError) as exc_info:
        ConfigurationValidator.validate_recognizer_registry_configuration(config)


def test_direct_validation_with_missing_global_regex_flags():
    """Test direct validation without global_regex_flags succeeds with default."""
    from presidio_analyzer.input_validation import ConfigurationValidator

    config = {
        "supported_languages": ["en"],
        "recognizers": ["CreditCardRecognizer"],
    }

    # Should not raise an exception
    validated = ConfigurationValidator.validate_recognizer_registry_configuration(config)

    # Verify default value and successful creation
    assert validated["global_regex_flags"] == 26
    assert validated["supported_languages"] == ["en"]


def test_recognizer_registry_provider_yaml_character_chunker_config():
    """Test that text_chunker dict with character chunker is passed from YAML."""
    this_path = Path(__file__).parent.absolute()
    test_yaml = Path(this_path, "conf/test_hf_recognizer_with_chunker.yaml")
    provider = RecognizerRegistryProvider(conf_file=test_yaml)
    registry = provider.create_recognizer_registry()

    from presidio_analyzer.predefined_recognizers.ner import HuggingFaceNerRecognizer
    from presidio_analyzer.chunkers import CharacterBasedTextChunker

    hf_recognizers = [
        r for r in registry.recognizers
        if isinstance(r, HuggingFaceNerRecognizer)
    ]
    assert len(hf_recognizers) == 1

    recognizer = hf_recognizers[0]
    assert isinstance(recognizer.text_chunker, CharacterBasedTextChunker)
    assert recognizer.text_chunker.chunk_size == 300
    assert recognizer.text_chunker.chunk_overlap == 40


def test_recognizer_registry_provider_tokenizer_chunker_config():
    """Test that text_chunker with tokenizer type creates TokenizerBasedTextChunker."""
    from unittest.mock import MagicMock
    from presidio_analyzer.predefined_recognizers.ner import HuggingFaceNerRecognizer
    from presidio_analyzer.chunkers import TokenizerBasedTextChunker

    mock_tokenizer = MagicMock()
    mock_tokenizer.model_max_length = 512
    mock_tokenizer.num_special_tokens_to_add = lambda pair=False: 0

    provider = RecognizerRegistryProvider(
        registry_configuration={
            "supported_languages": ["en"],
            "global_regex_flags": 26,
            "recognizers": [
                {
                    "name": "HF NER",
                    "type": "predefined",
                    "class_name": "HuggingFaceNerRecognizer",
                    "model_name": "dslim/bert-base-NER",
                    "supported_languages": ["en"],
                    "supported_entities": ["PERSON"],
                    "device": "cpu",
                    "text_chunker": {
                        "chunker_type": "tokenizer",
                        "tokenizer": mock_tokenizer,
                        "max_tokens": 256,
                        "overlap_tokens": 16,
                    },
                }
            ],
        }
    )
    registry = provider.create_recognizer_registry()

    hf_recognizers = [
        r for r in registry.recognizers
        if isinstance(r, HuggingFaceNerRecognizer)
    ]
    assert len(hf_recognizers) == 1

    recognizer = hf_recognizers[0]
    assert isinstance(recognizer.text_chunker, TokenizerBasedTextChunker)
    assert recognizer.text_chunker.max_tokens == 256
    assert recognizer.text_chunker.overlap_tokens == 16


def test_text_chunker_config_rejects_tokenizer_params_for_character():
    """Character chunker_type must not accept tokenizer-only params."""
    from pydantic import ValidationError
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        TextChunkerConfig,
    )

    with pytest.raises(ValidationError, match="chunker_type='character'"):
        TextChunkerConfig(chunker_type="character", max_tokens=256)


def test_text_chunker_config_rejects_character_params_for_tokenizer():
    """Tokenizer chunker_type must not accept character-only params."""
    from pydantic import ValidationError
    from presidio_analyzer.input_validation.yaml_recognizer_models import (
        TextChunkerConfig,
    )

    with pytest.raises(ValidationError, match="chunker_type='tokenizer'"):
        TextChunkerConfig(chunker_type="tokenizer", chunk_size=300)
