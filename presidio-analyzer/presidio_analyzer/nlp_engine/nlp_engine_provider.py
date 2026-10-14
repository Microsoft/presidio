import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import yaml

from presidio_analyzer.input_validation import ConfigurationValidator
from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    NlpEngine,
    NoOpNlpEngine,
    SlimSpacyNlpEngine,
    SpacyNlpEngine,
    StanzaNlpEngine,
    TransformersNlpEngine,
)

logger = logging.getLogger("presidio-analyzer")


class NlpEngineProvider:
    """Create different NLP engines from configuration.

    :param nlp_engines: List of available NLP engines
    Default: (SpacyNlpEngine, StanzaNlpEngine, TransformersNlpEngine,
    SlimSpacyNlpEngine, NoOpNlpEngine)
    :param nlp_configuration: Dict containing nlp configuration
    :example: configuration:
            {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en",
                            "model_name": "en_core_web_lg"
                          }]
            }
    Nlp engine names available by default: spacy, stanza, transformers, slim, no_op.
    :param conf_file: Path to yaml file containing nlp engine configuration.
    """

    def __init__(
        self,
        nlp_engines: Optional[Tuple] = None,
        conf_file: Optional[Union[Path, str]] = None,
        nlp_configuration: Optional[Dict] = None,
    ):
        if nlp_engines is None:
            nlp_engines = (
                SpacyNlpEngine,
                StanzaNlpEngine,
                TransformersNlpEngine,
                SlimSpacyNlpEngine,
                NoOpNlpEngine,
            )

        self.nlp_engines = {
            engine.engine_name: engine for engine in nlp_engines if engine.is_available
        }
        logger.debug(
            f"Loaded these available nlp engines: {list(self.nlp_engines.keys())}"
        )

        if conf_file and nlp_configuration:
            raise ValueError(
                "Either conf_file or nlp_configuration should be provided, not both."
            )

        if nlp_configuration:
            ConfigurationValidator.validate_nlp_configuration(nlp_configuration)
            self.nlp_configuration = nlp_configuration

        if conf_file or conf_file == "":
            if conf_file == "":
                raise ValueError("conf_file is empty")
            ConfigurationValidator.validate_file_path(conf_file)
            self.nlp_configuration = self._read_nlp_conf(conf_file)

        if conf_file is None and nlp_configuration is None:
            conf_file = self._get_full_conf_path()
            logger.debug(f"Reading default conf file from {conf_file}")
            self.nlp_configuration = self._read_nlp_conf(conf_file)
            ConfigurationValidator.validate_nlp_configuration(self.nlp_configuration)

    @staticmethod
    def _read_nlp_conf(conf_file: Union[Path, str]) -> Dict:
        """Read NLP configuration from a YAML file."""
        with open(conf_file) as file:
            return yaml.safe_load(file)

    @staticmethod
    def _get_full_conf_path(
        default_conf_file: Union[Path, str] = "default.yaml",
    ) -> Path:
        """Return a Path to the default conf file."""
        return Path(Path(__file__).parent, "../conf", default_conf_file)

    def create_engine(self) -> NlpEngine:
        """Create an NLP engine instance."""
        # Configuration is already validated by Pydantic in __init__
        nlp_engine_name = self.nlp_configuration["nlp_engine_name"]
        if nlp_engine_name not in self.nlp_engines:
            raise ValueError(
                f"NLP engine '{nlp_engine_name}' is not available. "
                "Make sure you have all required packages installed"
            )

        nlp_engine_class = self.nlp_engines[nlp_engine_name]
        nlp_models = self.nlp_configuration["models"]

        if nlp_engine_name == NoOpNlpEngine.engine_name:
            engine = nlp_engine_class(models=nlp_models)
        elif nlp_engine_name == SlimSpacyNlpEngine.engine_name:
            generic_tokenizer = self.nlp_configuration.get("generic_tokenizer")
            engine = nlp_engine_class(
                models=nlp_models, generic_tokenizer=generic_tokenizer
            )
        else:
            ner_model_configuration = self.nlp_configuration.get(
                "ner_model_configuration"
            )
            if ner_model_configuration:
                ner_model_configuration = NerModelConfiguration.from_dict(
                    ner_model_configuration
                )

            engine = nlp_engine_class(
                models=nlp_models, ner_model_configuration=ner_model_configuration
            )

        engine.load()
        logger.info(
            f"Created NLP engine: {engine.engine_name}. "
            f"Loaded models: {list(engine.nlp.keys())}"
        )
        return engine
