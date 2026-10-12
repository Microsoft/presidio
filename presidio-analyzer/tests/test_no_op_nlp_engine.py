from collections.abc import Iterator

import pytest
from spacy.tokens import Doc

from presidio_analyzer import (
    AnalyzerEngine,
    AnalyzerEngineProvider,
    BatchAnalyzerEngine,
    LemmaContextAwareEnhancer,
    Pattern,
    PatternRecognizer,
)
from presidio_analyzer.nlp_engine import NlpEngineProvider, NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer
from presidio_analyzer.recognizer_registry import RecognizerRegistry
from install_nlp_models import _download_model


@pytest.fixture
def no_op_nlp_engine():
    engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])
    engine.load()
    return engine


class TestNoOpNlpEngine:
    def test_when_init_without_models_then_raises(self):
        with pytest.raises(TypeError):
            NoOpNlpEngine()

    def test_when_init_with_unexpected_argument_then_raises(self):
        with pytest.raises(TypeError):
            NoOpNlpEngine(unexpected_argument=True)

    def test_when_init_with_empty_models_then_raises(self):
        with pytest.raises(ValueError, match="non-empty"):
            NoOpNlpEngine(models=[])

    def test_when_init_with_non_dict_model_then_raises(self):
        with pytest.raises(ValueError, match="Each model must be a dictionary"):
            NoOpNlpEngine(models=["no_op"])

    def test_when_init_without_lang_code_then_raises(self):
        with pytest.raises(ValueError, match="lang_code is missing"):
            NoOpNlpEngine(models=[{"model_name": "no_op"}])

    def test_when_init_without_model_name_then_raises(self):
        with pytest.raises(ValueError, match="model_name is missing"):
            NoOpNlpEngine(models=[{"lang_code": "en"}])

    def test_when_init_with_empty_language_then_raises(self):
        with pytest.raises(ValueError, match="lang_code must be a non-empty string"):
            NoOpNlpEngine(models=[{"lang_code": "", "model_name": "no_op"}])

    def test_when_init_with_non_string_model_name_then_raises(self):
        with pytest.raises(ValueError, match="model_name must be a string"):
            NoOpNlpEngine(models=[{"lang_code": "en", "model_name": 1}])

    def test_when_init_with_any_model_name_then_succeeds(self):
        engine = NoOpNlpEngine(
            models=[{"lang_code": "en", "model_name": "en_core_web_lg"}]
        )

        assert engine.models == [
            {"lang_code": "en", "model_name": "en_core_web_lg"}
        ]

    def test_when_init_with_extra_model_key_then_ignores_it(self):
        engine = NoOpNlpEngine(
            models=[
                {
                    "lang_code": "en",
                    "model_name": "no_op",
                    "extra_key": "ignored",
                }
            ]
        )

        assert engine.models == [{"lang_code": "en", "model_name": "no_op"}]

    def test_when_init_with_language_spaces_then_raises(self):
        with pytest.raises(ValueError, match="leading or trailing"):
            NoOpNlpEngine(models=[{"lang_code": " en", "model_name": "no_op"}])

    def test_when_init_with_duplicate_languages_then_raises(self):
        with pytest.raises(ValueError, match="Duplicate language"):
            NoOpNlpEngine(
                models=[
                    {"lang_code": "en", "model_name": "no_op"},
                    {"lang_code": "en", "model_name": "no_op"},
                ]
            )

    def test_when_load_then_supported_language_is_available(self, no_op_nlp_engine):
        assert no_op_nlp_engine.is_loaded()
        assert no_op_nlp_engine.get_supported_languages() == ["en"]

    def test_when_load_with_any_model_name_then_supported_language_is_available(self):
        engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])
        engine.models[0]["model_name"] = "en_core_web_lg"

        engine.load()

        assert engine.is_loaded()
        assert engine.get_supported_languages() == ["en"]

    def test_when_process_text_then_empty_artifacts_returned(self, no_op_nlp_engine):
        artifacts = no_op_nlp_engine.process_text("John Smith", language="en")

        assert artifacts.entities == []
        assert isinstance(artifacts.tokens, Doc)
        assert len(artifacts.tokens) == 0
        assert artifacts.tokens_indices == []
        assert artifacts.lemmas == []
        assert artifacts.keywords == []
        assert artifacts.scores == []
        assert artifacts.nlp_engine is no_op_nlp_engine

    def test_when_process_text_with_unsupported_language_then_raises(
        self, no_op_nlp_engine
    ):
        with pytest.raises(ValueError, match="not supported"):
            no_op_nlp_engine.process_text("John Smith", language="es")

    def test_when_process_text_with_non_string_text_then_raises(self, no_op_nlp_engine):
        with pytest.raises(TypeError, match="text must be a string"):
            no_op_nlp_engine.process_text(123, language="en")

    def test_when_process_text_with_non_string_language_then_raises(
        self, no_op_nlp_engine
    ):
        with pytest.raises(TypeError, match="language must be a string"):
            no_op_nlp_engine.process_text("John Smith", language=123)

    def test_when_not_loaded_then_process_text_raises(self):
        engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])

        with pytest.raises(ValueError, match="not loaded"):
            engine.process_text("John Smith", language="en")

    def test_when_not_loaded_then_get_supported_languages_raises(self):
        engine = NoOpNlpEngine(models=[{"lang_code": "en", "model_name": "no_op"}])

        with pytest.raises(ValueError, match="not loaded"):
            engine.get_supported_languages()

    def test_when_process_batch_then_empty_artifacts_returned(self, no_op_nlp_engine):
        results = no_op_nlp_engine.process_batch(["one", "two"], language="en")

        assert isinstance(results, Iterator)
        result_list = list(results)
        assert [text for text, _ in result_list] == ["one", "two"]
        assert all(artifacts.entities == [] for _, artifacts in result_list)
        assert all(isinstance(artifacts.tokens, Doc) for _, artifacts in result_list)
        assert all(len(artifacts.tokens) == 0 for _, artifacts in result_list)

    def test_when_process_batch_as_tuples_then_context_preserved(
        self, no_op_nlp_engine
    ):
        results = list(
            no_op_nlp_engine.process_batch(
                [("one", {"id": 1})], language="en", as_tuples=True
            )
        )

        assert len(results) == 1
        text, artifacts, context = results[0]
        assert text == "one"
        assert artifacts.entities == []
        assert context == {"id": 1}

    def test_when_process_batch_invalid_tuple_then_raises(self, no_op_nlp_engine):
        with pytest.raises(ValueError, match="tuples"):
            list(
                no_op_nlp_engine.process_batch(
                    ["not a tuple"], language="en", as_tuples=True
                )
            )

    def test_when_process_batch_with_non_string_text_then_converts_to_string(
        self, no_op_nlp_engine
    ):
        result = list(no_op_nlp_engine.process_batch([123], language="en"))

        assert result[0][0] == "123"
        assert result[0][1].entities == []

    def test_when_process_batch_as_tuples_with_non_string_text_then_converts_to_string(
        self, no_op_nlp_engine
    ):
        result = list(
            no_op_nlp_engine.process_batch(
                [(123, {"id": 1})], language="en", as_tuples=True
            )
        )

        text, artifacts, context = result[0]
        assert text == "123"
        assert artifacts.entities == []
        assert context == {"id": 1}

    def test_when_process_batch_with_unsupported_kwarg_then_warns(
        self, no_op_nlp_engine, caplog
    ):
        with caplog.at_level("WARNING", logger="presidio-analyzer"):
            results = list(
                no_op_nlp_engine.process_batch(
                    ["one"], language="en", unsupported_option=True
                )
            )

        assert results[0][0] == "one"
        assert "Ignoring unsupported kwargs" in caplog.text

    def test_when_get_supported_entities_then_empty(self, no_op_nlp_engine):
        assert no_op_nlp_engine.get_supported_entities() == []

    def test_when_stopword_or_punct_then_false(self, no_op_nlp_engine):
        assert no_op_nlp_engine.is_stopword("the", language="en") is False
        assert no_op_nlp_engine.is_punct(".", language="en") is False

    def test_when_stopword_or_punct_with_non_string_word_then_raises(
        self, no_op_nlp_engine
    ):
        with pytest.raises(TypeError, match="word must be a string"):
            no_op_nlp_engine.is_stopword(123, language="en")
        with pytest.raises(TypeError, match="word must be a string"):
            no_op_nlp_engine.is_punct(123, language="en")


class TestNoOpNlpEngineProvider:
    def test_when_create_no_op_engine_via_provider_then_succeeds(self):
        nlp_configuration = {
            "nlp_engine_name": "no_op",
            "models": [{"lang_code": "en", "model_name": "no_op"}],
        }

        engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

        assert isinstance(engine, NoOpNlpEngine)
        assert engine.get_supported_languages() == ["en"]
        assert engine.get_supported_entities() == []

    def test_when_no_op_engine_in_available_engines(self):
        provider = NlpEngineProvider()

        assert "no_op" in provider.nlp_engines

    def test_when_no_op_configuration_has_extra_key_then_ignores_it(self):
        nlp_configuration = {
            "nlp_engine_name": "no_op",
            "models": [{"lang_code": "en", "model_name": "no_op"}],
            "ner_model_configuration": {},
        }

        engine = NlpEngineProvider(nlp_configuration=nlp_configuration).create_engine()

        assert isinstance(engine, NoOpNlpEngine)
        assert engine.get_supported_languages() == ["en"]


class TestNoOpNlpEngineModelInstallation:
    def test_when_download_model_for_no_op_then_no_model_is_installed(self):
        _download_model("no_op", "no_op")


class TestNoOpNlpEngineAnalyzerIntegration:
    def test_when_analyzer_uses_no_op_then_spacy_recognizer_is_not_added(
        self, no_op_nlp_engine
    ):
        analyzer = AnalyzerEngine(nlp_engine=no_op_nlp_engine)

        nlp_recognizers = [
            recognizer
            for recognizer in analyzer.registry.recognizers
            if isinstance(recognizer, SpacyRecognizer)
        ]
        assert nlp_recognizers == []

    def test_when_analyzer_uses_no_op_with_registered_nlp_recognizer_then_raises(
        self, no_op_nlp_engine
    ):
        registry = RecognizerRegistry(
            recognizers=[SpacyRecognizer()], supported_languages=["en"]
        )

        with pytest.raises(ValueError, match="NoOpNlpEngine cannot be used"):
            AnalyzerEngine(registry=registry, nlp_engine=no_op_nlp_engine)

    def test_when_get_nlp_recognizer_with_no_op_then_raises(self, no_op_nlp_engine):
        with pytest.raises(ValueError, match="does not have an NLP recognizer"):
            RecognizerRegistry.get_nlp_recognizer(no_op_nlp_engine)

    def test_when_analyzer_uses_no_op_then_pattern_recognizers_still_run(
        self, no_op_nlp_engine
    ):
        analyzer = AnalyzerEngine(nlp_engine=no_op_nlp_engine)

        results = analyzer.analyze(
            text="My credit card is 4111111111111111",
            language="en",
            entities=["CREDIT_CARD"],
        )

        assert len(results) == 1
        assert results[0].entity_type == "CREDIT_CARD"

    def test_when_batch_analyzer_uses_no_op_then_primitive_values_still_run(
        self, no_op_nlp_engine
    ):
        analyzer = AnalyzerEngine(nlp_engine=no_op_nlp_engine)
        batch_analyzer = BatchAnalyzerEngine(analyzer_engine=analyzer)

        results = batch_analyzer.analyze_iterator(
            texts=[4111111111111111],
            language="en",
            entities=["CREDIT_CARD"],
        )

        assert len(results) == 1
        assert len(results[0]) == 1
        assert results[0][0].entity_type == "CREDIT_CARD"

    def test_when_analyzer_uses_no_op_then_explicit_context_enhances_score(
        self, no_op_nlp_engine
    ):
        zip_recognizer = PatternRecognizer(
            supported_entity="ZIP",
            patterns=[Pattern(name="zip", regex=r"\b\d{5}\b", score=0.3)],
            context=["zip"],
        )
        analyzer = AnalyzerEngine(nlp_engine=no_op_nlp_engine)

        results = analyzer.analyze(
            text="10023",
            language="en",
            entities=["ZIP"],
            ad_hoc_recognizers=[zip_recognizer],
            context=["zip"],
            return_decision_process=True,
        )

        assert len(results) == 1
        assert results[0].score > 0.3
        assert results[0].analysis_explanation.supportive_context_word == "zip"

    def test_when_analyzer_uses_no_op_then_in_text_context_does_not_enhance_score(
        self, no_op_nlp_engine
    ):
        zip_recognizer = PatternRecognizer(
            supported_entity="ZIP",
            patterns=[Pattern(name="zip", regex=r"\b\d{5}\b", score=0.3)],
            context=["zip"],
        )
        analyzer = AnalyzerEngine(nlp_engine=no_op_nlp_engine)

        results = analyzer.analyze(
            text="my zip code is 10023",
            language="en",
            entities=["ZIP"],
            ad_hoc_recognizers=[zip_recognizer],
        )

        assert len(results) == 1
        assert results[0].score == 0.3

    def test_when_analyzer_uses_no_op_with_lemma_context_enhancer_then_warns(
        self, no_op_nlp_engine
    ):
        with pytest.warns(UserWarning, match="cannot use context words"):
            AnalyzerEngine(
                nlp_engine=no_op_nlp_engine,
                context_aware_enhancer=LemmaContextAwareEnhancer(),
            )

    def test_when_provider_uses_no_op_then_spacy_recognizer_is_not_added(
        self, tmp_path
    ):
        analyzer_conf_file = tmp_path / "no_op_analyzer.yaml"
        analyzer_conf_file.write_text(
            """
supported_languages:
  - en
default_score_threshold: 0
nlp_configuration:
  nlp_engine_name: no_op
  models:
    - lang_code: en
      model_name: no_op
recognizer_registry:
  recognizers:
    - name: CreditCardRecognizer
      type: predefined
""",
            encoding="utf-8",
        )

        analyzer = AnalyzerEngineProvider(
            analyzer_engine_conf_file=analyzer_conf_file
        ).create_engine()

        assert isinstance(analyzer.nlp_engine, NoOpNlpEngine)
        assert not any(
            isinstance(recognizer, SpacyRecognizer)
            for recognizer in analyzer.registry.recognizers
        )

    def test_when_provider_uses_no_op_with_nlp_recognizer_then_raises(self, tmp_path):
        analyzer_conf_file = tmp_path / "no_op_with_nlp_recognizer.yaml"
        analyzer_conf_file.write_text(
            """
supported_languages:
  - en
default_score_threshold: 0
nlp_configuration:
  nlp_engine_name: no_op
  models:
    - lang_code: en
      model_name: no_op
recognizer_registry:
  recognizers:
    - name: SpacyRecognizer
      type: predefined
""",
            encoding="utf-8",
        )

        provider = AnalyzerEngineProvider(analyzer_engine_conf_file=analyzer_conf_file)

        with pytest.raises(ValueError, match="NoOpNlpEngine cannot be used"):
            provider.create_engine()
