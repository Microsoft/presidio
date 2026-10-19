import logging
from typing import Dict, List, Optional

import spacy
from spacy.tokens import Doc, Span

from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    SpacyNlpEngine,
)
from presidio_analyzer.nlp_engine.huggingface_token_pipe import (
    FACTORY_NAME,
    is_available,
)

logger = logging.getLogger("presidio-analyzer")


class TransformersNlpEngine(SpacyNlpEngine):
    """

    TransformersNlpEngine is a transformers based NlpEngine.

    It comprises a spacy pipeline used for tokenization,
    lemmatization, pos, and a transformers component for NER.

    Both the underlying spacy pipeline and the transformers engine could be
    configured by the user.
    :param models: A dict holding the model's configuration.
    :example:
    [{"lang_code": "en", "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "dslim/bert-base-NER"
            }
    }]
    :param ner_model_configuration: Parameters for the NER model.
    See conf/transformers.yaml for an example


    Note that since the spaCy model is not used for NER,
    we recommend using a simple model, such as en_core_web_sm for English.
    For potential Transformers models, see a list of models here:
    https://huggingface.co/models?pipeline_tag=token-classification
    It is further recommended to fine-tune these models
    to the specific scenario in hand.

    """

    engine_name = "transformers"
    is_available = is_available()

    def __init__(
        self,
        models: Optional[List[Dict]] = None,
        ner_model_configuration: Optional[NerModelConfiguration] = None,
    ):
        if not models:
            models = [
                {
                    "lang_code": "en",
                    "model_name": {
                        "spacy": "en_core_web_sm",
                        "transformers": "obi/deid_roberta_i2b2",
                    },
                }
            ]
        super().__init__(models=models, ner_model_configuration=ner_model_configuration)
        self.entity_key = "bert-base-ner"

    def load(self) -> None:
        """Load the spaCy and transformers models."""

        logger.debug(f"Loading SpaCy and transformers models: {self.models}")

        super()._enable_gpu()

        self.nlp = {}

        for model in self.models:
            self._validate_model_params(model)
            spacy_model = model["model_name"]["spacy"]
            transformers_model = model["model_name"]["transformers"]
            self._download_spacy_model_if_needed(spacy_model)

            nlp = spacy.load(spacy_model, disable=["parser", "ner"])

            pipe_config = {
                "model": transformers_model,
                "stride": self.ner_model_configuration.stride,
                "alignment_mode": self.ner_model_configuration.alignment_mode,
                "aggregation_strategy": self.ner_model_configuration.aggregation_strategy,  # noqa: E501
                "spans_key": self.entity_key,
            }

            nlp.add_pipe(FACTORY_NAME, config=pipe_config)
            self.nlp[model["lang_code"]] = nlp

    @staticmethod
    def _validate_model_params(model: Dict) -> None:
        if "lang_code" not in model:
            raise ValueError("lang_code is missing from model configuration")
        if "model_name" not in model:
            raise ValueError("model_name is missing from model configuration")
        if not isinstance(model["model_name"], dict):
            raise ValueError("model_name must be a dictionary")
        if "spacy" not in model["model_name"]:
            raise ValueError("spacy model name is missing from model configuration")
        if "transformers" not in model["model_name"]:
            raise ValueError(
                "transformers model name is missing from model configuration"
            )

    def _get_entities(self, doc: Doc) -> List[Span]:
        """
        Extract entities out of a spaCy pipeline, depending on the type of pipeline.

        For the Hugging Face token pipe, this is doc.spans[key].
        :param doc: the output spaCy doc.
        :return: List of entities
        """

        return doc.spans[self.entity_key]

    def _get_scores_for_entities(self, doc: Doc) -> List[float]:
        """Extract scores for entities from the doc.

        While spaCy does not provide confidence scores,
        the Hugging Face token pipe adds confidence scores
        as SpanGroup attributes.
        :param doc: SpaCy doc
        """

        return [float(score) for score in doc.spans[self.entity_key].attrs["scores"]]
