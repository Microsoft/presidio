import logging
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

import spacy
from spacy.language import Language
from spacy.tokens import Doc, Span

from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    NlpArtifacts,
    NlpEngine,
    device_detector,
)

logger = logging.getLogger("presidio-analyzer")


class SpacyNlpEngine(NlpEngine):
    """
    SpacyNlpEngine is an abstraction layer over the nlp module.

    It provides processing functionality as well as other queries
    on tokens.
    The SpacyNlpEngine uses SpaCy as its NLP module
    """

    engine_name = "spacy"
    is_available = bool(spacy)

    @property
    def has_ner(self) -> bool:
        """Returns True if this engine performs Named Entity Recognition natively."""
        return True

    def __init__(
        self,
        models: Optional[List[Dict[str, str]]] = None,
        ner_model_configuration: Optional[NerModelConfiguration] = None,
    ):
        """
        Initialize a wrapper on spaCy functionality.

        :param models: Dictionary with the name of the spaCy model per language.
        For example: models = [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        :param ner_model_configuration: Parameters for the NER model.
        See conf/spacy.yaml for an example
        """
        if not models:
            models = [{"lang_code": "en", "model_name": "en_core_web_lg"}]
        self.models = models

        if not ner_model_configuration:
            ner_model_configuration = NerModelConfiguration()
        self.ner_model_configuration = ner_model_configuration

        self.nlp = None

    def _enable_gpu(self) -> None:
        """Enable GPU support for spaCy/transformers if available."""
        device = device_detector.get_device()
        if device != "cpu":
            try:
                spacy.require_gpu()
            except Exception as e:
                logger.warning(
                    f"Failed to enable GPU ({device}), falling back to CPU: {e}"
                )

    def load(self) -> None:
        """Load the spaCy NLP model."""
        logger.debug(f"Loading SpaCy models: {self.models}")

        self._enable_gpu()

        self.nlp = {}
        for model in self.models:
            self._validate_model_params(model)
            self._download_spacy_model_if_needed(model["model_name"])
            self.nlp[model["lang_code"]] = spacy.load(model["model_name"])

    @staticmethod
    def _download_spacy_model_if_needed(model_name: str) -> None:
        if not (spacy.util.is_package(model_name) or Path(model_name).exists()):
            logger.warning(f"Model {model_name} is not installed. Downloading...")
            spacy.cli.download(model_name)
            logger.info(f"Finished downloading model {model_name}")

    @staticmethod
    def _validate_model_params(model: Dict) -> None:
        if "lang_code" not in model:
            raise ValueError("lang_code is missing from model configuration")
        if "model_name" not in model:
            raise ValueError("model_name is missing from model configuration")
        if not isinstance(model["model_name"], str):
            raise ValueError("model_name must be a string")

    def get_supported_entities(self) -> List[str]:
        """Return the supported entities for this NLP engine."""
        if not self.ner_model_configuration.model_to_presidio_entity_mapping:
            raise ValueError(
                "model_to_presidio_entity_mapping is missing from model configuration"
            )
        entities_from_mapping = list(
            set(self.ner_model_configuration.model_to_presidio_entity_mapping.values())
        )
        entities = [
            ent
            for ent in entities_from_mapping
            if ent not in self.ner_model_configuration.labels_to_ignore
        ]
        return entities

    def get_supported_languages(self) -> List[str]:
        """Return the supported languages for this NLP engine."""
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")
        return list(self.nlp.keys())

    def is_loaded(self) -> bool:
        """Return True if the model is already loaded."""
        return self.nlp is not None

    def process_text(self, text: str, language: str) -> NlpArtifacts:
        """Execute the SpaCy NLP pipeline on the given text and language."""
        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

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
        """Execute the NLP pipeline on a batch of texts using spacy pipe.

        :param texts: A list of texts to process. if as_tuples is set to True,
            texts should be a list of tuples (text, context).
        :param language: The language of the texts.
        :param batch_size: Default batch size for pipe and evaluate.
        :param n_process: Number of processors to process texts.
        :param as_tuples: If set to True, inputs should be a sequence of
            (text, context) tuples. Output will then be a sequence of
            (doc, context) tuples. Defaults to False.

        :return: A generator of tuples (text, NlpArtifacts, context) or
            (text, NlpArtifacts) depending on the value of as_tuples.
        """

        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

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
        """
        Return true if the given word is a stop word.

        (within the given language)
        """
        return self.nlp[language].vocab[word].is_stop

    def is_punct(self, word: str, language: str) -> bool:
        """
        Return true if the given word is a punctuation word.

        (within the given language).
        """
        return self.nlp[language].vocab[word].is_punct

    def get_nlp(self, language: str) -> Language:
        """
        Return the language model loaded for a language.

        :param language: Language
        :return: Model from spaCy
        """
        return self.nlp[language]

    def _doc_to_nlp_artifact(self, doc: Doc, language: str) -> NlpArtifacts:
        lemmas = [token.lemma_ for token in doc]
        tokens_indices = [token.idx for token in doc]

        entities = self._get_entities(doc)
        scores = self._get_scores_for_entities(doc)

        entities, scores = self._get_updated_entities(entities, scores)

        return NlpArtifacts(
            entities=entities,
            tokens=doc,
            tokens_indices=tokens_indices,
            lemmas=lemmas,
            nlp_engine=self,
            language=language,
            scores=scores,
        )

    def _get_entities(self, doc: Doc) -> List[Span]:
        """
        Extract entities out of a spaCy pipeline, depending on the type of pipeline.

        For normal spaCy, this would be doc.ents
        :param doc: the output spaCy doc.
        :return: List of entities
        """

        return doc.ents

    def _get_scores_for_entities(self, doc: Doc) -> List[float]:
        """Extract scores for entities from the doc.

        Since spaCy does not provide confidence scores for entities by default,
        we use the default score from the ner model configuration.
        :param doc: SpaCy doc
        """

        entities = doc.ents
        scores = [self.ner_model_configuration.default_score] * len(entities)
        return scores

    def _get_updated_entities(
        self, entities: List[Span], scores: List[float]
    ) -> Tuple[List[Span], List[float]]:
        """
        Get an updated list of entities based on the ner model configuration.

        Remove entities that are in labels_to_ignore,
        update entity names based on model_to_presidio_entity_mapping

        :param entities: Entities that were extracted from a spaCy pipeline
        :param scores: Original confidence scores for the entities extracted
        :return: Tuple holding the entities and confidence scores
        """
        if len(entities) != len(scores):
            raise ValueError("Entities and scores must be the same length")

        new_entities = []
        new_scores = []

        mapping = self.ner_model_configuration.model_to_presidio_entity_mapping
        to_ignore = self.ner_model_configuration.labels_to_ignore
        for ent, score in zip(entities, scores):
            # Remove model labels in the ignore list
            if ent.label_ in to_ignore:
                continue

            # Update entity label based on mapping
            if ent.label_ in mapping:
                ent.label_ = mapping[ent.label_]
            else:
                logger.warning(
                    f"Entity {ent.label_} is not mapped to a Presidio entity, "
                    f"but keeping anyway. "
                    f"Add to `NerModelConfiguration.labels_to_ignore` to remove."
                )

            # Remove presidio entities in the ignore list
            if ent.label_ in to_ignore:
                continue

            new_entities.append(ent)

            # Update score if entity is in low score entity names
            if ent.label_ in self.ner_model_configuration.low_score_entity_names:
                score *= self.ner_model_configuration.low_confidence_score_multiplier

            new_scores.append(score)

        return new_entities, new_scores
