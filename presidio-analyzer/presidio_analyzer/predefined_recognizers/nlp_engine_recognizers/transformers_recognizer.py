import logging
from typing import Optional

from presidio_analyzer.predefined_recognizers.nlp_engine_recognizers.spacy_recognizer import (  # noqa: E501
    SpacyRecognizer,
)

logger = logging.getLogger("presidio-analyzer")


class TransformersRecognizer(SpacyRecognizer):
    """
    Recognize entities produced by the Transformers NLP engine.

    The recognizer does not run Transformers models directly. It reads the
    entities and confidence scores exposed through NlpArtifacts.
    """  # noqa: E501

    ENTITIES = [
        "PERSON",
        "LOCATION",
        "ORGANIZATION",
        "AGE",
        "ID",
        "EMAIL",
        "DATE_TIME",
        "PHONE_NUMBER",
    ]

    def __init__(self, name: Optional[str] = None, **kwargs):
        self.DEFAULT_EXPLANATION = self.DEFAULT_EXPLANATION.replace(
            "Spacy", "Transformers"
        )
        super().__init__(name=name, **kwargs)
