import logging
from typing import Any, Dict, Iterable, Iterator, List, Tuple, Union

from spacy.tokens import Doc
from spacy.vocab import Vocab

from presidio_analyzer.nlp_engine import NlpArtifacts, NlpEngine

logger = logging.getLogger("presidio-analyzer")


class NoOpNlpEngine(NlpEngine):
    """An NLP engine that performs no linguistic processing.

    This engine is intended for AnalyzerEngine configurations where all active
    recognizers are self-contained and do not require NLP artifacts. It loads no
    external model and returns empty artifacts for each analyzed text.
    The default LemmaContextAwareEnhancer can use context passed explicitly to
    ``AnalyzerEngine.analyze()``, but cannot use context words from the analyzed
    text because this engine produces no tokens or lemmas.
    """

    engine_name = "no_op"
    is_available = True

    def __init__(
        self,
        models: List[Dict[str, str]],
    ):
        self.models = self._validate_models(models)
        self._vocab = Vocab()
        self.nlp = None

    def load(self) -> None:
        """Mark configured languages as loaded without loading external models."""
        nlp = {}
        for model in self.models:
            nlp[model["lang_code"]] = None

        self.nlp = nlp
        logger.info("Loaded no-op NLP engine with languages: %s", list(self.nlp.keys()))

    @classmethod
    def _validate_models(cls, models: List[Dict[str, str]]) -> List[Dict[str, str]]:
        if not isinstance(models, list) or not models:
            raise ValueError("models must be a non-empty list")

        seen_languages = set()
        validated_models = []
        for model in models:
            validated_model = cls._validate_model_params(model)
            language = validated_model["lang_code"]
            if language in seen_languages:
                raise ValueError(
                    f"Duplicate language '{language}' in no-op NLP engine models"
                )
            seen_languages.add(language)
            validated_models.append(validated_model)

        return validated_models

    @classmethod
    def _validate_model_params(cls, model: Dict) -> Dict[str, str]:
        """Validate that required model parameters are present."""
        if not isinstance(model, dict):
            raise ValueError("Each model must be a dictionary")
        if "lang_code" not in model:
            raise ValueError("lang_code is missing from model configuration")
        if "model_name" not in model:
            raise ValueError("model_name is missing from model configuration")
        if not isinstance(model["lang_code"], str) or not model["lang_code"]:
            raise ValueError("lang_code must be a non-empty string")
        if model["lang_code"] != model["lang_code"].strip():
            raise ValueError("lang_code must not contain leading or trailing spaces")
        if not isinstance(model["model_name"], str):
            raise ValueError("model_name must be a string")
        return {"lang_code": model["lang_code"], "model_name": model["model_name"]}

    def is_loaded(self) -> bool:
        """Return True if the no-op engine has been initialized."""
        return self.nlp is not None

    def process_text(self, text: str, language: str) -> NlpArtifacts:
        """Return empty NLP artifacts for the given text and language."""
        self._validate_string(text, "text")
        self._validate_loaded_language(language)
        return self._create_empty_nlp_artifacts(language)

    def process_batch(
        self,
        texts: Iterable[Union[str, Tuple[str, Any]]],
        language: str,
        batch_size: int = 1,
        n_process: int = 1,
        as_tuples: bool = False,
        **kwargs,
    ) -> Iterator[Union[Tuple[str, NlpArtifacts], Tuple[str, NlpArtifacts, Any]]]:
        """Return empty NLP artifacts for each text in a batch."""
        if kwargs:
            logger.warning(
                "Ignoring unsupported kwargs in NoOpNlpEngine.process_batch: %s",
                sorted(kwargs.keys()),
            )
        self._validate_loaded_language(language)

        for item in texts:
            if as_tuples:
                if not isinstance(item, tuple) or len(item) != 2:
                    raise ValueError(
                        "When 'as_tuples' is True, "
                        "'texts' must be an iterable of tuples (text, context)."
                    )
                text, context = item
                text = str(text)
                yield text, self._create_empty_nlp_artifacts(language), context
            else:
                text = str(item)
                yield text, self._create_empty_nlp_artifacts(language)

    def is_stopword(self, word: str, language: str) -> bool:
        """Return False because no stop-word vocabulary is available."""
        self._validate_string(word, "word")
        self._validate_loaded_language(language)
        return False

    def is_punct(self, word: str, language: str) -> bool:
        """Return False because no punctuation vocabulary is available."""
        self._validate_string(word, "word")
        self._validate_loaded_language(language)
        return False

    def get_supported_entities(self) -> List[str]:
        """Return no entities because this engine does not run NER."""
        return []

    def get_supported_languages(self) -> List[str]:
        """Return the languages configured for this no-op engine."""
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")
        return list(self.nlp.keys())

    def _validate_loaded_language(self, language: str) -> None:
        self._validate_string(language, "language")
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

        if language not in self.nlp:
            raise ValueError(
                f"Language '{language}' is not supported by this NLP engine. "
                f"Supported languages: {list(self.nlp.keys())}"
            )

    @staticmethod
    def _validate_string(value: Any, parameter_name: str) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{parameter_name} must be a string")
        return value

    def _create_empty_nlp_artifacts(self, language: str) -> NlpArtifacts:
        return NlpArtifacts(
            entities=[],
            tokens=Doc(self._vocab, words=[]),
            tokens_indices=[],
            lemmas=[],
            nlp_engine=self,
            language=language,
            scores=[],
        )
