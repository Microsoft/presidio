from typing import Iterator

import pytest

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from presidio_analyzer.nlp_engine import (
    NlpEngineProvider,
    SlimSpacyNlpEngine,
)
from presidio_analyzer.nlp_engine.slim_spacy_nlp_engine import DEFAULT_SLIM_MODELS
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.recognizer_registry import (
    RecognizerRegistry,
    RecognizerRegistryProvider,
)


@pytest.fixture(scope="module")
def slim_nlp_engine():
    """Create and load a slim NLP engine for English."""
    engine = SlimSpacyNlpEngine(
        models=[{"lang_code": "en", "model_name": "en_core_web_sm"}]
    )
    engine.load()
    return engine


class TestSlimSpacyNlpEngineInit:
    """Tests for SlimSpacyNlpEngine initialization."""

    def test_when_init_with_default_then_english_model_configured(self):
        engine = SlimSpacyNlpEngine()
        assert len(engine.models) == 1
        assert engine.models[0]["lang_code"] == "en"
        assert engine.models[0]["model_name"] == "en_core_web_sm"

    def test_when_init_with_explicit_models_then_models_used(self):
        models = [{"lang_code": "en", "model_name": "en_core_web_sm"}]
        engine = SlimSpacyNlpEngine(models=models)
        assert engine.models == models

    def test_when_init_with_supported_languages_then_default_models_selected(self):
        engine = SlimSpacyNlpEngine(supported_languages=["en", "es"])
        assert len(engine.models) == 2
        assert engine.models[0] == {"lang_code": "en", "model_name": "en_core_web_sm"}
        assert engine.models[1] == {
            "lang_code": "es",
            "model_name": "es_core_news_sm",
        }

    def test_when_init_with_unsupported_language_then_raises(self):
        with pytest.raises(ValueError, match="No default slim model"):
            SlimSpacyNlpEngine(supported_languages=["xx_unsupported"])

    def test_when_init_with_unsupported_language_and_blank_fallback(self):
        engine = SlimSpacyNlpEngine(
            supported_languages=["sw"], generic_tokenizer="blank"
        )
        assert len(engine.models) == 0
        assert "sw" in engine._blank_languages

    def test_when_init_with_unsupported_language_and_model_fallback(self):
        engine = SlimSpacyNlpEngine(
            supported_languages=["sw"], generic_tokenizer="xx_ent_wiki_sm"
        )
        assert engine.models[0] == {
            "lang_code": "sw",
            "model_name": "xx_ent_wiki_sm",
        }

    def test_when_init_with_mixed_languages_and_fallback(self):
        engine = SlimSpacyNlpEngine(
            supported_languages=["en", "sw"], generic_tokenizer="blank"
        )
        assert len(engine.models) == 1
        assert engine.models[0]["model_name"] == "en_core_web_sm"
        assert "sw" in engine._blank_languages

    def test_when_models_and_languages_both_given_then_models_takes_precedence(self):
        models = [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        engine = SlimSpacyNlpEngine(
            models=models, supported_languages=["es"]
        )
        # models parameter takes precedence
        assert engine.models == models

    def test_when_engine_name_then_slim(self):
        assert SlimSpacyNlpEngine.engine_name == "slim"

    def test_when_is_available_then_true(self):
        assert SlimSpacyNlpEngine.is_available is True

    def test_when_auto_download_default_then_true(self):
        engine = SlimSpacyNlpEngine()
        assert engine.auto_download is True

    def test_when_auto_download_false_then_false(self):
        engine = SlimSpacyNlpEngine(auto_download=False)
        assert engine.auto_download is False


class TestSlimSpacyNlpEngineLoad:
    """Tests for loading the slim engine."""

    def test_when_load_then_nlp_populated(self, slim_nlp_engine):
        assert slim_nlp_engine.nlp is not None
        assert "en" in slim_nlp_engine.nlp

    def test_when_load_then_ner_disabled(self, slim_nlp_engine):
        nlp = slim_nlp_engine.nlp["en"]
        pipe_names = nlp.pipe_names
        assert "ner" not in pipe_names

    def test_when_load_then_parser_disabled(self, slim_nlp_engine):
        nlp = slim_nlp_engine.nlp["en"]
        pipe_names = nlp.pipe_names
        assert "parser" not in pipe_names

    def test_when_load_blank_model_then_tokenization_works(self):
        engine = SlimSpacyNlpEngine(
            supported_languages=["fi"], generic_tokenizer="blank"
        )
        engine.load()
        assert engine.is_loaded()
        artifacts = engine.process_text("hello world", language="fi")
        assert len(artifacts.tokens) == 2
        assert artifacts.entities == []

    def test_when_load_blank_unknown_language_then_falls_back_to_xx(self):
        engine = SlimSpacyNlpEngine(
            supported_languages=["sw"], generic_tokenizer="blank"
        )
        engine.load()
        assert engine.is_loaded()
        artifacts = engine.process_text("hello world", language="sw")
        assert len(artifacts.tokens) == 2
        assert artifacts.entities == []

    def test_when_is_loaded_before_load_then_false(self):
        engine = SlimSpacyNlpEngine()
        assert engine.is_loaded() is False

    def test_when_is_loaded_after_load_then_true(self, slim_nlp_engine):
        assert slim_nlp_engine.is_loaded() is True

    def test_when_load_with_invalid_model_then_raises(self):
        engine = SlimSpacyNlpEngine(
            models=[{"lang_code": "en", "model_name": "nonexistent_model_xyz"}],
            auto_download=False,
        )
        with pytest.raises(OSError):
            engine.load()

    def test_when_validate_model_params_missing_lang_code_then_raises(self):
        with pytest.raises(ValueError, match="lang_code"):
            SlimSpacyNlpEngine._validate_model_params(
                {"model_name": "en_core_web_sm"}
            )

    def test_when_validate_model_params_missing_model_name_then_raises(self):
        with pytest.raises(ValueError, match="model_name"):
            SlimSpacyNlpEngine._validate_model_params({"lang_code": "en"})

    def test_when_validate_model_params_non_string_model_then_raises(self):
        with pytest.raises(ValueError, match="model_name must be a string"):
            SlimSpacyNlpEngine._validate_model_params(
                {"lang_code": "en", "model_name": 123}
            )


class TestSlimSpacyNlpEngineProcessText:
    """Tests for process_text method."""

    def test_when_process_text_then_tokens_returned(self, slim_nlp_engine):
        artifacts = slim_nlp_engine.process_text("simple text", language="en")
        assert len(artifacts.tokens) == 2

    def test_when_process_text_then_no_entities(self, slim_nlp_engine):
        text = "John Smith lives in New York and works at Microsoft"
        artifacts = slim_nlp_engine.process_text(text, language="en")
        assert artifacts.entities == []
        assert artifacts.scores == []

    def test_when_process_text_then_lemmas_returned(self, slim_nlp_engine):
        artifacts = slim_nlp_engine.process_text("running quickly", language="en")
        assert len(artifacts.lemmas) == 2
        # "running" should be lemmatized
        assert artifacts.lemmas[0] == "run"

    def test_when_process_text_then_tokens_indices_returned(self, slim_nlp_engine):
        artifacts = slim_nlp_engine.process_text("hello world", language="en")
        assert len(artifacts.tokens_indices) == 2
        assert artifacts.tokens_indices[0] == 0
        assert artifacts.tokens_indices[1] == 6

    def test_when_process_text_then_nlp_engine_set(self, slim_nlp_engine):
        artifacts = slim_nlp_engine.process_text("test", language="en")
        assert artifacts.nlp_engine is slim_nlp_engine

    def test_when_not_loaded_then_process_text_raises(self):
        engine = SlimSpacyNlpEngine()
        with pytest.raises(ValueError, match="not loaded"):
            engine.process_text("test", language="en")

    def test_when_unsupported_language_then_process_text_raises(self, slim_nlp_engine):
        with pytest.raises(ValueError, match="not supported"):
            slim_nlp_engine.process_text("test", language="fr")

    def test_when_process_empty_text_then_returns_artifacts(self, slim_nlp_engine):
        artifacts = slim_nlp_engine.process_text("", language="en")
        assert len(artifacts.tokens) == 0
        assert artifacts.entities == []


class TestSlimSpacyNlpEngineProcessBatch:
    """Tests for process_batch method."""

    def test_when_process_batch_then_returns_iterator(self, slim_nlp_engine):
        results = slim_nlp_engine.process_batch(
            ["hello", "world"], language="en"
        )
        assert isinstance(results, Iterator)

    def test_when_process_batch_strings_then_text_and_artifacts(self, slim_nlp_engine):
        results = list(
            slim_nlp_engine.process_batch(["simple text", "another"], language="en")
        )
        assert len(results) == 2
        text, artifacts = results[0]
        assert text == "simple text"
        assert len(artifacts.tokens) == 2
        assert artifacts.entities == []

    def test_when_process_batch_as_tuples_then_context_preserved(
        self, slim_nlp_engine
    ):
        inputs = [("hello world", {"id": 1}), ("test text", {"id": 2})]
        results = list(
            slim_nlp_engine.process_batch(inputs, language="en", as_tuples=True)
        )
        assert len(results) == 2
        text, artifacts, context = results[0]
        assert text == "hello world"
        assert context == {"id": 1}
        assert artifacts.entities == []

    def test_when_process_batch_not_loaded_then_raises(self):
        engine = SlimSpacyNlpEngine()
        with pytest.raises(ValueError, match="not loaded"):
            list(engine.process_batch(["test"], language="en"))

    def test_when_process_batch_invalid_tuples_then_raises(self, slim_nlp_engine):
        with pytest.raises(ValueError, match="tuples"):
            list(
                slim_nlp_engine.process_batch(
                    ["not a tuple"], language="en", as_tuples=True
                )
            )


class TestSlimSpacyNlpEngineLinguisticUtils:
    """Tests for stopword and punctuation detection."""

    def test_when_stopword_then_returns_true(self, slim_nlp_engine):
        assert slim_nlp_engine.is_stopword("the", language="en") is True

    def test_when_not_stopword_then_returns_false(self, slim_nlp_engine):
        assert slim_nlp_engine.is_stopword("microsoft", language="en") is False

    def test_when_punct_then_returns_true(self, slim_nlp_engine):
        assert slim_nlp_engine.is_punct(".", language="en") is True

    def test_when_not_punct_then_returns_false(self, slim_nlp_engine):
        assert slim_nlp_engine.is_punct("hello", language="en") is False


class TestSlimSpacyNlpEngineSupportedEntitiesAndLanguages:
    """Tests for supported entities and languages."""

    def test_has_ner_is_false(self, slim_nlp_engine):
        assert slim_nlp_engine.has_ner is False

    def test_when_get_supported_entities_then_empty(self, slim_nlp_engine):
        assert slim_nlp_engine.get_supported_entities() == []

    def test_when_get_supported_languages_then_returns_loaded(self, slim_nlp_engine):
        assert slim_nlp_engine.get_supported_languages() == ["en"]

    def test_when_get_supported_languages_not_loaded_then_raises(self):
        engine = SlimSpacyNlpEngine()
        with pytest.raises(ValueError, match="not loaded"):
            engine.get_supported_languages()


class TestSlimSpacyNlpEngineRegistryIntegration:
    """Tests for registering a slim engine with analyzer registries."""

    def test_when_registry_adds_slim_engine_then_spacy_recognizer_is_not_added(
        self, slim_nlp_engine
    ):
        registry = RecognizerRegistry(supported_languages=["en"])

        registry.add_nlp_recognizer(slim_nlp_engine)

        assert registry.recognizers == []

    def test_when_provider_uses_slim_engine_then_no_spacy_entities_are_advertised(
        self, slim_nlp_engine
    ):
        provider = RecognizerRegistryProvider(
            registry_configuration={
                "supported_languages": ["en"],
                "recognizers": [{"name": "CreditCardRecognizer", "type": "predefined"}],
            },
            nlp_engine=slim_nlp_engine,
        )

        registry = provider.create_recognizer_registry()

        assert not any(
            isinstance(recognizer, SpacyRecognizer)
            for recognizer in registry.recognizers
        )
        assert registry.get_supported_entities(languages=["en"]) == ["CREDIT_CARD"]

    def test_when_get_nlp_recognizer_with_slim_engine_then_raises(
        self, slim_nlp_engine
    ):
        with pytest.raises(ValueError, match="does not have an NLP recognizer"):
            RecognizerRegistry.get_nlp_recognizer(slim_nlp_engine)

    def test_when_analyzer_uses_slim_with_spacy_recognizer_then_raises(
        self, slim_nlp_engine
    ):
        registry = RecognizerRegistry(
            recognizers=[SpacyRecognizer()], supported_languages=["en"]
        )

        with pytest.raises(
            ValueError,
            match="SlimSpacyNlpEngine does not provide NER output",
        ):
            AnalyzerEngine(registry=registry, nlp_engine=slim_nlp_engine)

    def test_when_analyzer_uses_slim_then_in_text_context_enhances_score(
        self, slim_nlp_engine
    ):
        zip_recognizer = PatternRecognizer(
            supported_entity="ZIP",
            patterns=[Pattern(name="zip", regex=r"\b\d{5}\b", score=0.3)],
            context=["zip"],
        )
        registry = RecognizerRegistry(
            recognizers=[zip_recognizer], supported_languages=["en"]
        )
        analyzer = AnalyzerEngine(registry=registry, nlp_engine=slim_nlp_engine)

        results = analyzer.analyze(
            text="my zip code is 10023",
            language="en",
            entities=["ZIP"],
            return_decision_process=True,
        )

        assert len(results) == 1
        assert results[0].score > 0.3
        assert results[0].analysis_explanation.supportive_context_word == "zip"


class TestSlimSpacyNlpEngineProvider:
    """Tests for creating slim engine via NlpEngineProvider."""

    def test_when_create_slim_engine_via_provider_then_succeeds(self, mocker):
        mocker.patch(
            "presidio_analyzer.nlp_engine.slim_spacy_nlp_engine."
            "SlimSpacyNlpEngine._download_spacy_model_if_needed",
            return_value=None,
        )
        nlp_configuration = {
            "nlp_engine_name": "slim",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        engine = provider.create_engine()
        assert isinstance(engine, SlimSpacyNlpEngine)
        assert engine.nlp is not None

    def test_when_create_slim_engine_from_yaml_then_succeeds(self, mocker):
        mocker.patch(
            "presidio_analyzer.nlp_engine.slim_spacy_nlp_engine."
            "SlimSpacyNlpEngine._download_spacy_model_if_needed",
            return_value=None,
        )
        nlp_configuration = {
            "nlp_engine_name": "slim",
            "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
        }
        provider = NlpEngineProvider(nlp_configuration=nlp_configuration)
        engine = provider.create_engine()
        assert isinstance(engine, SlimSpacyNlpEngine)

    def test_when_slim_engine_in_available_engines(self):
        provider = NlpEngineProvider()
        assert "slim" in provider.nlp_engines


class TestDefaultSlimModels:
    """Tests for the default model mapping."""

    def test_when_default_models_then_english_present(self):
        assert "en" in DEFAULT_SLIM_MODELS

    def test_when_default_models_then_all_values_are_sm(self):
        for lang, model in DEFAULT_SLIM_MODELS.items():
            assert "_sm" in model or "sm" in model, (
                f"Default model for {lang} ({model}) should be a small model"
            )
