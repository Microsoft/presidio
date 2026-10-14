# ruff: noqa: D103,D205,E501,F541,F841,W293

import importlib.util
import os
import re
from pathlib import Path
from typing import List
from unittest.mock import patch

import pytest
import yaml
from install_nlp_models import _install_models_from_nlp_config, install_models
from presidio_analyzer import AnalyzerEngineProvider, RecognizerResult
from presidio_analyzer.nlp_engine import NlpArtifacts, SpacyNlpEngine
from presidio_analyzer.predefined_recognizers import (
    AzureAILanguageRecognizer,
    CreditCardRecognizer,
    SpacyRecognizer,
    StanzaRecognizer,
)

def _has_module(name: str) -> bool:
    # find_spec imports the parent packages of a dotted name, so a missing
    # intermediate raises ModuleNotFoundError instead of returning None --
    # "azure.health.deidentification" does exactly that without the ahds extra.
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


# Gate the optional-dependency tests below on the module each one actually
# imports. `pytest.importorskip` cannot be used for this: evaluated inside a
# decorator it runs at module import, so a missing extra takes the whole file
# out of collection instead of skipping the two tests that need it.
#
# The bare `azure` name is also too coarse. `azure.*` are namespace packages and
# the `ahds` extra populates them too, so `import azure` can succeed while
# `azure.ai.textanalytics` is absent.
_HAS_TEXT_ANALYTICS = _has_module("azure.ai.textanalytics")
_HAS_HEALTH_DEID = _has_module("azure.health.deidentification")


def get_full_paths(analyzer_yaml, nlp_engine_yaml=None, recognizer_registry_yaml=None):
    this_path = Path(__file__).parent.absolute()

    analyzer_yaml_path = Path(this_path, analyzer_yaml) if analyzer_yaml else None
    nlp_engine_yaml_path = Path(this_path, nlp_engine_yaml) if nlp_engine_yaml else None
    recognizer_registry_yaml_path = (
        Path(this_path, recognizer_registry_yaml) if recognizer_registry_yaml else None
    )
    return analyzer_yaml_path, nlp_engine_yaml_path, recognizer_registry_yaml_path


def test_analyzer_engine_provider_default_configuration(mandatory_recognizers):
    provider = AnalyzerEngineProvider()
    engine = provider.create_engine()
    assert engine.supported_languages == ["en"]
    assert (
        engine.registry.global_regex_flags == re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    assert engine.default_score_threshold == 0
    assert all(
        recognizer.score_thresholds == {}
        for recognizer in engine.registry.recognizers
    )
    names = [recognizer.name for recognizer in engine.registry.recognizers]
    for predefined_recognizer in mandatory_recognizers:
        assert predefined_recognizer in names
    assert "SpacyRecognizer" in names
    assert isinstance(engine.nlp_engine, SpacyNlpEngine)
    assert engine.nlp_engine.engine_name == "spacy"


def test_analyzer_engine_provider_configuration_file():
    test_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")
    provider = AnalyzerEngineProvider(test_yaml)
    engine = provider.create_engine()
    assert engine.supported_languages == ["de", "en", "es"]
    assert engine.default_score_threshold == 0.7
    recognizer_registry = engine.registry
    assert (
        recognizer_registry.global_regex_flags
        == re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    assert len(recognizer_registry.recognizers) == 8
    assert [
        recognizer.supported_language
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "ItFiscalCodeRecognizer"
    ] == ["de", "en", "es"]
    assert [
        recognizer.supported_language
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "CreditCardRecognizer"
    ] == ["en"]
    assert [
        recognizer.supported_language
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "ZipCodeRecognizer"
    ] == ["de"]
    assert [
        recognizer.supported_language
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "ExampleCustomRecognizer"
    ] == ["en", "es"]
    assert sorted(
        [
            recognizer.supported_language
            for recognizer in recognizer_registry.recognizers
            if recognizer.name == "SpacyRecognizer"
        ]
    ) == sorted(["en"])
    spanish_recognizer = [
        recognizer
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "ExampleCustomRecognizer"
        and recognizer.supported_language == "es"
    ][0]
    assert spanish_recognizer.context == ["tarjeta", "credito"]
    credit_card = next(
        recognizer
        for recognizer in recognizer_registry.recognizers
        if recognizer.name == "CreditCardRecognizer"
    )
    assert credit_card.score_thresholds == {
        "default": 0.4,
        "CREDIT_CARD": 0.7,
    }
    assert isinstance(engine.nlp_engine, SpacyNlpEngine)
    assert engine.nlp_engine.engine_name == "spacy"


def test_analyzer_engine_provider_inline_recognizer_thresholds_affect_output(tmp_path):
    analyzer_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")

    with open(analyzer_yaml) as file:
        configuration = yaml.safe_load(file)

    configuration["default_score_threshold"] = 0.9
    credit_card = configuration["recognizer_registry"]["recognizers"][0]
    credit_card["score_thresholds"] = {"default": 0.4}

    threshold_yaml = tmp_path / "analyzer_with_thresholds.yaml"
    threshold_yaml.write_text(yaml.safe_dump(configuration, sort_keys=False))

    provider = AnalyzerEngineProvider(threshold_yaml)
    engine = provider.create_engine()

    loaded_credit_card = next(
        recognizer
        for recognizer in engine.registry.recognizers
        if recognizer.name == "CreditCardRecognizer"
    )
    assert loaded_credit_card.score_thresholds == {"default": 0.4}

    results = engine.analyze(
        text=" Credit card: 4095-2609-9393-4932",
        language="en",
        entities=["CREDIT_CARD"],
    )

    assert len(results) == 1


def test_analyzer_engine_provider_external_registry_thresholds_affect_output(tmp_path):
    analyzer_yaml = tmp_path / "analyzer.yaml"
    analyzer_yaml.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "default_score_threshold": 0.9,
                "nlp_configuration": {
                    "nlp_engine_name": "spacy",
                    "models": [
                        {"lang_code": "en", "model_name": "en_core_web_lg"}
                    ],
                },
            }
        )
    )
    registry_yaml = tmp_path / "registry.yaml"
    registry_yaml.write_text(
        yaml.safe_dump(
            {
                "supported_languages": ["en"],
                "recognizers": [
                    {
                        "name": "RocketRecognizer",
                        "type": "custom",
                        "supported_entity": "ROCKET",
                        "supported_language": "en",
                        "patterns": [
                            {"name": "rocket", "regex": "rocket", "score": 0.5}
                        ],
                        "score_thresholds": {"default": 0.4},
                    }
                ],
            }
        )
    )
    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=analyzer_yaml,
        recognizer_registry_conf_file=registry_yaml,
    )

    engine = provider.create_engine()
    results = engine.analyze("rocket", "en", entities=["ROCKET"])

    assert [result.entity_type for result in results] == ["ROCKET"]


def test_analyzer_engine_provider_defaults(mandatory_recognizers):
    provider = AnalyzerEngineProvider()
    engine = provider.create_engine()
    assert engine.supported_languages == ["en"]
    assert engine.default_score_threshold == 0
    assert all(
        recognizer.score_thresholds == {}
        for recognizer in engine.registry.recognizers
    )
    recognizer_registry = engine.registry
    assert (
        recognizer_registry.global_regex_flags
        == re.DOTALL | re.MULTILINE | re.IGNORECASE
    )
    assert recognizer_registry.supported_languages == ["en"]
    names = [recognizer.name for recognizer in recognizer_registry.recognizers]
    for predefined_recognizer in mandatory_recognizers:
        assert predefined_recognizer in names
    assert isinstance(engine.nlp_engine, SpacyNlpEngine)
    assert engine.nlp_engine.engine_name == "spacy"


def test_analyzer_engine_provider_with_files_per_provider():
    analyzer_yaml, nlp_engine_yaml, recognizer_registry_yaml = get_full_paths(
        "conf/simple_analyzer_engine.yaml",
        "conf/default.yaml",
        "conf/test_recognizer_registry.yaml",
    )

    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=analyzer_yaml,
        nlp_engine_conf_file=nlp_engine_yaml,
        recognizer_registry_conf_file=recognizer_registry_yaml,
    )

    analyzer_engine = provider.create_engine()

    # assert analyzer instance is correct
    assert analyzer_engine.supported_languages == ["en", "es"]
    assert analyzer_engine.default_score_threshold == 0.43

    # assert nlp engine is correct
    nlp_engine = analyzer_engine.nlp_engine
    assert isinstance(nlp_engine, SpacyNlpEngine)
    assert nlp_engine.nlp is not None
    assert nlp_engine.get_supported_languages() == ["en"]

    # assert recognizer registry is correct
    recognizer_registry = analyzer_engine.registry
    assert len(recognizer_registry.recognizers) == 6
    assert recognizer_registry.supported_languages == ["en", "es"]


@pytest.mark.skipif(
    not _HAS_TEXT_ANALYTICS, reason="azure-ai-language extra not installed"
)
def test_analyzer_engine_provider_with_azure_ai_language(monkeypatch):
    # The constructor builds a client when none is injected, falling back to
    # these variables. Nothing here reaches the network: the SDK client is
    # constructed locally and `analyze` is overridden below.
    monkeypatch.setenv("AZURE_AI_KEY", "test-key")
    monkeypatch.setenv("AZURE_AI_ENDPOINT", "https://example.invalid/")

    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_azure_ai_language_reco.yaml",
    )

    class MockAzureAiLanguageRecognizer(AzureAILanguageRecognizer):
        def analyze(
            self,
            text: str,
            entities: List[str] = None,
            nlp_artifacts: NlpArtifacts = None,
        ) -> List[RecognizerResult]:
            return [RecognizerResult(entity_type="PERSON", start=0, end=4, score=0.9)]

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    names = {
        rec.name
        for rec in analyzer_engine.registry.recognizers
        if isinstance(rec, MockAzureAiLanguageRecognizer)
    }

    # The plain entry takes its name from the YAML key; the `class_name` entry
    # takes the name configured next to it. Both require the constructor to
    # accept `name`, which is what regressed after #1800.
    assert names == {"MockAzureAiLanguageRecognizer", "Azure AI Language PII"}

    assert len(analyzer_engine.analyze("This is a test", language="en")) > 0


# AzureHealthDeidRecognizer.__init__ builds a client when none is passed, and
# that path reads AHDS_ENDPOINT and raises ValueError without it. The YAML entry
# supplies no client, so the endpoint is as much a precondition as the package.
@pytest.mark.skipif(
    not _HAS_HEALTH_DEID or not os.getenv("AHDS_ENDPOINT"),
    reason="ahds extra not installed or AHDS_ENDPOINT not set",
)
def test_analyzer_engine_provider_with_ahds():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_ahds_reco.yaml",
    )
    from presidio_analyzer.predefined_recognizers import AzureHealthDeidRecognizer

    class MockAHDSDeidRecognizer(AzureHealthDeidRecognizer):
        def analyze(
            self,
            text: str,
            entities: List[str] = None,
            nlp_artifacts: NlpArtifacts = None,
        ) -> List[RecognizerResult]:
            return [RecognizerResult(entity_type="PATIENT", start=0, end=4, score=0.9)]

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    ahds_recognizers = [
        rec
        for rec in analyzer_engine.registry.recognizers
        if rec.name == "Azure Health Data Services de-identification"
    ]

    assert len(ahds_recognizers) == 1

    assert len(analyzer_engine.analyze("This is a test", language="en")) > 0
    


def test_analyzer_engine_provider_no_nlp_recognizer():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_nlp_reco_disabled_conf.yaml",
    )

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    assert len(analyzer_engine.get_recognizers()) == 1
    recognizer = analyzer_engine.get_recognizers()[0]
    assert isinstance(recognizer, CreditCardRecognizer)

    assert len(analyzer_engine.analyze("My Credit card number is 4917300800000000", language="en")) > 0


def test_analyzer_engine_provider_no_nlp_recognizer_is_added():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_no_nlp_reco_conf.yaml",
    )
    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    assert len(analyzer_engine.get_recognizers()) == 2
    nlp_recognizer = [
        rec
        for rec in analyzer_engine.get_recognizers()
        if isinstance(rec, SpacyRecognizer)
    ]
    assert len(nlp_recognizer) == 1


def test_analyzer_engine_provider_no_nlp_recognizer_is_added_per_language():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_no_nlp_reco_conf_multilingual.yaml",
    )
    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    assert len(analyzer_engine.get_recognizers()) == 4 # Two CreditCardRecognizers and two SpacyRecognizers
    nlp_recognizers = [
        rec
        for rec in analyzer_engine.get_recognizers()
        if isinstance(rec, SpacyRecognizer)
    ]
    assert len(nlp_recognizers) == 2  # one per language
    assert set([rec.supported_language for rec in nlp_recognizers]) == {"en", "es"}


def test_analyzer_engine_provider_mismatch_between_nlp_engine_and_nlp_recognizer():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_nlp_reco_does_not_match_engine.yaml",
    )

    with pytest.raises(ValueError):
        provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
        analyzer_engine = provider.create_engine()


def test_analyzer_engine_provider_multiple_nlp_recognizers_raises_exception():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_multiple_nlp_recognizers.yaml",
    )

    with pytest.raises(
        ValueError,
        match=f"Multiple NLP recognizers for language en found in the configuration. "
                f"Please remove the duplicates."):
        provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
        analyzer_engine = provider.create_engine()


def test_analyzer_engine_provider_no_nlp_engine_or_provider_results_in_default_nlp_recognizer():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_no_nlp_engine.yaml",
    )
    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    assert len(analyzer_engine.get_recognizers()) == 2 # SpacyRecognizer, CreditCardRecognizer
    nlp_recognizer = [
        rec
        for rec in analyzer_engine.get_recognizers()
        if isinstance(rec, SpacyRecognizer)
    ]
    assert len(nlp_recognizer) == 1


@pytest.mark.skip_engine("stanza_en")
def test_analyzer_engine_stanza_without_recognizer_creates_recognizer():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/test_stanza_without_recognizer.yaml",
    )
    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()

    assert (
        len(analyzer_engine.get_recognizers()) == 3
    )  # StanzaRecognizer en, StanzaRecognizer es, CreditCardRecognizer
    nlp_recognizers = [
        rec
        for rec in analyzer_engine.get_recognizers()
        if isinstance(rec, StanzaRecognizer)
    ]
    assert len(nlp_recognizers) == 2
    supported_languages = {
        nlp_recognizers[0].supported_language,
        nlp_recognizers[1].supported_language,
    }
    assert supported_languages == {"en", "es"}

def test_analyzer_engine_provider_one_custom_recognizer():
    analyzer_yaml, _, _ = get_full_paths(
        "conf/custom_recognizer_yaml.yaml",
    )
    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)

    analyzer_engine = provider.create_engine()
    assert len(analyzer_engine.get_recognizers()) == 1
    assert analyzer_engine.analyze("My zip code is 12345", language="en")[0].score == pytest.approx(0.4)


def test_analyzer_engine_provider_invalid_analyzer_conf_file():
    """Test that invalid analyzer configuration file path raises error."""
    with pytest.raises(ValueError):
        AnalyzerEngineProvider(analyzer_engine_conf_file="/nonexistent/path/file.yaml")


def test_analyzer_engine_provider_invalid_nlp_conf_file():
    """Test that invalid NLP engine configuration file path raises error."""
    with pytest.raises(ValueError):
        AnalyzerEngineProvider(nlp_engine_conf_file="/nonexistent/path/file.yaml")


def test_analyzer_engine_provider_invalid_registry_conf_file():
    """Test that invalid recognizer registry configuration file path raises error."""
    with pytest.raises(ValueError):
        AnalyzerEngineProvider(recognizer_registry_conf_file="/nonexistent/path/file.yaml")


def test_analyzer_engine_provider_get_configuration_with_nonexistent_file():
    """Test get_configuration falls back to default when file doesn't exist."""
    provider = AnalyzerEngineProvider()

    # Test with nonexistent file - should fall back to default
    config = provider.get_configuration("/tmp/nonexistent_config_file_12345.yaml")

    # Should return a valid configuration (the default one)
    assert config is not None
    assert isinstance(config, dict)


def test_analyzer_engine_provider_get_configuration_with_invalid_yaml():
    """Test get_configuration handles invalid YAML gracefully."""
    import os
    import tempfile

    # Create a temporary file with invalid YAML
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write("invalid: yaml: content: [[[")
        temp_file = f.name

    try:
        provider = AnalyzerEngineProvider()
        config = provider.get_configuration(temp_file)

        # Should fall back to default configuration
        assert config is not None
        assert isinstance(config, dict)
    finally:
        os.unlink(temp_file)


def test_analyzer_engine_provider_get_full_conf_path():
    """Test _get_full_conf_path static method."""
    from pathlib import Path

    path = AnalyzerEngineProvider._get_full_conf_path()

    assert isinstance(path, Path)
    assert path.name == "default_analyzer.yaml"
    assert path.exists()


def test_analyzer_engine_provider_get_full_conf_path_custom_file():
    """Test _get_full_conf_path with custom filename."""
    from pathlib import Path

    path = AnalyzerEngineProvider._get_full_conf_path("custom_file.yaml")

    assert isinstance(path, Path)
    assert path.name == "custom_file.yaml"


def test_analyzer_engine_provider_configuration_property():
    """Test that configuration property is set correctly."""
    provider = AnalyzerEngineProvider()

    assert provider.configuration is not None
    assert isinstance(provider.configuration, dict)


def test_analyzer_engine_provider_nlp_engine_conf_file_property():
    """Test that nlp_engine_conf_file property is stored correctly."""
    test_yaml, nlp_yaml, _ = get_full_paths(
        "conf/simple_analyzer_engine.yaml",
        "conf/default.yaml",
    )

    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=test_yaml,
        nlp_engine_conf_file=nlp_yaml,
    )

    assert provider.nlp_engine_conf_file == nlp_yaml


def test_analyzer_engine_provider_recognizer_registry_conf_file_property():
    """Test that recognizer_registry_conf_file property is stored correctly."""
    test_yaml, _, registry_yaml = get_full_paths(
        "conf/simple_analyzer_engine.yaml",
        None,
        "conf/test_recognizer_registry.yaml",
    )

    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=test_yaml,
        recognizer_registry_conf_file=registry_yaml,
    )

    assert provider.recognizer_registry_conf_file == registry_yaml


def test_analyzer_engine_provider_load_nlp_engine_from_conf():
    """Test _load_nlp_engine with nlp_configuration in analyzer config."""
    analyzer_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
    nlp_engine = provider._load_nlp_engine()

    assert nlp_engine is not None
    assert nlp_engine.engine_name == "spacy"


def test_analyzer_engine_provider_load_nlp_engine_default():
    """Test _load_nlp_engine falls back to default when no config provided."""
    provider = AnalyzerEngineProvider()
    nlp_engine = provider._load_nlp_engine()

    assert nlp_engine is not None
    assert isinstance(nlp_engine, SpacyNlpEngine)


def test_analyzer_engine_provider_load_recognizer_registry_from_embedded_config():
    """Test _load_recognizer_registry with embedded recognizer_registry in config."""
    analyzer_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
    nlp_engine = provider._load_nlp_engine()

    registry = provider._load_recognizer_registry(
        supported_languages=["en"],
        nlp_engine=nlp_engine,
    )

    assert registry is not None
    assert len(registry.recognizers) > 0


def test_analyzer_engine_provider_load_recognizer_registry_default():
    """Test _load_recognizer_registry uses default when no config provided."""
    provider = AnalyzerEngineProvider()
    nlp_engine = provider._load_nlp_engine()

    registry = provider._load_recognizer_registry(
        supported_languages=["en"],
        nlp_engine=nlp_engine,
    )

    assert registry is not None
    assert len(registry.recognizers) > 0


def test_analyzer_engine_provider_create_engine_with_all_params():
    """Test create_engine with all configuration parameters."""
    analyzer_yaml, nlp_yaml, registry_yaml = get_full_paths(
        "conf/simple_analyzer_engine.yaml",
        "conf/default.yaml",
        "conf/test_recognizer_registry.yaml",
    )

    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=analyzer_yaml,
        nlp_engine_conf_file=nlp_yaml,
        recognizer_registry_conf_file=registry_yaml,
    )

    engine = provider.create_engine()

    assert engine is not None
    assert engine.nlp_engine is not None
    assert engine.registry is not None
    assert len(engine.supported_languages) > 0


def test_analyzer_engine_provider_inline_sections_take_priority_over_per_section_files():
    """Test that nlp_configuration / recognizer_registry sections embedded in the
    analyzer conf file take priority over separately provided per-section files.

    This is the key behaviour that lets a single unified ANALYZER_CONF_FILE drive
    both NLP and registry configuration without being silently overridden by
    Dockerfile-baked-in default values for NLP_CONF_FILE and
    RECOGNIZER_REGISTRY_CONF_FILE.
    """
    # test_analyzer_engine.yaml contains both nlp_configuration and
    # recognizer_registry sections.
    analyzer_yaml, nlp_yaml, registry_yaml = get_full_paths(
        "conf/test_analyzer_engine.yaml",
        "conf/default.yaml",
        "conf/test_recognizer_registry.yaml",
    )

    provider = AnalyzerEngineProvider(
        analyzer_engine_conf_file=analyzer_yaml,
        nlp_engine_conf_file=nlp_yaml,
        recognizer_registry_conf_file=registry_yaml,
    )
    engine = provider.create_engine()

    # The analyzer yaml's supported_languages + recognizer_registry should prevail.
    # test_analyzer_engine.yaml lists de, en, es — not the registry-only en.
    assert "de" in engine.supported_languages
    assert "en" in engine.supported_languages
    assert "es" in engine.supported_languages

    # The registry from the inline section has more than the 6 recognizers
    # in test_recognizer_registry.yaml, confirming the inline section won.
    assert len(engine.registry.recognizers) > 6
    credit_card = next(
        recognizer
        for recognizer in engine.registry.recognizers
        if recognizer.name == "CreditCardRecognizer"
    )
    assert credit_card.score_thresholds == {
        "default": 0.4,
        "CREDIT_CARD": 0.7,
    }


def test_analyzer_engine_provider_multiple_languages_support():
    """Test analyzer engine with multiple language support."""
    analyzer_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
    engine = provider.create_engine()

    assert "en" in engine.supported_languages
    assert "de" in engine.supported_languages
    assert "es" in engine.supported_languages


def test_analyzer_engine_provider_default_score_threshold():
    """Test that default_score_threshold is properly set."""
    analyzer_yaml, _, _ = get_full_paths("conf/test_analyzer_engine.yaml")

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_yaml)
    engine = provider.create_engine()

    assert engine.default_score_threshold == 0.7


def test_analyzer_engine_provider_with_pathlib_path():
    """Test AnalyzerEngineProvider works with pathlib.Path objects."""
    from pathlib import Path

    analyzer_yaml, _, _ = get_full_paths("conf/simple_analyzer_engine.yaml")
    analyzer_path = Path(analyzer_yaml)

    provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_path)
    engine = provider.create_engine()

    assert engine is not None


def test_analyzer_engine_provider_configuration_logging(caplog):
    """Test that configuration loading logs appropriate messages."""
    import logging

    with caplog.at_level(logging.INFO):
        provider = AnalyzerEngineProvider()
        _ = provider.create_engine()

    # Check that some logging occurred
    assert len(caplog.records) > 0




# --- install_models / _install_models_from_nlp_config tests ---

_NLP_CONF_CONTENT = (
    "nlp_engine_name: spacy\n"
    "models:\n"
    "  - lang_code: en\n"
    "    model_name: en_core_web_sm\n"
)

_ANALYZER_CONF_WITH_NLP = (
    "nlp_configuration:\n"
    "  nlp_engine_name: spacy\n"
    "  models:\n"
    "    - lang_code: en\n"
    "      model_name: en_core_web_lg\n"
)

_ANALYZER_CONF_WITHOUT_NLP = "supported_languages:\n  - en\n"


def test_install_models_only_analyzer_conf_with_nlp_configuration(tmp_path):
    """analyzer_conf_file with nlp_configuration — uses analyzer's NLP config."""
    analyzer_yaml = tmp_path / "analyzer.yaml"
    analyzer_yaml.write_text(_ANALYZER_CONF_WITH_NLP)

    with patch("install_nlp_models._download_model") as mock_dl:
        install_models(analyzer_conf_file=str(analyzer_yaml))

    mock_dl.assert_called_once_with("spacy", "en_core_web_lg")


def test_install_models_analyzer_conf_without_nlp_falls_back_to_nlp_conf(tmp_path):
    """analyzer_conf_file without nlp_configuration — falls back to nlp_conf_file."""
    analyzer_yaml = tmp_path / "analyzer.yaml"
    analyzer_yaml.write_text(_ANALYZER_CONF_WITHOUT_NLP)
    nlp_yaml = tmp_path / "nlp.yaml"
    nlp_yaml.write_text(_NLP_CONF_CONTENT)

    with patch("install_nlp_models._download_model") as mock_dl:
        install_models(nlp_conf_file=str(nlp_yaml), analyzer_conf_file=str(analyzer_yaml))

    mock_dl.assert_called_once_with("spacy", "en_core_web_sm")


def test_install_models_only_nlp_conf_file(tmp_path):
    """Only nlp_conf_file provided — reads and installs from it directly."""
    nlp_yaml = tmp_path / "nlp.yaml"
    nlp_yaml.write_text(_NLP_CONF_CONTENT)

    with patch("install_nlp_models._download_model") as mock_dl:
        install_models(nlp_conf_file=str(nlp_yaml))

    mock_dl.assert_called_once_with("spacy", "en_core_web_sm")


def test_install_models_analyzer_conf_takes_priority_over_nlp_conf(tmp_path):
    """Both files provided and analyzer_conf_file has nlp_configuration — analyzer wins."""
    analyzer_yaml = tmp_path / "analyzer.yaml"
    analyzer_yaml.write_text(_ANALYZER_CONF_WITH_NLP)
    nlp_yaml = tmp_path / "nlp.yaml"
    nlp_yaml.write_text(_NLP_CONF_CONTENT)

    with patch("install_nlp_models._download_model") as mock_dl:
        install_models(nlp_conf_file=str(nlp_yaml), analyzer_conf_file=str(analyzer_yaml))

    mock_dl.assert_called_once_with("spacy", "en_core_web_lg")


def test_install_models_nonexistent_analyzer_conf_raises_os_error(tmp_path):
    """Nonexistent analyzer_conf_file raises OSError."""
    with pytest.raises(OSError):
        install_models(analyzer_conf_file=str(tmp_path / "missing.yaml"))


def test_install_models_nonexistent_nlp_conf_raises_os_error(tmp_path):
    """Nonexistent nlp_conf_file raises OSError."""
    with pytest.raises(OSError):
        install_models(nlp_conf_file=str(tmp_path / "missing.yaml"))


def test_install_models_from_nlp_config_missing_engine_name_raises_value_error():
    """nlp_configuration without nlp_engine_name raises ValueError."""
    with pytest.raises(ValueError, match="nlp_engine_name"):
        _install_models_from_nlp_config({"models": [{"model_name": "en_core_web_sm"}]})


def test_install_models_from_nlp_config_missing_models_raises_value_error():
    """nlp_configuration without models raises ValueError."""
    with pytest.raises(ValueError, match="models"):
        _install_models_from_nlp_config({"nlp_engine_name": "spacy"})
