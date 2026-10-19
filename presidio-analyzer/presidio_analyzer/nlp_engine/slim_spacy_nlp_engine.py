import logging
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Set, Tuple, Union

import spacy
from spacy.tokens import Doc

from presidio_analyzer.nlp_engine import NlpArtifacts, NlpEngine

logger = logging.getLogger("presidio-analyzer")

# Default small spaCy models per language for tokenization/lemmatization.
# These are lightweight and focused on linguistic features (no NER).
DEFAULT_SLIM_MODELS = {
    "en": "en_core_web_sm",
    "es": "es_core_news_sm",
    "de": "de_core_news_sm",
    "fr": "fr_core_news_sm",
    "it": "it_core_news_sm",
    "pt": "pt_core_news_sm",
    "nl": "nl_core_news_sm",
    "pl": "pl_core_news_sm",
    "ro": "ro_core_news_sm",
    "ja": "ja_core_news_sm",
    "zh": "zh_core_web_sm",
    "da": "da_core_news_sm",
    "el": "el_core_news_sm",
    "nb": "nb_core_news_sm",
    "lt": "lt_core_news_sm",
    "mk": "mk_core_news_sm",
    "xx": "xx_ent_wiki_sm",
    "he": "he_core_news_sm",
}


class SlimSpacyNlpEngine(NlpEngine):
    """A slim NLP engine that provides only tokenization and lemmatization.

    This engine loads spaCy models with the NER pipeline component disabled,
    reducing memory usage and load time. It is intended for use in Presidio v3
    where entity extraction is handled by self-contained recognizers rather
    than the shared NLP engine.

    The slim engine:
    - Provides tokenization, lemmatization, stopword and punctuation checks.
    - Does NOT extract named entities (returns empty entity lists).
    - Uses small spaCy models by default for fast loading and low memory.
    - Supports auto-downloading spaCy models when they are missing.
    - Falls back to a generic tokenizer for unsupported languages.

    :param models: List of model configurations per language.
        Example: [{"lang_code": "en", "model_name": "en_core_web_sm"}]
        If not provided, uses default small models for the given languages.
    :param supported_languages: List of language codes to support.
        Used only when models is not provided, to select default models.
    :param auto_download: Whether to automatically download missing spaCy models.
    :param generic_tokenizer: Model name to use as a fallback for languages
        without a default model. Set to "blank" to use spacy.blank(lang)
        (basic tokenization, no lemmatization). Set to a spaCy model name
        (e.g. "xx_ent_wiki_sm") to use that model for all fallback languages.
        If None, a ValueError is raised for unsupported languages.
    """

    engine_name = "slim"
    is_available = bool(spacy)

    @property
    def has_ner(self) -> bool:
        """Return False because the slim pipeline does not include NER."""
        return False

    def __init__(
        self,
        models: Optional[List[Dict[str, str]]] = None,
        supported_languages: Optional[List[str]] = None,
        auto_download: bool = True,
        generic_tokenizer: Optional[str] = None,
    ):
        self.generic_tokenizer = generic_tokenizer
        self._blank_languages: Set[str] = set()

        if models:
            self.models = models
        elif supported_languages:
            self.models = self._models_from_languages(
                supported_languages, generic_tokenizer
            )
        else:
            self.models = [{"lang_code": "en", "model_name": "en_core_web_sm"}]

        self.auto_download = auto_download
        self.nlp = None

    def _models_from_languages(
        self,
        languages: List[str],
        generic_tokenizer: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """Build model configs from language codes using default small models.

        If a language has no default model and generic_tokenizer is set,
        uses the generic tokenizer as a fallback. If generic_tokenizer is
        "blank", creates a bare spacy.blank() pipeline for that language.
        """
        models = []
        for lang in languages:
            model_name = DEFAULT_SLIM_MODELS.get(lang)
            if not model_name:
                if generic_tokenizer:
                    if generic_tokenizer == "blank":
                        self._blank_languages.add(lang)
                        continue
                    else:
                        model_name = generic_tokenizer
                    logger.info(
                        f"No default slim model for language '{lang}', "
                        f"using generic tokenizer: {model_name}"
                    )
                else:
                    raise ValueError(
                        f"No default slim model for language '{lang}'. "
                        f"Provide an explicit model via the 'models' parameter, "
                        f"or set 'generic_tokenizer' to 'blank' or a spaCy model "
                        f"name for a fallback. "
                        f"Supported defaults: {sorted(DEFAULT_SLIM_MODELS.keys())}"
                    )
            models.append({"lang_code": lang, "model_name": model_name})
        return models

    def load(self) -> None:
        """Load spaCy models with NER disabled."""
        logger.debug(f"Loading slim SpaCy models: {self.models}")

        self.nlp = {}

        # Load blank pipelines for languages that have no trained model
        for lang in self._blank_languages:
            try:
                self.nlp[lang] = spacy.blank(lang)
            except ImportError:
                logger.warning(
                    f"spaCy has no language module for '{lang}', "
                    f"falling back to multilingual tokenizer (xx)"
                )
                self.nlp[lang] = spacy.blank("xx")
            logger.info(f"Created blank spaCy pipeline for '{lang}'")

        # Load trained models with NER/parser disabled
        for model in self.models:
            self._validate_model_params(model)
            model_name = model["model_name"]

            if self.auto_download:
                self._download_spacy_model_if_needed(model_name)

            self.nlp[model["lang_code"]] = spacy.load(
                model_name, disable=["ner", "parser"]
            )

        logger.info(f"Loaded slim NLP engine with languages: {list(self.nlp.keys())}")

    @staticmethod
    def _download_spacy_model_if_needed(model_name: str) -> None:
        """Download a spaCy model if it is not already installed."""
        if not (spacy.util.is_package(model_name) or Path(model_name).exists()):
            logger.warning(f"Model {model_name} is not installed. Downloading...")
            spacy.cli.download(model_name)
            logger.info(f"Finished downloading model {model_name}")

    @staticmethod
    def _validate_model_params(model: Dict) -> None:
        """Validate that required model parameters are present."""
        if "lang_code" not in model:
            raise ValueError("lang_code is missing from model configuration")
        if "model_name" not in model:
            raise ValueError("model_name is missing from model configuration")
        if not isinstance(model["model_name"], str):
            raise ValueError("model_name must be a string")

    def is_loaded(self) -> bool:
        """Return True if the model is already loaded."""
        return self.nlp is not None

    def process_text(self, text: str, language: str) -> NlpArtifacts:
        """Execute the slim NLP pipeline on the given text.

        Performs tokenization and lemmatization only. No named entities
        are extracted.
        """
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

        if language not in self.nlp:
            raise ValueError(
                f"Language '{language}' is not supported by this NLP engine. "
                f"Supported languages: {list(self.nlp.keys())}"
            )

        doc = self.nlp[language](text)
        return self._doc_to_nlp_artifact(doc, language)

    def process_batch(
        self,
        texts: Union[List[str], List[Tuple[str, object]]],
        language: str,
        batch_size: int = 1,
        n_process: int = 1,
        as_tuples: bool = False,
    ) -> Generator[
        Union[Tuple[Any, NlpArtifacts, Any], Tuple[Any, NlpArtifacts]], Any, None
    ]:
        """Execute the slim NLP pipeline on a batch of texts."""
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

        if language not in self.nlp:
            raise ValueError(
                f"Language '{language}' is not supported by this NLP engine. "
                f"Supported languages: {list(self.nlp.keys())}"
            )

        if as_tuples:
            if not all(isinstance(item, tuple) and len(item) == 2 for item in texts):
                raise ValueError(
                    "When 'as_tuples' is True, "
                    "'texts' must be a list of tuples (text, context)."
                )
            texts = ((str(text), context) for text, context in texts)
        else:
            texts = (str(text) for text in texts)

        batch_output = self.nlp[language].pipe(
            texts, as_tuples=as_tuples, batch_size=batch_size, n_process=n_process
        )
        for output in batch_output:
            if as_tuples:
                doc, context = output
                yield doc.text, self._doc_to_nlp_artifact(doc, language), context
            else:
                doc = output
                yield doc.text, self._doc_to_nlp_artifact(doc, language)

    def is_stopword(self, word: str, language: str) -> bool:
        """Return true if the given word is a stop word."""
        return self.nlp[language].vocab[word].is_stop

    def is_punct(self, word: str, language: str) -> bool:
        """Return true if the given word is a punctuation word."""
        return self.nlp[language].vocab[word].is_punct

    def get_supported_entities(self) -> List[str]:
        """Return an empty list — the slim engine does not extract entities."""
        return []

    def get_supported_languages(self) -> List[str]:
        """Return the supported languages for this NLP engine."""
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")
        return list(self.nlp.keys())

    def _doc_to_nlp_artifact(self, doc: Doc, language: str) -> NlpArtifacts:
        """Convert a spaCy Doc to NlpArtifacts with no entities."""
        lemmas = [token.lemma_ for token in doc]
        tokens_indices = [token.idx for token in doc]

        return NlpArtifacts(
            entities=[],
            tokens=doc,
            tokens_indices=tokens_indices,
            lemmas=lemmas,
            nlp_engine=self,
            language=language,
            scores=[],
        )
